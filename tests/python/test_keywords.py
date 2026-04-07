import pytest
from python.keywords import extract_keywords_yake, extract_keywords_embedding


def test_yake_extracts_keywords():
    texts = [
        "The server lag is terrible and matchmaking takes forever",
        "Server issues are ruining the game, constant lag spikes",
        "Lag and server problems make this unplayable"
    ]
    keywords = extract_keywords_yake(texts, top_n=5)
    assert len(keywords) > 0
    assert len(keywords) <= 5
    # "server" or "lag" should appear in top keywords
    kw_lower = [k[0].lower() for k in keywords]
    assert any("server" in k or "lag" in k for k in kw_lower)


def test_yake_handles_empty():
    keywords = extract_keywords_yake([], top_n=5)
    assert keywords == []
