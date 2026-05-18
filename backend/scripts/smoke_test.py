from pathlib import Path
import os
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

with tempfile.TemporaryDirectory() as tmpdir:
    os.environ["REVIEWFORGE_DB_PATH"] = str(Path(tmpdir) / "reviewforge-smoke.duckdb")

    from fastapi.testclient import TestClient
    from backend.app.main import app

    with TestClient(app) as client:
        read_checks = [
            ("GET", "/health", None),
            ("GET", "/api/dashboard", None),
            ("GET", "/api/languages", None),
            ("GET", "/api/events", None),
            ("GET", "/api/clusters", None),
            ("GET", "/api/evidence", None),
            ("GET", "/api/reports", None),
            ("GET", "/api/settings", None),
            ("GET", "/api/settings/models", None),
            ("GET", "/api/jobs", None),
        ]
        for method, path, payload in read_checks:
            response = client.request(method, path, json=payload)
            response.raise_for_status()

        refresh = client.post("/api/refresh-steam", json={"max_reviews": 5, "use_live_steam": False})
        refresh.raise_for_status()
        refresh_payload = refresh.json()
        assert refresh_payload["source"] == "sample"
        assert "next_cursor" in refresh_payload
        assert "has_more" in refresh_payload

        analysis = client.post("/api/analysis-runs", json={"scope": "all", "min_cluster_size": 2})
        analysis.raise_for_status()
        analysis_payload = analysis.json()
        assert analysis_payload["analysis_run"]["status"] == "succeeded"
        assert analysis_payload["reviews_analyzed"] >= 1

        for path in [
            "/api/analysis-runs",
            "/api/clusters",
            "/api/evidence",
            "/api/timeline?bucket=day",
        ]:
            response = client.get(path)
            response.raise_for_status()
            assert response.json()

        events = client.get("/api/events")
        events.raise_for_status()
        event_id = events.json()[0]["id"]
        impact = client.get(f"/api/events/{event_id}/impact?window_days=14")
        impact.raise_for_status()

print("ReviewForge backend smoke test passed.")
