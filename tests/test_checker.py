"""
Тесты для модуля checker.py
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from checker import (
    SiteReport,
    CheckResult,
    analyze,
    save_session,
    load_session,
    _check_title,
    _check_meta_description,
    _check_h1,
    _check_images,
    _check_viewport,
    _check_canonical,
    _check_open_graph,
    _check_https,
    _check_load_time,
    _check_lang,
    _check_favicon,
    _check_structured_data,
    _check_twitter_card,
    _check_heading_structure,
)
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def make_report() -> SiteReport:
    return SiteReport(url="https://example.com")


# ---------------------------------------------------------------------------
# SiteReport
# ---------------------------------------------------------------------------

class TestSiteReport:
    def test_score_empty(self):
        report = make_report()
        assert report.score == 0

    def test_score_all_passed(self):
        report = make_report()
        for i in range(5):
            report.add(CheckResult(f"check_{i}", True, "ok"))
        assert report.score == 100

    def test_score_half_passed(self):
        report = make_report()
        report.add(CheckResult("a", True, "ok"))
        report.add(CheckResult("b", False, "fail", "error"))
        assert report.score == 50

    def test_errors_and_warnings_collected(self):
        report = make_report()
        report.add(CheckResult("a", False, "err", "error"))
        report.add(CheckResult("b", False, "warn", "warning"))
        report.add(CheckResult("c", True, "ok"))
        assert len(report.errors) == 1
        assert len(report.warnings) == 1


# ---------------------------------------------------------------------------
# _check_title
# ---------------------------------------------------------------------------

class TestCheckTitle:
    def test_missing_title(self):
        soup = make_soup("<html><head></head></html>")
        report = make_report()
        _check_title(soup, report)
        assert not report.checks[-1].passed
        assert report.checks[-1].level == "error"

    def test_empty_title(self):
        soup = make_soup("<html><head><title>   </title></head></html>")
        report = make_report()
        _check_title(soup, report)
        assert not report.checks[-1].passed

    def test_short_title(self):
        soup = make_soup("<html><head><title>Hi</title></head></html>")
        report = make_report()
        _check_title(soup, report)
        assert not report.checks[-1].passed
        assert report.checks[-1].level == "warning"

    def test_long_title(self):
        long_title = "A" * 80
        soup = make_soup(f"<html><head><title>{long_title}</title></head></html>")
        report = make_report()
        _check_title(soup, report)
        assert not report.checks[-1].passed
        assert report.checks[-1].level == "warning"

    def test_good_title(self):
        soup = make_soup("<html><head><title>Хороший заголовок страницы</title></head></html>")
        report = make_report()
        _check_title(soup, report)
        assert report.checks[-1].passed


# ---------------------------------------------------------------------------
# _check_meta_description
# ---------------------------------------------------------------------------

class TestCheckMetaDescription:
    def test_missing(self):
        soup = make_soup("<html><head></head></html>")
        report = make_report()
        _check_meta_description(soup, report)
        assert not report.checks[-1].passed
        assert report.checks[-1].level == "error"

    def test_short(self):
        soup = make_soup('<html><head><meta name="description" content="Short"></head></html>')
        report = make_report()
        _check_meta_description(soup, report)
        assert not report.checks[-1].passed
        assert report.checks[-1].level == "warning"

    def test_long(self):
        long_desc = "A" * 200
        soup = make_soup(
            f'<html><head><meta name="description" content="{long_desc}"></head></html>'
        )
        report = make_report()
        _check_meta_description(soup, report)
        assert not report.checks[-1].passed
        assert report.checks[-1].level == "warning"

    def test_good(self):
        desc = "Это отличное описание страницы, которое соответствует всем рекомендациям."
        soup = make_soup(
            f'<html><head><meta name="description" content="{desc}"></head></html>'
        )
        report = make_report()
        _check_meta_description(soup, report)
        assert report.checks[-1].passed


# ---------------------------------------------------------------------------
# _check_h1
# ---------------------------------------------------------------------------

class TestCheckH1:
    def test_missing(self):
        soup = make_soup("<html><body><p>text</p></body></html>")
        report = make_report()
        _check_h1(soup, report)
        assert not report.checks[-1].passed
        assert report.checks[-1].level == "error"

    def test_multiple(self):
        soup = make_soup("<html><body><h1>One</h1><h1>Two</h1></body></html>")
        report = make_report()
        _check_h1(soup, report)
        assert not report.checks[-1].passed
        assert report.checks[-1].level == "warning"

    def test_single(self):
        soup = make_soup("<html><body><h1>Good heading</h1></body></html>")
        report = make_report()
        _check_h1(soup, report)
        assert report.checks[-1].passed


# ---------------------------------------------------------------------------
# _check_images
# ---------------------------------------------------------------------------

class TestCheckImages:
    def test_no_images(self):
        soup = make_soup("<html><body></body></html>")
        report = make_report()
        _check_images(soup, report)
        assert report.checks[-1].passed

    def test_all_have_alt(self):
        soup = make_soup('<html><body><img src="a.jpg" alt="A"><img src="b.jpg" alt="B"></body></html>')
        report = make_report()
        _check_images(soup, report)
        assert report.checks[-1].passed

    def test_some_missing_alt(self):
        soup = make_soup('<html><body><img src="a.jpg" alt="A"><img src="b.jpg"></body></html>')
        report = make_report()
        _check_images(soup, report)
        assert not report.checks[-1].passed
        assert report.checks[-1].level == "warning"


# ---------------------------------------------------------------------------
# _check_viewport
# ---------------------------------------------------------------------------

class TestCheckViewport:
    def test_missing(self):
        soup = make_soup("<html><head></head></html>")
        report = make_report()
        _check_viewport(soup, report)
        assert not report.checks[-1].passed
        assert report.checks[-1].level == "error"

    def test_present(self):
        soup = make_soup(
            '<html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head></html>'
        )
        report = make_report()
        _check_viewport(soup, report)
        assert report.checks[-1].passed


# ---------------------------------------------------------------------------
# _check_canonical
# ---------------------------------------------------------------------------

class TestCheckCanonical:
    def test_missing(self):
        soup = make_soup("<html><head></head></html>")
        report = make_report()
        _check_canonical(soup, report)
        assert not report.checks[-1].passed
        assert report.checks[-1].level == "warning"

    def test_present(self):
        soup = make_soup(
            '<html><head><link rel="canonical" href="https://example.com/page"></head></html>'
        )
        report = make_report()
        _check_canonical(soup, report)
        assert report.checks[-1].passed


# ---------------------------------------------------------------------------
# _check_open_graph
# ---------------------------------------------------------------------------

class TestCheckOpenGraph:
    def test_all_missing(self):
        soup = make_soup("<html><head></head></html>")
        report = make_report()
        _check_open_graph(soup, report)
        assert not report.checks[-1].passed

    def test_all_present(self):
        soup = make_soup(
            '<html><head>'
            '<meta property="og:title" content="T">'
            '<meta property="og:description" content="D">'
            '<meta property="og:image" content="I">'
            '</head></html>'
        )
        report = make_report()
        _check_open_graph(soup, report)
        assert report.checks[-1].passed


# ---------------------------------------------------------------------------
# _check_https
# ---------------------------------------------------------------------------

class TestCheckHttps:
    def test_https(self):
        report = make_report()
        _check_https("https://example.com", report)
        assert report.checks[-1].passed

    def test_http(self):
        report = make_report()
        _check_https("http://example.com", report)
        assert not report.checks[-1].passed
        assert report.checks[-1].level == "error"


# ---------------------------------------------------------------------------
# _check_load_time
# ---------------------------------------------------------------------------

class TestCheckLoadTime:
    def test_fast(self):
        report = make_report()
        _check_load_time(0.5, report)
        assert report.checks[-1].passed

    def test_medium(self):
        report = make_report()
        _check_load_time(3.0, report)
        assert not report.checks[-1].passed
        assert report.checks[-1].level == "warning"

    def test_slow(self):
        report = make_report()
        _check_load_time(5.0, report)
        assert not report.checks[-1].passed
        assert report.checks[-1].level == "error"


# ---------------------------------------------------------------------------
# _check_lang
# ---------------------------------------------------------------------------

class TestCheckLang:
    def test_missing_lang(self):
        soup = make_soup("<html><head></head></html>")
        report = make_report()
        _check_lang(soup, report)
        assert not report.checks[-1].passed
        assert report.checks[-1].level == "warning"

    def test_empty_lang(self):
        soup = make_soup('<html lang=""><head></head></html>')
        report = make_report()
        _check_lang(soup, report)
        assert not report.checks[-1].passed

    def test_present_lang(self):
        soup = make_soup('<html lang="ru"><head></head></html>')
        report = make_report()
        _check_lang(soup, report)
        assert report.checks[-1].passed
        assert "ru" in report.checks[-1].message

    def test_present_lang_en(self):
        soup = make_soup('<html lang="en-US"><head></head></html>')
        report = make_report()
        _check_lang(soup, report)
        assert report.checks[-1].passed


# ---------------------------------------------------------------------------
# _check_favicon
# ---------------------------------------------------------------------------

class TestCheckFavicon:
    def test_favicon_in_html(self):
        soup = make_soup(
            '<html><head><link rel="icon" href="/favicon.ico"></head></html>'
        )
        report = make_report()
        _check_favicon(soup, "https://example.com", report)
        assert report.checks[-1].passed

    def test_favicon_shortcut_icon(self):
        soup = make_soup(
            '<html><head><link rel="shortcut icon" href="/favicon.ico"></head></html>'
        )
        report = make_report()
        _check_favicon(soup, "https://example.com", report)
        assert report.checks[-1].passed

    @patch("checker.requests.get")
    def test_favicon_via_http_found(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        soup = make_soup("<html><head></head></html>")
        report = make_report()
        _check_favicon(soup, "https://example.com", report)
        assert report.checks[-1].passed

    @patch("checker.requests.get")
    def test_favicon_not_found(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp
        soup = make_soup("<html><head></head></html>")
        report = make_report()
        _check_favicon(soup, "https://example.com", report)
        assert not report.checks[-1].passed
        assert report.checks[-1].level == "warning"


# ---------------------------------------------------------------------------
# _check_structured_data
# ---------------------------------------------------------------------------

class TestCheckStructuredData:
    def test_missing(self):
        soup = make_soup("<html><head></head></html>")
        report = make_report()
        _check_structured_data(soup, report)
        assert not report.checks[-1].passed
        assert report.checks[-1].level == "warning"

    def test_valid_json_ld(self):
        html = (
            '<html><head>'
            '<script type="application/ld+json">{"@context":"https://schema.org","@type":"WebSite"}</script>'
            '</head></html>'
        )
        soup = make_soup(html)
        report = make_report()
        _check_structured_data(soup, report)
        assert report.checks[-1].passed

    def test_invalid_json_ld(self):
        html = (
            '<html><head>'
            '<script type="application/ld+json">not valid json</script>'
            '</head></html>'
        )
        soup = make_soup(html)
        report = make_report()
        _check_structured_data(soup, report)
        assert not report.checks[-1].passed

    def test_mixed_json_ld(self):
        html = (
            '<html><head>'
            '<script type="application/ld+json">{"@type":"WebSite"}</script>'
            '<script type="application/ld+json">bad json</script>'
            '</head></html>'
        )
        soup = make_soup(html)
        report = make_report()
        _check_structured_data(soup, report)
        assert not report.checks[-1].passed


# ---------------------------------------------------------------------------
# _check_twitter_card
# ---------------------------------------------------------------------------

class TestCheckTwitterCard:
    def test_all_missing(self):
        soup = make_soup("<html><head></head></html>")
        report = make_report()
        _check_twitter_card(soup, report)
        assert not report.checks[-1].passed
        assert report.checks[-1].level == "warning"

    def test_all_present(self):
        html = (
            '<html><head>'
            '<meta name="twitter:card" content="summary">'
            '<meta name="twitter:title" content="Title">'
            '<meta name="twitter:description" content="Description">'
            '</head></html>'
        )
        soup = make_soup(html)
        report = make_report()
        _check_twitter_card(soup, report)
        assert report.checks[-1].passed

    def test_partial(self):
        html = (
            '<html><head>'
            '<meta name="twitter:card" content="summary">'
            '</head></html>'
        )
        soup = make_soup(html)
        report = make_report()
        _check_twitter_card(soup, report)
        assert not report.checks[-1].passed
        assert "twitter:title" in report.checks[-1].message
        assert "twitter:description" in report.checks[-1].message


# ---------------------------------------------------------------------------
# _check_heading_structure
# ---------------------------------------------------------------------------

class TestCheckHeadingStructure:
    def test_no_headings(self):
        soup = make_soup("<html><body><p>text</p></body></html>")
        report = make_report()
        _check_heading_structure(soup, report)
        assert not report.checks[-1].passed
        assert report.checks[-1].level == "warning"

    def test_correct_structure(self):
        soup = make_soup(
            "<html><body><h1>Main</h1><h2>Section</h2><h3>Sub</h3></body></html>"
        )
        report = make_report()
        _check_heading_structure(soup, report)
        assert report.checks[-1].passed

    def test_skipped_level(self):
        soup = make_soup(
            "<html><body><h1>Main</h1><h3>Skipped h2</h3></body></html>"
        )
        report = make_report()
        _check_heading_structure(soup, report)
        assert not report.checks[-1].passed
        assert "h1→h3" in report.checks[-1].message

    def test_only_h1(self):
        soup = make_soup("<html><body><h1>Only heading</h1></body></html>")
        report = make_report()
        _check_heading_structure(soup, report)
        assert report.checks[-1].passed


# ---------------------------------------------------------------------------
# analyze (integration-level with mocked HTTP)
# ---------------------------------------------------------------------------

MINIMAL_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>Пример хорошей страницы для теста</title>
  <meta name="description" content="Это подробное описание страницы для тестирования модуля Cheker.">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="canonical" href="https://example.com/">
  <meta property="og:title" content="Title">
  <meta property="og:description" content="Desc">
  <meta property="og:image" content="img.jpg">
</head>
<body>
  <h1>Заголовок страницы</h1>
  <img src="cat.jpg" alt="Кот">
</body>
</html>"""


