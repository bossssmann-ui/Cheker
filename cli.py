"""
Cheker CLI — запускает анализ сайта из командной строки.

Использование:
    python cli.py https://example.com
    python cli.py example.com
"""

from __future__ import annotations

import argparse
import sys

from checker import analyze, SiteReport, CheckResult, save_session, load_session


_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


def _color(text: str, code: str, *, use_color: bool = True) -> str:
    if not use_color:
        return text
    return f"{code}{text}{_RESET}"


def _icon(result: CheckResult, *, use_color: bool) -> str:
    if result.passed:
        return _color("✓", _GREEN, use_color=use_color)
    if result.level == "error":
        return _color("✗", _RED, use_color=use_color)
    return _color("!", _YELLOW, use_color=use_color)


def print_report(report: SiteReport, *, use_color: bool = True) -> None:
    bold = _BOLD if use_color else ""
    reset = _RESET if use_color else ""

    print(f"\n{bold}{'═' * 60}{reset}")
    print(f"{bold}  Cheker — отчёт по сайту{reset}")
    print(f"{bold}{'═' * 60}{reset}")
    print(f"  URL:           {report.url}")
    if report.status_code is not None:
        print(f"  HTTP-статус:   {report.status_code}")
    if report.load_time is not None:
        print(f"  Время загрузки:{report.load_time:.2f} с")
    print(f"{bold}{'─' * 60}{reset}\n")

    for check in report.checks:
        icon = _icon(check, use_color=use_color)
        print(f"  {icon}  {check.message}")

    errors = len(report.errors)
    warnings = len(report.warnings)
    passed = sum(1 for c in report.checks if c.passed)
    total = len(report.checks)

    print(f"\n{bold}{'─' * 60}{reset}")
    score_str = f"Оценка: {report.score}/100"
    if use_color:
        color = _GREEN if report.score >= 80 else _YELLOW if report.score >= 50 else _RED
        score_str = _color(score_str, color + _BOLD)
    print(f"  {score_str}")
    print(f"  Пройдено: {passed}/{total}  |  Ошибок: {errors}  |  Предупреждений: {warnings}")
    print(f"{bold}{'═' * 60}{reset}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cheker",
        description="Анализирует сайт на SEO-ошибки и технические проблемы.",
    )
    parser.add_argument("url", nargs="?", help="URL сайта для проверки (например, https://example.com)")
    parser.add_argument(
        "--no-color",
        action="store_true",
        default=False,
        help="Отключить цветной вывод",
    )
    parser.add_argument(
        "--repeat", "-r",
        action="store_true",
        default=False,
        help="Повторить последнюю сессию (использовать URL из предыдущего запуска)",
    )
    args = parser.parse_args(argv)

    if args.repeat:
        last_url = load_session()
        if last_url is None:
            print("Ошибка: нет сохранённой сессии для повтора.", file=sys.stderr)
            return 1
        url = last_url
        print(f"Повтор последней сессии: {url}")
    else:
        if not args.url:
            parser.error("укажите URL или используйте --repeat для повтора последней сессии")
        url = args.url

    use_color = not args.no_color and sys.stdout.isatty()

    print(f"Анализируем: {url} …")
    report = analyze(url)
    save_session(report.url)
    print_report(report, use_color=use_color)

    # Exit with non-zero code if there are errors
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
