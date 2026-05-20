from pathlib import Path
import os
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.check_docs import check_repository

doc_errors = check_repository(ROOT)
assert not doc_errors, "Documentation guard failed:\n" + "\n".join(f"- {error}" for error in doc_errors)

with tempfile.TemporaryDirectory() as tmpdir:
    os.environ["REVIEWFORGE_DB_PATH"] = str(Path(tmpdir) / "reviewforge-smoke.duckdb")

    from fastapi.testclient import TestClient
    from backend.app.main import app
    from backend.app.analysis import IssueAspect, _build_issue_card

    def issue_unit(review_id, text, intent, aspect, voted_up=False):
        return {
            "review": {"weighted_vote_score": 0.8},
            "review_id": review_id,
            "unit_text": text,
            "language": "en",
            "voted_up": voted_up,
            "intent": intent,
            "aspect": aspect,
            "quality_score": 0.9,
            "text_hash": f"hash-{review_id}",
        }

    content_aspect = IssueAspect(
        "content_volume",
        "분량/완성도",
        r"content|route|ending",
        "플레이 분량과 완성도 신호입니다.",
        "가격/분량 기대와 실제 플레이 루프를 나눠 확인하세요.",
    )
    route_card = _build_issue_card(
        "content_volume",
        "complaint",
        [
            issue_unit(
                "route-1",
                "The route choice needs a clearer guide and manual save support.",
                "complaint",
                "content_volume",
            ),
            issue_unit(
                "route-2",
                "Ending route hints are missing, so I needed a walkthrough and save slots.",
                "complaint",
                "content_volume",
            ),
            issue_unit(
                "route-3",
                "Choices and gallery unlock routes are hard to track without a guide.",
                "complaint",
                "content_volume",
            ),
        ],
        None,
        1000,
        [content_aspect],
    )
    assert route_card["title"].startswith("루트/선택지 안내와 세이브 편의")
    assert "추천 액션(개선/확장)" in route_card["recommended_action"]

    story_aspect = IssueAspect(
        "story_logic",
        "스토리/세계관/엔딩",
        r"story|character|art",
        "스토리와 캐릭터 신호입니다.",
        "강점이면 후속작과 홍보의 핵심 약속으로 쓸 수 있는지 확인하세요.",
    )
    praise_card = _build_issue_card(
        "story_logic",
        "praise",
        [
            issue_unit(
                "praise-1",
                "The character art and music are amazing, easy to recommend.",
                "praise",
                "story_logic",
                True,
            ),
            issue_unit(
                "praise-2",
                "I love the characters, visual art, and voice acting.",
                "praise",
                "story_logic",
                True,
            ),
            issue_unit(
                "praise-3",
                "Great story presentation with memorable character CG and music.",
                "praise",
                "story_logic",
                True,
            ),
        ],
        None,
        1000,
        [story_aspect],
    )
    assert praise_card["title"].startswith("캐릭터/아트/연출 매력")
    assert "추천 액션(홍보 문구/확장)" in praise_card["recommended_action"]

    with TestClient(app) as client:
        read_checks = [
            ("GET", "/health", None),
            ("GET", "/api/dashboard", None),
            ("GET", "/api/languages", None),
            ("GET", "/api/games", None),
            ("GET", "/api/events", None),
            ("GET", "/api/clusters", None),
            ("GET", "/api/evidence", None),
            ("GET", "/api/claims", None),
            ("GET", "/api/issues", None),
            ("GET", "/api/issues/summary", None),
            ("GET", "/api/reports", None),
            ("GET", "/api/settings", None),
            ("GET", "/api/settings/models", None),
            ("GET", "/api/jobs", None),
        ]
        for method, path, payload in read_checks:
            response = client.request(method, path, json=payload)
            response.raise_for_status()

        games = client.get("/api/games")
        games.raise_for_status()
        default_game = games.json()[0]
        assert default_game["app_id"] == "1145350"
        assert default_game["review_count"] >= 1
        assert "next_action" in default_game
        assert "cluster_count" in default_game

        created_game = client.post(
            "/api/games",
            json={"app_id": "999001", "name": "Smoke Test Game", "short_name": "STG", "tags": ["smoke"]},
        )
        created_game.raise_for_status()
        assert created_game.json()["name"] == "Smoke Test Game"
        assert created_game.json()["short_name"] == "STG"
        assert created_game.json()["tags"] == ["smoke"]

        updated_game = client.patch("/api/games/999001", json={"name": "Smoke Test Game Updated", "note": "patched"})
        updated_game.raise_for_status()
        assert updated_game.json()["name"] == "Smoke Test Game Updated"
        assert updated_game.json()["note"] == "patched"

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
        assert analysis_payload["clusters_created"] >= 1
        assert analysis_payload["evidence_created"] >= 1
        assert "issues_created" in analysis_payload
        assert "issue_evidence_created" in analysis_payload

        scoped_refresh = client.post(
            "/api/refresh-steam",
            json={"app_id": "999001", "max_reviews": 3, "use_live_steam": False},
        )
        scoped_refresh.raise_for_status()
        scoped_dashboard = client.get("/api/dashboard?app_id=999001")
        scoped_dashboard.raise_for_status()
        assert scoped_dashboard.json()["total_reviews"] == 3
        assert client.get("/api/languages?app_id=999001").json()

        for path in [
            "/api/analysis-runs",
            "/api/clusters",
            "/api/evidence",
            "/api/claims",
            "/api/issues/summary",
            "/api/timeline?bucket=day",
        ]:
            response = client.get(path)
            response.raise_for_status()
            assert response.json()

        issues_payload = client.get("/api/issues").json()
        if issues_payload:
            issue_id = issues_payload[0]["id"]
            issue_evidence = client.get(f"/api/issues/{issue_id}/evidence")
            issue_evidence.raise_for_status()

        cluster_id = client.get("/api/clusters").json()[0]["id"]
        cluster_payload = client.get("/api/clusters").json()
        assert cluster_payload[0]["top_keywords"]
        assert cluster_payload[0]["keyword_method"] in {"ctfidf", "frequency"}
        assert cluster_payload[0]["label_source"] in {"game_theme", "common_theme", "keyword", "fallback"}
        assert cluster_payload[0]["label_confidence"] in {"high", "medium", "low"}
        assert isinstance(cluster_payload[0]["label_warnings"], list)
        assert isinstance(cluster_payload[0]["matched_terms"], list)
        assert cluster_payload[0]["insight"]["source"] == "deterministic"
        sampled_reviews = client.get(f"/api/clusters/{cluster_id}/reviews?sample=complaint&limit=5")
        sampled_reviews.raise_for_status()
        assert sampled_reviews.json()
        assert "quality_flags" in sampled_reviews.json()[0]

        evidence_payload = client.get("/api/evidence").json()
        assert "claim_text" in evidence_payload[0]
        assert evidence_payload[0]["claim_id"] is not None
        evidence_quotes = [item["quote"] for item in evidence_payload]
        assert len(evidence_quotes) == len(set(evidence_quotes))

        events = client.get("/api/events")
        events.raise_for_status()
        event_id = events.json()[0]["id"]
        impact = client.get(f"/api/events/{event_id}/impact?window_days=14")
        impact.raise_for_status()

        deleted_game = client.delete("/api/games/999001")
        deleted_game.raise_for_status()
        assert deleted_game.json()["deleted"] is True

print("ReviewForge backend smoke test passed.")