def _make_mock_response(url: str = "https://example.com", status: int = 200, text: str = MINIMAL_HTML):
    mock_resp = MagicMock()
    mock_resp.status_code = status
    mock_resp.text = text
    mock_resp.url = url
    return mock_resp


class TestAnalyze:
    def _mock_requests_get(self, url, **kwargs):
        return _make_mock_response(url=url)

    @patch("checker.requests.get")
    def test_good_page(self, mock_get):
        mock_get.return_value = _make_mock_response()
        report = analyze("https://example.com")
        assert report.status_code == 200
        assert report.score > 50

    @patch("checker.requests.get")
    def test_http_error(self, mock_get):
        mock_get.return_value = _make_mock_response(status=404)
        report = analyze("https://example.com")
        assert report.status_code == 404
        assert any(not c.passed for c in report.checks)

    @patch("checker.requests.get")
    def test_connection_error(self, mock_get):
        import requests as req_lib
        mock_get.side_effect = req_lib.RequestException("timeout")
        report = analyze("https://unreachable.example")
        assert any(not c.passed for c in report.checks)

    @patch("checker.requests.get")
    def test_url_scheme_added(self, mock_get):
        mock_get.return_value = _make_mock_response(url="https://example.com")
        report = analyze("example.com")
        assert report.url.startswith("https://")


