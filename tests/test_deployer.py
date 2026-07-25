"""Tests for the deployer sidecar: the sole Docker-socket holder (LAW2-03/04).

The Docker layer is faked throughout (deployer.main._run is monkeypatched), so no
Docker socket, no real containers, and no compose file are required. What is being
tested here is the sidecar's CONTRACT - auth, the concurrency lock, the hardcoded
command shape, the pre-mutation tag capture, and the deployment marker - since
those are the properties Law 2's isolation claim actually rests on.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from deployer import main as deployer_main
from deployer.constants import (
    DEPLOYER_ROLLBACK_EXIT_CODE,
    DEPLOYER_ROLLBACK_FROM_IMAGE,
    DEPLOYER_ROLLBACK_TO_IMAGE,
    DEPLOYMENT_MARKER_SCENARIO,
    ROLLBACK_MARKER_SCENARIO,
)

TOKEN = "test-deployer-token"


@pytest.fixture(autouse=True)
def _configure_token(monkeypatch):
    monkeypatch.setenv("DEPLOYER_TOKEN", TOKEN)


@pytest.fixture(autouse=True)
def _no_real_file_writes(monkeypatch):
    """Stop the sidecar writing its tag file to the real /workspace path."""
    written: list[str] = []
    monkeypatch.setattr(deployer_main, "_write_image_tag", lambda tag: written.append(tag))
    return written


@pytest.fixture
def fake_run(monkeypatch):
    """Capture every argv the sidecar would hand to Docker, and fake the results."""
    calls: list[list[str]] = []

    async def _fake(argv):
        calls.append(argv)
        if "inspect" in argv:
            return 0, "agent-k-rag:v2-broken\n", ""
        return 0, "Recreated rag-app", ""

    monkeypatch.setattr(deployer_main, "_run", _fake)
    return calls


@pytest.fixture
def client():
    return TestClient(deployer_main.app)


def _post(client, token: str | None = TOKEN):
    headers = {} if token is None else {"X-Deployer-Token": token}
    return client.post("/rollback", headers=headers)


# --- D-06 drift protection for the deliberately duplicated constants ---


def test_deployment_marker_attribute_names_match_app():
    """deployer/constants.py duplicates these values rather than importing them
    (so the socket-holding container stays dependency-light). This assertion is
    what keeps that duplication honest - see deployer/constants.py's docstring."""
    from app import observability

    assert DEPLOYMENT_MARKER_SCENARIO == observability.DEPLOYMENT_MARKER_SCENARIO
    from deployer.constants import DEPLOYMENT_MARKER_VERSION

    assert DEPLOYMENT_MARKER_VERSION == observability.DEPLOYMENT_MARKER_VERSION


def test_deployer_does_not_import_the_rag_app():
    """The socket-holding process must not pull in the RAG app's dependency tree
    (sqlalchemy, pgvector, sentence-transformers, the LLM client). Keeping this
    surface small IS the Law 2 isolation argument."""
    import ast

    tree = ast.parse(open(deployer_main.__file__, encoding="utf-8").read())
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")

    assert not any(name == "app" or name.startswith("app.") for name in imported)


# --- LAW2-03: exactly one mutating endpoint ---


def test_exposes_exactly_one_mutating_endpoint():
    mutating = set()
    for route in deployer_main.app.routes:
        methods = getattr(route, "methods", set()) or set()
        for method in methods:
            if method in {"POST", "PUT", "PATCH", "DELETE"}:
                mutating.add((route.path, method))
    assert mutating == {("/rollback", "POST")}


def test_rollback_accepts_no_image_reference(client, fake_run):
    """The caller names no image. A body attempting to specify one is ignored -
    the endpoint takes no parameters at all, so there is nothing to influence."""
    response = client.post(
        "/rollback",
        headers={"X-Deployer-Token": TOKEN},
        json={"image": "attacker/evil:latest", "service": "signoz"},
    )
    assert response.status_code == 200
    compose_argv = [c for c in fake_run if "compose" in c][0]
    assert "attacker/evil:latest" not in compose_argv
    assert "signoz" not in compose_argv


# --- Auth ---


def test_missing_token_configuration_fails_closed(client, fake_run, monkeypatch):
    """Unlike the RAG app's /admin/flags, an unconfigured token here means the
    endpoint refuses to serve - this process can mutate infrastructure."""
    monkeypatch.delenv("DEPLOYER_TOKEN", raising=False)
    assert _post(client).status_code == 503
    assert fake_run == []


