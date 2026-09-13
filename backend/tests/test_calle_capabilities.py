from fastapi.testclient import TestClient
from app.main import app, _capability_check

client = TestClient(app)


def test_published_supported_route_is_explicitly_not_runtime_guaranteed():
    response = client.get("/calle/capability", params={"region": "GB", "locale": "en-GB"})
    assert response.status_code == 200
    body = response.json()
    assert body["published_supported"] is True
    assert body["runtime_route_guaranteed"] is False


def test_unpublished_region_is_rejected_before_side_effect():
    supported, reason = _capability_check("IT", "it-IT")
    assert supported is False
    assert "does not publish recipient region IT" in reason


def test_wrong_language_for_region_is_rejected_before_side_effect():
    supported, reason = _capability_check("FR", "en-GB")
    assert supported is False
    assert "does not publish FR/en-GB" in reason


def test_readiness_distinguishes_credentials_from_runtime_route():
    body = client.get("/calle/readiness").json()
    assert body["runtime_route_guaranteed"] is False
    assert "published_capabilities" in body
