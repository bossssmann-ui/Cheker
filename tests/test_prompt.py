"""
Тесты для модуля prompt.py
"""

from __future__ import annotations

import pytest

from prompt import (
    CONFIG,
    SYSTEM_PROMPT,
    ConsultantConfig,
    DiscountPolicy,
    Objection,
    SellingPoint,
    build_prompt,
    get_discount_range,
    get_objection_response,
    get_selling_points,
    is_valid_discount,
)


# ---------------------------------------------------------------------------
# ConsultantConfig
# ---------------------------------------------------------------------------


class TestConsultantConfig:
    def test_default_name(self):
        assert CONFIG.name == "Алексей"

    def test_default_company(self):
        assert CONFIG.company == "СпецТехМаш"

    def test_default_location(self):
        assert CONFIG.location == "Находка, Приморский край, Россия"

    def test_default_language(self):
        assert CONFIG.language == "ru"

    def test_default_role(self):
        assert CONFIG.role == "старший менеджер по продажам и брокер"

    def test_selling_points_not_empty(self):
        assert len(CONFIG.selling_points) >= 2

    def test_selling_point_own_tlc(self):
        keys = [sp.key for sp in CONFIG.selling_points]
        assert "own_tlc" in keys

    def test_selling_point_vat_return(self):
        keys = [sp.key for sp in CONFIG.selling_points]
        assert "vat_return" in keys

    def test_objections_not_empty(self):
        assert len(CONFIG.objections) >= 2

    def test_config_is_frozen(self):
        with pytest.raises(AttributeError):
            CONFIG.name = "Другое имя"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# DiscountPolicy
# ---------------------------------------------------------------------------


class TestDiscountPolicy:
    def test_default_min(self):
        assert CONFIG.discount.min_rub == 15_000

    def test_default_max(self):
        assert CONFIG.discount.max_rub == 20_000

    def test_rules_not_empty(self):
        assert len(CONFIG.discount.rules) >= 1

    def test_rules_contain_no_upfront(self):
        combined = " ".join(CONFIG.discount.rules)
        assert "первым" in combined.lower() or "без причины" in combined.lower()

    def test_policy_is_frozen(self):
        with pytest.raises(AttributeError):
            CONFIG.discount.min_rub = 0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# SYSTEM_PROMPT
# ---------------------------------------------------------------------------


class TestSystemPrompt:
    def test_prompt_is_string(self):
        assert isinstance(SYSTEM_PROMPT, str)

    def test_prompt_not_empty(self):
        assert len(SYSTEM_PROMPT) > 0

    def test_prompt_contains_name(self):
        assert "Алексей" in SYSTEM_PROMPT

    def test_prompt_contains_company(self):
        assert "СпецТехМаш" in SYSTEM_PROMPT

    def test_prompt_contains_location(self):
        assert "Находка" in SYSTEM_PROMPT

    def test_prompt_mentions_language_rule(self):
        assert "русском" in SYSTEM_PROMPT.lower() or "русский" in SYSTEM_PROMPT.lower()

    def test_prompt_mentions_b2b_b2c(self):
        assert "B2B" in SYSTEM_PROMPT
        assert "B2C" in SYSTEM_PROMPT

    def test_prompt_mentions_pacific_star(self):
        assert "Пасифик Стар" in SYSTEM_PROMPT

    def test_prompt_mentions_vat(self):
        assert "НДС" in SYSTEM_PROMPT

    def test_prompt_mentions_auction(self):
        assert "аукцион" in SYSTEM_PROMPT.lower()

    def test_prompt_mentions_deposit(self):
        assert "депозит" in SYSTEM_PROMPT.lower()

    def test_prompt_mentions_discount_limit(self):
        assert "15 000" in SYSTEM_PROMPT or "15000" in SYSTEM_PROMPT
        assert "20 000" in SYSTEM_PROMPT or "20000" in SYSTEM_PROMPT

    def test_prompt_mentions_no_hallucination_rule(self):
        assert "НЕ выдумывай" in SYSTEM_PROMPT or "не выдумывай" in SYSTEM_PROMPT

    def test_prompt_mentions_objection_scam(self):
        assert "мошенник" in SYSTEM_PROMPT.lower()

    def test_prompt_mentions_objection_expensive(self):
        assert "дорого" in SYSTEM_PROMPT.lower()


# ---------------------------------------------------------------------------
# build_prompt
# ---------------------------------------------------------------------------


class TestBuildPrompt:
    def test_without_client_name(self):
        result = build_prompt()
        assert result == SYSTEM_PROMPT

    def test_with_client_name(self):
        result = build_prompt(client_name="Иван")
        assert result.startswith(SYSTEM_PROMPT)
        assert "Иван" in result

    def test_with_none_client_name(self):
        result = build_prompt(client_name=None)
        assert result == SYSTEM_PROMPT

    def test_with_empty_client_name(self):
        result = build_prompt(client_name="")
        assert result == SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# get_selling_points
# ---------------------------------------------------------------------------


class TestGetSellingPoints:
    def test_returns_list(self):
        result = get_selling_points()
        assert isinstance(result, list)

    def test_at_least_two_points(self):
        assert len(get_selling_points()) >= 2

    def test_contains_strings(self):
        for sp in get_selling_points():
            assert isinstance(sp, str)
            assert len(sp) > 0


# ---------------------------------------------------------------------------
# get_objection_response
# ---------------------------------------------------------------------------


class TestGetObjectionResponse:
    def test_scam_keyword(self):
        result = get_objection_response("мошенники")
        assert result is not None
        assert "вбелую" in result

    def test_expensive_keyword(self):
        result = get_objection_response("дорого")
        assert result is not None
        assert "гарантируем" in result

    def test_unknown_keyword(self):
        result = get_objection_response("абракадабра")
        assert result is None

    def test_case_insensitive(self):
        result = get_objection_response("МОШЕННИКИ")
        assert result is not None

    def test_partial_match(self):
        result = get_objection_response("вы мошенники!")
        assert result is not None


# ---------------------------------------------------------------------------
# get_discount_range / is_valid_discount
# ---------------------------------------------------------------------------


class TestDiscountUtils:
    def test_get_discount_range(self):
        min_d, max_d = get_discount_range()
        assert min_d == 15_000
        assert max_d == 20_000

    def test_valid_discount_min(self):
        assert is_valid_discount(15_000) is True

    def test_valid_discount_max(self):
        assert is_valid_discount(20_000) is True

    def test_valid_discount_mid(self):
        assert is_valid_discount(17_500) is True

    def test_invalid_discount_below(self):
        assert is_valid_discount(14_999) is False

    def test_invalid_discount_above(self):
        assert is_valid_discount(20_001) is False

    def test_invalid_discount_zero(self):
        assert is_valid_discount(0) is False

    def test_invalid_discount_negative(self):
        assert is_valid_discount(-1000) is False
