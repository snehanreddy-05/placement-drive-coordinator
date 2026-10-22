"""
CORS preflight tests for PlacementOS FastAPI backend.

These tests verify that OPTIONS preflight requests from the production Vercel
frontend receive the correct Access-Control-Allow-Origin header.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# We need to mock the database init so the app can load without a real DB
@pytest.fixture(scope="module")
def client():
    with patch("app.database.init_db", return_value=None):
        from app.main import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


PRODUCTION_ORIGIN = "https://placement-drive-coordinator-olive.vercel.app"
LOCAL_ORIGIN = "http://localhost:3000"
BLOCKED_ORIGIN = "https://evil.example.com"


def _preflight_headers(origin: str, path: str) -> dict:
    return {
        "Origin": origin,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Content-Type",
    }


class TestCORSProductionOrigin:
    """Preflight requests from the production Vercel frontend must be accepted."""

    def test_health_preflight_allows_production_origin(self, client: TestClient):
        """OPTIONS /api/health must return Allow-Origin for the Vercel frontend."""
        resp = client.options(
            "/api/health",
            headers=_preflight_headers(PRODUCTION_ORIGIN, "/api/health"),
        )
        assert resp.status_code in (200, 204), (
            f"Expected 200/204 from preflight, got {resp.status_code}"
        )
        acao = resp.headers.get("access-control-allow-origin", "")
        assert acao == PRODUCTION_ORIGIN, (
            f"Expected Access-Control-Allow-Origin: {PRODUCTION_ORIGIN!r}, got {acao!r}"
        )

    def test_dashboard_summary_preflight_allows_production_origin(self, client: TestClient):
        """OPTIONS /api/dashboard/summary must return Allow-Origin for the Vercel frontend."""
        resp = client.options(
            "/api/dashboard/summary",
            headers=_preflight_headers(PRODUCTION_ORIGIN, "/api/dashboard/summary"),
        )
        assert resp.status_code in (200, 204), (
            f"Expected 200/204 from preflight, got {resp.status_code}"
        )
        acao = resp.headers.get("access-control-allow-origin", "")
        assert acao == PRODUCTION_ORIGIN, (
            f"Expected Access-Control-Allow-Origin: {PRODUCTION_ORIGIN!r}, got {acao!r}"
        )

    def test_health_preflight_exposes_allow_methods(self, client: TestClient):
        """Preflight response must include Access-Control-Allow-Methods."""
        resp = client.options(
            "/api/health",
            headers=_preflight_headers(PRODUCTION_ORIGIN, "/api/health"),
        )
        methods = resp.headers.get("access-control-allow-methods", "")
        assert methods, "Access-Control-Allow-Methods header must not be empty"

    def test_health_preflight_exposes_allow_headers(self, client: TestClient):
        """Preflight response must include Access-Control-Allow-Headers."""
        resp = client.options(
            "/api/health",
            headers=_preflight_headers(PRODUCTION_ORIGIN, "/api/health"),
        )
        headers_val = resp.headers.get("access-control-allow-headers", "")
        assert headers_val, "Access-Control-Allow-Headers header must not be empty"


class TestCORSLocalOrigin:
    """Local development origins must also be accepted."""

    def test_health_preflight_allows_localhost(self, client: TestClient):
        resp = client.options(
            "/api/health",
            headers=_preflight_headers(LOCAL_ORIGIN, "/api/health"),
        )
        assert resp.status_code in (200, 204)
        acao = resp.headers.get("access-control-allow-origin", "")
        assert acao == LOCAL_ORIGIN, (
            f"Expected Access-Control-Allow-Origin: {LOCAL_ORIGIN!r}, got {acao!r}"
        )


class TestCORSBlockedOrigin:
    """Origins not in the allow-list must NOT receive Access-Control-Allow-Origin."""

    def test_blocked_origin_not_reflected(self, client: TestClient):
        resp = client.options(
            "/api/health",
            headers=_preflight_headers(BLOCKED_ORIGIN, "/api/health"),
        )
        acao = resp.headers.get("access-control-allow-origin", "")
        assert acao != BLOCKED_ORIGIN, (
            f"Blocked origin {BLOCKED_ORIGIN!r} must not be reflected in ACAO header"
        )


class TestCORSSimpleRequests:
    """Simple GET requests from the production origin must include CORS headers."""

    def test_health_get_includes_acao_header(self, client: TestClient):
        resp = client.get(
            "/api/health",
            headers={"Origin": PRODUCTION_ORIGIN},
        )
        acao = resp.headers.get("access-control-allow-origin", "")
        assert acao == PRODUCTION_ORIGIN, (
            f"Simple GET must return ACAO header for production origin; got {acao!r}"
        )


class TestCORSConfiguration:
    """Verify the CORS allow-list is configured correctly at the settings level."""

    def test_production_origin_in_default_allowed_origins(self):
        """Production Vercel URL must appear in the default ALLOWED_ORIGINS setting."""
        from app.config import settings
        origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
        assert PRODUCTION_ORIGIN in origins, (
            f"{PRODUCTION_ORIGIN!r} not found in ALLOWED_ORIGINS: {origins}"
        )

    def test_production_origin_guaranteed_in_main(self):
        """app/main.py must guarantee the production origin even if env var omits it."""
        from app.main import PRODUCTION_ORIGIN as MP, origins as configured_origins
        assert MP == PRODUCTION_ORIGIN
        assert PRODUCTION_ORIGIN in configured_origins, (
            f"Production origin not found in the origins list passed to CORSMiddleware: {configured_origins}"
        )