def test_wrong_token_is_rejected(client, fake_run):
    assert _post(client, token="wrong").status_code == 401
    assert fake_run == []


def test_absent_token_header_is_rejected(client, fake_run):
    assert _post(client, token=None).status_code == 401
    assert fake_run == []


# --- The rollback itself ---


def test_successful_rollback_captures_pre_mutation_image(client, fake_run):
    response = _post(client)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rolled_back"
    assert body["previous_image"] == "agent-k-rag:v2-broken"
    assert body["rolled_back_to"] == deployer_main.KNOWN_GOOD_TAG


def test_image_is_captured_before_the_mutation(client, fake_run):
    """Ordering matters: capturing after `up -d` would read the NEW tag and
    report a rollback from the version it just deployed to."""
    _post(client)
    assert "inspect" in fake_run[0]
    assert "compose" in fake_run[1]


def test_uses_force_recreate_and_never_restart(client, fake_run):
    """`restart` would restart the container on its CURRENT image and appear to
    succeed while changing nothing - the incident would silently continue."""
    _post(client)
    compose_argv = [c for c in fake_run if "compose" in c][0]
    assert compose_argv[:2] == ["docker", "compose"]
    assert "up" in compose_argv
    assert "-d" in compose_argv
    assert "--force-recreate" in compose_argv
    assert "restart" not in compose_argv


def test_known_good_tag_is_pinned_before_recreate(client, fake_run, _no_real_file_writes):
    _post(client)
    assert _no_real_file_writes == [deployer_main.KNOWN_GOOD_TAG]


def test_missing_container_still_rolls_forward_to_known_good(client, monkeypatch):
    """A down container reports previous_image=None honestly rather than
    fabricating a tag - and the rollback still proceeds, since bringing a down
    service up on the known-good image is the correct action."""
    calls = []

    async def _fake(argv):
        calls.append(argv)
        if "inspect" in argv:
            return 1, "", "No such object"
        return 0, "", ""

    monkeypatch.setattr(deployer_main, "_run", _fake)
    response = _post(client)
    assert response.status_code == 200
    assert response.json()["previous_image"] is None


def test_compose_failure_returns_500(client, monkeypatch):
    async def _fake(argv):
        if "inspect" in argv:
            return 0, "agent-k-rag:v2-broken\n", ""
        return 1, "", "service not found"

    monkeypatch.setattr(deployer_main, "_run", _fake)
    assert _post(client).status_code == 500


# --- Concurrency lock ---


def test_concurrent_rollback_returns_409(client, fake_run, monkeypatch):
    class _HeldLock:
        def locked(self):
            return True

        async def __aenter__(self):
            raise AssertionError("must not enter the lock when it is already held")

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr(deployer_main, "_rollback_lock", _HeldLock())
    response = _post(client)
    assert response.status_code == 409
    assert fake_run == []


# --- LAW2-04: the deployment marker ---


def test_deployment_marker_emitted_on_success(client, fake_run, in_memory_exporter):
    _post(client)
    markers = [s for s in in_memory_exporter.get_finished_spans() if s.name == "deployment.marker"]
    assert len(markers) == 1
    attrs = markers[0].attributes
    assert attrs[DEPLOYMENT_MARKER_SCENARIO] == ROLLBACK_MARKER_SCENARIO
    assert attrs[DEPLOYER_ROLLBACK_FROM_IMAGE] == "agent-k-rag:v2-broken"
    assert attrs[DEPLOYER_ROLLBACK_TO_IMAGE] == deployer_main.KNOWN_GOOD_TAG
    assert attrs[DEPLOYER_ROLLBACK_EXIT_CODE] == 0


def test_deployment_marker_emitted_on_failure_with_nonzero_exit(client, monkeypatch, in_memory_exporter):
    """An attempted-but-failed rollback is exactly what an operator reading the
    trace view needs to see - the marker must not be success-only."""

    async def _fake(argv):
        if "inspect" in argv:
            return 0, "agent-k-rag:v2-broken\n", ""
        return 1, "", "boom"

    monkeypatch.setattr(deployer_main, "_run", _fake)
    _post(client)
    markers = [s for s in in_memory_exporter.get_finished_spans() if s.name == "deployment.marker"]
    assert len(markers) == 1
    assert markers[0].attributes[DEPLOYER_ROLLBACK_EXIT_CODE] == 1


def test_healthz_is_read_only_and_unauthenticated(client, fake_run):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert fake_run == []
