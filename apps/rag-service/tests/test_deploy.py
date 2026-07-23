"""Tests for the deployment marker store."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client without running the full lifespan (no DB needed)."""
    from fastapi import FastAPI

    from app import deploy, flags
    from app.otel import init_otel

    init_otel()

    app = FastAPI()
    app.include_router(deploy.router)
    app.include_router(flags.router)

    # Clear markers before each test
    import app.deploy as deploy_mod

    deploy_mod._markers.clear()

    return TestClient(app)


def test_create_deployment_marker(client):
    """POST /admin/deploy should create a marker."""
    response = client.post(
        "/admin/deploy",
        json={"version": "v2", "note": "prompt template update"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "v2"
    assert data["note"] == "prompt template update"
    assert "timestamp" in data
    assert "previous_version" in data


def test_list_deployment_markers(client):
    """GET /admin/deploy should list all markers."""
    # Create two markers
    client.post("/admin/deploy", json={"version": "v2", "note": "first"})
    client.post("/admin/deploy", json={"version": "v3", "note": "second"})

    response = client.get("/admin/deploy")
    assert response.status_code == 200
    data = response.json()
    assert len(data["markers"]) == 2
    assert data["markers"][0]["version"] == "v2"
    assert data["markers"][1]["version"] == "v3"
    assert data["current_version"] == "v3"


def test_clear_deployment_markers(client):
    """DELETE /admin/deploy should clear all markers."""
    client.post("/admin/deploy", json={"version": "v2", "note": "test"})
    client.post("/admin/deploy", json={"version": "v3", "note": "test2"})

    response = client.delete("/admin/deploy")
    assert response.status_code == 200
    assert response.json()["count"] == 2

    # Verify cleared
    list_response = client.get("/admin/deploy")
    assert len(list_response.json()["markers"]) == 0
