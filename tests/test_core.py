import pytest

from hbg_free_material.core import (
    StockImagesError,
    _extension,
    provider_status,
    select_round_robin,
    validate_pixabay_audio_url,
)


def test_provider_status_ignores_placeholders(monkeypatch):
    monkeypatch.setenv("PEXELS_API_KEY", "your_pexels_api_key")
    monkeypatch.setenv("UNSPLASH_API_KEY", "")
    monkeypatch.setenv("PIXABAY_API_KEY", "configured")
    assert provider_status() == {
        "pexels": False,
        "unsplash": False,
        "pixabay": True,
    }


def test_round_robin_balances_providers():
    items = [
        {"platform": "pexels", "id": "p1"},
        {"platform": "pexels", "id": "p2"},
        {"platform": "unsplash", "id": "u1"},
        {"platform": "pixabay", "id": "x1"},
    ]
    assert [item["id"] for item in select_round_robin(items, 4)] == ["p1", "u1", "x1", "p2"]


def test_pixabay_audio_url_is_strict():
    validate_pixabay_audio_url("https://cdn.pixabay.com/audio/2026/01/demo.mp3")
    with pytest.raises(StockImagesError):
        validate_pixabay_audio_url("https://example.com/audio/demo.mp3")
    with pytest.raises(StockImagesError):
        validate_pixabay_audio_url("http://cdn.pixabay.com/audio/demo.mp3")


def test_extension_falls_back_by_media_kind():
    assert _extension("video/mp4", "https://example.com/file", "video") == ".mp4"
    assert _extension("", "https://example.com/no-suffix", "audio") == ".mp3"