# ---------------------------------------------------------------------------
# Session persistence
# ---------------------------------------------------------------------------

class TestSession:
    def test_save_and_load(self, tmp_path, monkeypatch):
        session_file = tmp_path / ".cheker_session.json"
        monkeypatch.setattr("checker._SESSION_FILE", str(session_file))
        save_session("https://example.com")
        assert load_session() == "https://example.com"

    def test_load_missing_file(self, tmp_path, monkeypatch):
        session_file = tmp_path / ".cheker_session.json"
        monkeypatch.setattr("checker._SESSION_FILE", str(session_file))
        assert load_session() is None

    def test_load_corrupt_file(self, tmp_path, monkeypatch):
        session_file = tmp_path / ".cheker_session.json"
        session_file.write_text("not valid json", encoding="utf-8")
        monkeypatch.setattr("checker._SESSION_FILE", str(session_file))
        assert load_session() is None

    def test_save_overwrites(self, tmp_path, monkeypatch):
        session_file = tmp_path / ".cheker_session.json"
        monkeypatch.setattr("checker._SESSION_FILE", str(session_file))
        save_session("https://first.com")
        save_session("https://second.com")
        assert load_session() == "https://second.com"


# ---------------------------------------------------------------------------
# CLI --repeat flag
# ---------------------------------------------------------------------------

class TestCLIRepeat:
    @patch("checker.requests.get")
    def test_repeat_no_session(self, mock_get, tmp_path, monkeypatch, capsys):
        import cli
        session_file = tmp_path / ".cheker_session.json"
        monkeypatch.setattr("checker._SESSION_FILE", str(session_file))
        result = cli.main(["--repeat"])
        assert result == 1
        captured = capsys.readouterr()
        assert "нет сохранённой сессии" in captured.err

    @patch("checker.requests.get")
    def test_repeat_uses_last_url(self, mock_get, tmp_path, monkeypatch, capsys):
        import cli
        session_file = tmp_path / ".cheker_session.json"
        monkeypatch.setattr("checker._SESSION_FILE", str(session_file))
        mock_get.return_value = _make_mock_response()
        # First run to save session
        cli.main(["https://example.com", "--no-color"])
        # Repeat
        mock_get.return_value = _make_mock_response()
        result = cli.main(["--repeat", "--no-color"])
        captured = capsys.readouterr()
        assert "Повтор последней сессии: https://example.com" in captured.out

    @patch("checker.requests.get")
    def test_no_url_no_repeat_prints_error(self, mock_get, tmp_path, monkeypatch):
        import cli
        with pytest.raises(SystemExit):
            cli.main([])
