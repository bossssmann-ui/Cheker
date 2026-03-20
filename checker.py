"""
Cheker — модуль для анализа сайтов на SEO-ошибки и технические проблемы.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

_SESSION_FILE = os.path.join(os.path.expanduser("~"), ".cheker_session.json")


def save_session(url: str) -> None:
    """Сохраняет URL последней сессии в файл."""
    with open(_SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_url": url}, f)


def load_session() -> Optional[str]:
    """Загружает URL последней сессии из файла.

    Возвращает None, если файл не найден, повреждён или не содержит ключ 'last_url'.
    """
    try:
        with open(_SESSION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("last_url")
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return None

TIMEOUT = 10  # seconds


@dataclass
class CheckResult:
    """Результат одной проверки."""

    name: str
    passed: bool
    message: str
    level: str = "info"  # "info", "warning", "error"


@dataclass
class SiteReport:
    """Полный отчёт по сайту."""

    url: str
    status_code: Optional[int] = None
    load_time: Optional[float] = None
    checks: List[CheckResult] = field(default_factory=list)
    errors: List[CheckResult] = field(default_factory=list)
    warnings: List[CheckResult] = field(default_factory=list)

    def add(self, result: CheckResult) -> None:
        self.checks.append(result)
        if not result.passed:
            if result.level == "error":
                self.errors.append(result)
            elif result.level == "warning":
                self.warnings.append(result)

    @property
    def score(self) -> int:
        """Оценка сайта от 0 до 100."""
        if not self.checks:
            return 0
        passed = sum(1 for c in self.checks if c.passed)
        return round(passed / len(self.checks) * 100)


def _fetch(url: str) -> tuple[Optional[requests.Response], float]:
    """Загружает страницу и возвращает (response, time_seconds)."""
    start = time.monotonic()
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; Cheker/1.0; "
                "+https://github.com/bossssmann-ui/Cheker)"
            )
        }
        response = requests.get(url, timeout=TIMEOUT, headers=headers, allow_redirects=True)
        elapsed = time.monotonic() - start
        return response, elapsed
    except requests.RequestException:
        elapsed = time.monotonic() - start
        return None, elapsed


def _check_title(soup: BeautifulSoup, report: SiteReport) -> None:
    title_tag = soup.find("title")
    if not title_tag or not title_tag.get_text(strip=True):
        report.add(CheckResult("title", False, "Тег <title> отсутствует", "error"))
        return
    title = title_tag.get_text(strip=True)
    length = len(title)
    if length < 10:
        report.add(
            CheckResult(
                "title",
                False,
                f"Тег <title> слишком короткий ({length} симв.; рекомендуется 10–70)",
                "warning",
            )
        )
    elif length > 70:
        report.add(
            CheckResult(
                "title",
                False,
                f"Тег <title> слишком длинный ({length} симв.; рекомендуется 10–70)",
                "warning",
            )
        )
    else:
        report.add(
            CheckResult("title", True, f"Тег <title> в норме ({length} симв.): «{title}»")
        )


def _check_meta_description(soup: BeautifulSoup, report: SiteReport) -> None:
    tag = soup.find("meta", attrs={"name": "description"})
    if not tag or not tag.get("content", "").strip():
        report.add(
            CheckResult("meta_description", False, "Meta description отсутствует", "error")
        )
        return
    content = tag["content"].strip()
    length = len(content)
    if length < 50:
        report.add(
            CheckResult(
                "meta_description",
                False,
                f"Meta description слишком короткий ({length} симв.; рекомендуется 50–160)",
                "warning",
            )
        )
    elif length > 160:
        report.add(
            CheckResult(
                "meta_description",
                False,
                f"Meta description слишком длинный ({length} симв.; рекомендуется 50–160)",
                "warning",
            )
        )
    else:
        report.add(
            CheckResult(
                "meta_description",
                True,
                f"Meta description в норме ({length} симв.)",
            )
        )


def _check_h1(soup: BeautifulSoup, report: SiteReport) -> None:
    h1_tags = soup.find_all("h1")
    if not h1_tags:
        report.add(CheckResult("h1", False, "Тег <h1> отсутствует", "error"))
    elif len(h1_tags) > 1:
        report.add(
            CheckResult(
                "h1",
                False,
                f"На странице {len(h1_tags)} тегов <h1>; рекомендуется один",
                "warning",
            )
        )
    else:
        text = h1_tags[0].get_text(strip=True)
        report.add(CheckResult("h1", True, f"Тег <h1> присутствует: «{text[:60]}»"))


def _check_images(soup: BeautifulSoup, report: SiteReport) -> None:
    images = soup.find_all("img")
    if not images:
        report.add(CheckResult("images_alt", True, "Изображений на странице нет"))
        return
    missing = [img.get("src", "") for img in images if not img.get("alt")]
    if missing:
        report.add(
            CheckResult(
                "images_alt",
                False,
                f"{len(missing)} из {len(images)} изображений без атрибута alt",
                "warning",
            )
        )
    else:
        report.add(
            CheckResult(
                "images_alt", True, f"Все {len(images)} изображений имеют атрибут alt"
            )
        )


def _check_viewport(soup: BeautifulSoup, report: SiteReport) -> None:
    tag = soup.find("meta", attrs={"name": "viewport"})
    if not tag:
        report.add(
            CheckResult(
                "viewport",
                False,
                "Мета-тег viewport отсутствует (страница не адаптирована для мобильных)",
                "error",
            )
        )
    else:
        report.add(CheckResult("viewport", True, "Мета-тег viewport присутствует"))


def _check_canonical(soup: BeautifulSoup, report: SiteReport) -> None:
    tag = soup.find("link", attrs={"rel": "canonical"})
    if not tag or not tag.get("href"):
        report.add(
            CheckResult(
                "canonical",
                False,
                "Canonical-ссылка отсутствует",
                "warning",
            )
        )
    else:
        report.add(
            CheckResult("canonical", True, f"Canonical: {tag['href']}")
        )


def _check_open_graph(soup: BeautifulSoup, report: SiteReport) -> None:
    og_title = soup.find("meta", attrs={"property": "og:title"})
    og_desc = soup.find("meta", attrs={"property": "og:description"})
    og_image = soup.find("meta", attrs={"property": "og:image"})
    missing = []
    if not og_title:
        missing.append("og:title")
    if not og_desc:
        missing.append("og:description")
    if not og_image:
        missing.append("og:image")
    if missing:
        report.add(
            CheckResult(
                "open_graph",
                False,
                f"Отсутствуют Open Graph теги: {', '.join(missing)}",
                "warning",
            )
        )
    else:
        report.add(CheckResult("open_graph", True, "Основные Open Graph теги присутствуют"))


def _check_https(url: str, report: SiteReport) -> None:
    parsed = urlparse(url)
    if parsed.scheme == "https":
        report.add(CheckResult("https", True, "Сайт использует HTTPS"))
    else:
        report.add(
            CheckResult("https", False, "Сайт не использует HTTPS", "error")
        )


def _check_load_time(load_time: float, report: SiteReport) -> None:
    if load_time <= 2.0:
        report.add(
            CheckResult(
                "load_time",
                True,
                f"Время загрузки: {load_time:.2f} с (отлично)",
            )
        )
    elif load_time <= 4.0:
        report.add(
            CheckResult(
                "load_time",
                False,
                f"Время загрузки: {load_time:.2f} с (рекомендуется до 2 с)",
                "warning",
            )
        )
    else:
        report.add(
            CheckResult(
                "load_time",
                False,
                f"Время загрузки: {load_time:.2f} с (слишком медленно)",
                "error",
            )
        )


def _check_robots_txt(base_url: str, report: SiteReport) -> None:
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        resp = requests.get(robots_url, timeout=TIMEOUT)
        if resp.status_code == 200:
            report.add(CheckResult("robots_txt", True, f"robots.txt найден: {robots_url}"))
        else:
            report.add(
                CheckResult(
                    "robots_txt",
                    False,
                    f"robots.txt не найден (HTTP {resp.status_code})",
                    "warning",
                )
            )
    except requests.RequestException:
        report.add(
            CheckResult("robots_txt", False, "Не удалось проверить robots.txt", "warning")
        )


def _check_sitemap(soup: BeautifulSoup, base_url: str, report: SiteReport) -> None:
    # Check <link rel="sitemap"> in HTML
    tag = soup.find("link", attrs={"rel": "sitemap"})
    if tag and tag.get("href"):
        report.add(CheckResult("sitemap", True, f"Sitemap в HTML: {tag['href']}"))
        return
    # Check common path
    parsed = urlparse(base_url)
    sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
    try:
        resp = requests.get(sitemap_url, timeout=TIMEOUT)
        if resp.status_code == 200:
            report.add(CheckResult("sitemap", True, f"sitemap.xml найден: {sitemap_url}"))
        else:
            report.add(
                CheckResult(
                    "sitemap",
                    False,
                    "sitemap.xml не найден",
                    "warning",
                )
            )
    except requests.RequestException:
        report.add(
            CheckResult("sitemap", False, "Не удалось проверить sitemap.xml", "warning")
        )


def _check_lang(soup: BeautifulSoup, report: SiteReport) -> None:
    """Проверяет наличие атрибута lang у тега <html>."""
    html_tag = soup.find("html")
    if not html_tag or not html_tag.get("lang", "").strip():
        report.add(
            CheckResult(
                "lang",
                False,
                "Атрибут lang отсутствует у тега <html> (важно для SEO и доступности)",
                "warning",
            )
        )
    else:
        lang = html_tag["lang"].strip()
        report.add(CheckResult("lang", True, f"Атрибут lang задан: «{lang}»"))


def _check_favicon(soup: BeautifulSoup, base_url: str, report: SiteReport) -> None:
    """Проверяет наличие favicon."""
    # Check <link rel="icon"> or <link rel="shortcut icon"> in HTML
    icon_tag = soup.find("link", attrs={"rel": ["icon", "shortcut icon"]})
    if icon_tag and icon_tag.get("href"):
        report.add(CheckResult("favicon", True, f"Favicon найден в HTML: {icon_tag['href']}"))
        return
    # Try standard /favicon.ico path
    parsed = urlparse(base_url)
    favicon_url = f"{parsed.scheme}://{parsed.netloc}/favicon.ico"
    try:
        resp = requests.get(favicon_url, timeout=TIMEOUT)
        if resp.status_code == 200:
            report.add(CheckResult("favicon", True, f"favicon.ico найден: {favicon_url}"))
        else:
            report.add(
                CheckResult("favicon", False, "Favicon не найден", "warning")
            )
    except requests.RequestException:
        report.add(
            CheckResult("favicon", False, "Не удалось проверить favicon", "warning")
        )


def _check_structured_data(soup: BeautifulSoup, report: SiteReport) -> None:
    """Проверяет наличие структурированных данных (JSON-LD / Schema.org)."""
    json_ld_tags = soup.find_all("script", attrs={"type": "application/ld+json"})
    if not json_ld_tags:
        report.add(
            CheckResult(
                "structured_data",
                False,
                "Структурированные данные (JSON-LD) отсутствуют",
                "warning",
            )
        )
        return
    valid = 0
    invalid = 0
    for tag in json_ld_tags:
        try:
            json.loads(tag.string or "")
            valid += 1
        except (ValueError, TypeError):
            invalid += 1
    if invalid:
        report.add(
            CheckResult(
                "structured_data",
                False,
                f"Найдено {valid} валидных и {invalid} невалидных JSON-LD блоков",
                "warning",
            )
        )
    else:
        report.add(
            CheckResult(
                "structured_data",
                True,
                f"Найдено {valid} валидных JSON-LD блоков (Schema.org)",
            )
        )


def _check_twitter_card(soup: BeautifulSoup, report: SiteReport) -> None:
    """Проверяет наличие Twitter Card мета-тегов."""
    card = soup.find("meta", attrs={"name": "twitter:card"})
    title = soup.find("meta", attrs={"name": "twitter:title"})
    description = soup.find("meta", attrs={"name": "twitter:description"})
    missing = []
    if not card:
        missing.append("twitter:card")
    if not title:
        missing.append("twitter:title")
    if not description:
        missing.append("twitter:description")
    if missing:
        report.add(
            CheckResult(
                "twitter_card",
                False,
                f"Отсутствуют Twitter Card теги: {', '.join(missing)}",
                "warning",
            )
        )
    else:
        report.add(
            CheckResult("twitter_card", True, "Основные Twitter Card теги присутствуют")
        )


def _check_heading_structure(soup: BeautifulSoup, report: SiteReport) -> None:
    """Проверяет корректность иерархии заголовков (h1–h6)."""
    headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    if not headings:
        report.add(
            CheckResult(
                "heading_structure",
                False,
                "На странице нет заголовков (h1–h6)",
                "warning",
            )
        )
        return
    # Check for skipped levels (e.g. h1 → h3 skips h2)
    levels = [int(h.name[1]) for h in headings]
    skips = []
    for i in range(1, len(levels)):
        if levels[i] > levels[i - 1] + 1:
            skips.append(f"h{levels[i - 1]}→h{levels[i]}")
    if skips:
        report.add(
            CheckResult(
                "heading_structure",
                False,
                f"Пропущены уровни заголовков: {', '.join(skips)}",
                "warning",
            )
        )
    else:
        report.add(
            CheckResult(
                "heading_structure",
                True,
                f"Иерархия заголовков корректна ({len(headings)} заголовков)",
            )
        )


def analyze(url: str) -> SiteReport:
    """
    Анализирует сайт по указанному URL и возвращает SiteReport.

    :param url: URL сайта для проверки (например, https://example.com)
    :return: SiteReport с результатами всех проверок
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    report = SiteReport(url=url)

    # Fetch the page
    response, load_time = _fetch(url)
    report.load_time = load_time

    if response is None:
        report.add(
            CheckResult(
                "http",
                False,
                f"Не удалось загрузить страницу: {url}",
                "error",
            )
        )
        return report

    report.status_code = response.status_code

    if response.status_code >= 400:
        report.add(
            CheckResult(
                "http",
                False,
                f"HTTP ошибка: {response.status_code}",
                "error",
            )
        )
        return report

    report.add(
        CheckResult("http", True, f"Страница доступна (HTTP {response.status_code})")
    )

    # Parse HTML
    soup = BeautifulSoup(response.text, "html.parser")

    # Run all checks
    _check_https(response.url, report)
    _check_load_time(load_time, report)
    _check_title(soup, report)
    _check_meta_description(soup, report)
    _check_h1(soup, report)
    _check_images(soup, report)
    _check_viewport(soup, report)
    _check_canonical(soup, report)
    _check_open_graph(soup, report)
    _check_robots_txt(response.url, report)
    _check_sitemap(soup, response.url, report)
    _check_lang(soup, report)
    _check_favicon(soup, response.url, report)
    _check_structured_data(soup, report)
    _check_twitter_card(soup, report)
    _check_heading_structure(soup, report)

    return report
