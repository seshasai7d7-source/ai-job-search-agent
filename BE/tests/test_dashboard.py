import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from dashboard import app as dashboard


def test_overlap_display_is_clear_and_null_is_not_a_score():
    assert dashboard.display_skills_overlap(None) == "Not enough data"
    assert dashboard.display_skills_overlap(67.04) == "67.0%"


def test_dashboard_api_client_uses_configured_local_api(monkeypatch):
    seen = {}

    def fake_request(method, url, **kwargs):
        seen["method"] = method
        seen["url"] = url
        seen["kwargs"] = kwargs
        return SimpleNamespace(is_error=False, content=b"{}", json=lambda: {"status": "ok"})

    monkeypatch.setattr(dashboard, "API_BASE_URL", "http://127.0.0.1:8123")
    monkeypatch.setattr(dashboard.httpx, "request", fake_request)

    result = dashboard.api_request("GET", "/health")

    assert result == {"status": "ok"}
    assert seen["url"] == "http://127.0.0.1:8123/health"
    assert seen["kwargs"]["timeout"] == 30


def test_dashboard_surfaces_api_errors(monkeypatch):
    monkeypatch.setattr(
        dashboard.httpx,
        "request",
        lambda *args, **kwargs: SimpleNamespace(
            is_error=True,
            status_code=409,
            text="",
            json=lambda: {"detail": "Profile approval required"},
        ),
    )

    with pytest.raises(RuntimeError, match="409: Profile approval required"):
        dashboard.api_request("POST", "/matches/recompute")


def test_dashboard_does_not_import_or_access_database():
    dashboard_path = Path(__file__).resolve().parents[1] / "dashboard" / "app.py"
    syntax = ast.parse(dashboard_path.read_text(encoding="utf-8"))
    imported_modules = []
    for node in ast.walk(syntax):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported_modules.append(node.module or "")

    assert not any(
        module.startswith(("sqlalchemy", "app.database"))
        for module in imported_modules
    )
