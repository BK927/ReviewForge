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
        checks = [
            ("GET", "/health", None),
            ("GET", "/api/dashboard", None),
            ("GET", "/api/languages", None),
            ("GET", "/api/events", None),
            ("GET", "/api/clusters", None),
            ("GET", "/api/evidence", None),
            ("GET", "/api/reports", None),
            ("GET", "/api/settings", None),
            ("GET", "/api/jobs", None),
            ("POST", "/api/refresh-steam", {"max_reviews": 2, "use_live_steam": False}),
        ]
        for method, path, payload in checks:
            response = client.request(method, path, json=payload)
            response.raise_for_status()

print("ReviewForge backend smoke test passed.")
