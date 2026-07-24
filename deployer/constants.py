"""Span/attribute names emitted by the deployer sidecar.

DELIBERATE DUPLICATION. These values mirror `app/observability.py`'s
DEPLOYMENT_MARKER_* constants, but this module does NOT import them - the sidecar
is the sole holder of the Docker socket and is kept dependency-light and
importable without the RAG app's entire dependency tree (sqlalchemy, pgvector,
sentence-transformers, the LLM client...). Importing `app.*` here would drag all
of that into the one container that holds the socket, which is exactly the blast
radius Law 2's isolation boundary exists to keep small.

The duplication is protected against drift by
tests/test_deployer.py::test_deployment_marker_attribute_names_match_app - it
fails the build if these ever diverge from app/observability.py. So D-06's
"single source of truth for attribute names" is preserved by an assertion rather
than by an import, because here the import is the thing we cannot afford.
"""

# Mirrors app.observability.DEPLOYMENT_MARKER_SCENARIO / _VERSION (FLAG-06).
DEPLOYMENT_MARKER_SCENARIO = "deployment.scenario"
DEPLOYMENT_MARKER_VERSION = "deployment.version"

# Sidecar-only attributes - no counterpart in app/observability.py, because
# nothing inside the RAG app ever performs or describes a mutation.
DEPLOYER_ROLLBACK_FROM_IMAGE = "deployer.rollback.from_image"
DEPLOYER_ROLLBACK_TO_IMAGE = "deployer.rollback.to_image"
DEPLOYER_ROLLBACK_SERVICE = "deployer.rollback.service"
DEPLOYER_ROLLBACK_EXIT_CODE = "deployer.rollback.exit_code"

# The scenario label stamped on a rollback's deployment marker. Distinct from the
# four flag names so an operator can tell "Agent K rolled this back" apart from
# "a failure scenario was toggled on" when both appear in the same trace view.
ROLLBACK_MARKER_SCENARIO = "agent_k_rollback"
