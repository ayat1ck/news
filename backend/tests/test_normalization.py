"""Unit tests for the normalization pipeline."""

from app.workers.pipeline.normalization import normalize_text


def test_normalize_strips_html():
    """Test HTML tag removal."""
    result = normalize_text("<p>Hello <b>world</b></p>", "")
    assert "<" not in result
    assert "Hello" in result
    assert "world" in result


def test_normalize_whitespace():
    """Test whitespace normalization."""
    result = normalize_text("Hello    world\n\n\n\ntest", "")
    assert "    " not in result
    assert "\n\n\n" not in result


def test_normalize_tracking_params():
    """Test tracking parameter removal from URLs."""
    result = normalize_text("Visit https://example.com?utm_source=twitter&utm_medium=social", "")
    assert "utm_source" not in result
    assert "utm_medium" not in result


def test_normalize_html_extraction():
    """Test extraction from raw HTML."""
    html = "<html><body><h1>Title</h1><p>Content here</p><script>evil()</script></body></html>"
    result = normalize_text("", html)
    assert "Content" in result or "Title" in result
    assert "evil()" not in result


def test_normalize_empty():
    """Test empty input."""
    result = normalize_text("", "")
    assert result == ""
