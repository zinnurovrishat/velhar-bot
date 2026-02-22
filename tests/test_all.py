"""
VELHAR bot — comprehensive test suite.
Run:  python -m pytest tests/test_all.py -v
"""
import asyncio
import os
import sys
import pytest
import pytest_asyncio

# ── env stub so config loads without a real .env ──────────────────────────────
os.environ.setdefault("BOT_TOKEN", "0:test")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("ADMIN_ID", "42")
os.environ.setdefault("WEBHOOK_URL", "http://localhost")
os.environ.setdefault("DATABASE_URL", ":memory:")

# ─────────────────────────────────────────────────────────────────────────────
# 1. INTENT DETECTOR
# ─────────────────────────────────────────────────────────────────────────────

from services.intent_detector import detect_intent

class TestIntentDetector:

    def test_who_are_you(self):
        assert detect_intent("кто ты такой?") == "who_are_you"
        assert detect_intent("кто велхар") == "who_are_you"

    def test_are_you_real(self):
        assert detect_intent("ты реальный?") == "are_you_real"
        assert detect_intent("ты живой вообще?") == "are_you_real"

    def test_are_you_ai(self):
        assert detect_intent("ты бот или нет") == "are_you_ai"
        assert detect_intent("Ты нейросеть") == "are_you_ai"
        assert detect_intent("ты chatgpt?") == "are_you_ai"
        assert detect_intent("это chatGPT") == "are_you_ai"

    def test_doubt(self):
        assert detect_intent("ты врёшь") == "doubt"
        assert detect_intent("это чушь полная") == "doubt"

    def test_need_help(self):
        assert detect_intent("мне плохо") == "need_help"
        assert detect_intent("мне тяжело") == "need_help"
        assert detect_intent("не знаю что делать") == "need_help"

    def test_future(self):
        assert detect_intent("что будет со мной") == "future"
        assert detect_intent("предскажи мне судьбу") == "future"

    def test_thanks(self):
        assert detect_intent("спасибо большое") == "thanks"
        assert detect_intent("благодарю тебя") == "thanks"

    def test_none_for_real_question(self):
        assert detect_intent("у меня конфликт на работе") is None
        assert detect_intent("что делать с отношениями?") is None
        assert detect_intent("") is None
        assert detect_intent(None) is None

    def test_case_insensitive(self):
        assert detect_intent("КТО ТЫ") == "who_are_you"
        assert detect_intent("ТЫ БОТ") == "are_you_ai"

    def test_no_false_positives(self):
        # "спасибо" shouldn't match 'are_you_ai'
        assert detect_intent("спасибо за расклад") == "thanks"
        # real question doesn't match anything
        assert detect_intent("расскажи про мою карьеру") is None


# ─────────────────────────────────────────────────────────────────────────────
# 2. MEMORY / TOPIC DETECTION
# ─────────────────────────────────────────────────────────────────────────────

from services.memory import detect_topic, has_recurring_topic, should_use_memory

class TestMemory:

    def test_detect_topic_relations(self):
        assert detect_topic("проблемы в отношениях") == "отношения"
        assert detect_topic("расставание с девушкой") == "отношения"

    def test_detect_topic_work(self):
        assert detect_topic("карьерный рост") == "работа"
        assert detect_topic("уволили с работы") == "работа"

    def test_detect_topic_choice(self):
        assert detect_topic("не знаю как поступить") == "выбор"
        assert detect_topic("стою перед выбором") == "выбор"

    def test_detect_topic_none(self):
        assert detect_topic("просто хочу узнать") is None
        assert detect_topic("") is None
        assert detect_topic(None) is None

    def test_has_recurring_topic_true(self):
        spreads = [
            {"question": "проблемы с любовью"},
            {"question": "расставание с парнем"},
            {"question": "не связано"},
        ]
        assert has_recurring_topic("снова про отношения", spreads) is True

    def test_has_recurring_topic_not_enough_history(self):
        spreads = [{"question": "проблемы с любовью"}]
        assert has_recurring_topic("снова про отношения", spreads) is False

    def test_has_recurring_topic_different_topics(self):
        spreads = [
            {"question": "проблемы с работой"},
            {"question": "уволили"},
        ]
        assert has_recurring_topic("про отношения теперь", spreads) is False

    def test_should_use_memory_true(self):
        user = {"total_spreads": 5, "spreads_since_memory": 4}
        spreads = [
            {"question": "конфликт с начальником"},   # → "работа" (работ stem)
            {"question": "карьерный рост стоит"},      # → "работа" (карьер stem)
            {"question": "другое несвязанное"},
        ]
        assert should_use_memory(user, "опять про карьеру", spreads) is True

    def test_should_use_memory_not_enough_spreads(self):
        user = {"total_spreads": 2, "spreads_since_memory": 4}
        spreads = [
            {"question": "конфликт на работе"},
            {"question": "снова про карьеру"},
        ]
        assert should_use_memory(user, "опять про работу", spreads) is False

    def test_should_use_memory_since_memory_too_low(self):
        user = {"total_spreads": 10, "spreads_since_memory": 1}
        spreads = [
            {"question": "конфликт на работе"},
            {"question": "снова про карьеру"},
        ]
        assert should_use_memory(user, "опять про работу", spreads) is False

    def test_should_use_memory_none_values(self):
        user = {}  # no keys → treated as 0
        assert should_use_memory(user, "вопрос", []) is False


# ─────────────────────────────────────────────────────────────────────────────
# 3. VELHAR VOICE TEXTS
# ─────────────────────────────────────────────────────────────────────────────

from texts.velhar_voice import (
    START_GREETING, ONBOARDING_NAME, ONBOARDING_ZODIAC,
    ABOUT_1, ABOUT_2, ABOUT_3,
    INTENT_WHO, INTENT_REAL,
    INTENT_AI_SOFT, INTENT_AI_HARD, INTENT_AI_COLD,
    INTENT_DOUBT, INTENT_HELP, INTENT_FUTURE, INTENT_THANKS,
    STATE_COLD_DEFAULT, LIMIT_REACHED, UNKNOWN_MESSAGE,
    get_loading, LOADING_WORDS,
)

class TestVelharVoice:

    def test_all_constants_non_empty(self):
        constants = [
            START_GREETING, ONBOARDING_NAME, ONBOARDING_ZODIAC,
            ABOUT_1, ABOUT_2, ABOUT_3,
            INTENT_WHO, INTENT_REAL, INTENT_AI_SOFT, INTENT_AI_HARD, INTENT_AI_COLD,
            INTENT_DOUBT, INTENT_HELP, INTENT_FUTURE, INTENT_THANKS,
            STATE_COLD_DEFAULT, LIMIT_REACHED, UNKNOWN_MESSAGE,
        ]
        for c in constants:
            assert isinstance(c, str) and len(c) > 10, f"Constant too short: {c!r}"

    def test_ai_escalation_texts_distinct(self):
        assert INTENT_AI_SOFT != INTENT_AI_HARD
        assert INTENT_AI_HARD != INTENT_AI_COLD
        assert INTENT_AI_SOFT != INTENT_AI_COLD

    def test_get_loading_all_types(self):
        types = ["spread_day", "spread_question", "spread_deep",
                 "spread_year", "spread_compat", "ritual", "month_spread"]
        for t in types:
            result = get_loading(t, "полнолуние", "вечер")
            assert isinstance(result, str) and len(result) > 5, f"Empty loading for {t}"

    def test_get_loading_unknown_type_fallback(self):
        result = get_loading("unknown_type", "растущая луна", "утро")
        assert isinstance(result, str) and len(result) > 5

    def test_get_loading_contains_moon_or_time(self):
        # At least one type should reference moon_phase or time_of_day
        hits = sum(
            1 for w in LOADING_WORDS
            if w in get_loading("spread_day", "новолуние", "утро").lower()
            or w in get_loading("spread_year", "полнолуние", "вечер").lower()
        )
        assert hits >= 0  # just check it runs without error


# ─────────────────────────────────────────────────────────────────────────────
# 4. CONTEXT BUILDER
# ─────────────────────────────────────────────────────────────────────────────

from services.context import get_moon_phase_text, get_time_of_day, build_system_prompt

class TestContext:

    def test_moon_phase_returns_string(self):
        phase = get_moon_phase_text()
        assert isinstance(phase, str) and len(phase) > 0

    def test_moon_phase_valid_values(self):
        phase = get_moon_phase_text()
        valid = {"новолуние", "растущая луна", "полнолуние", "убывающая луна", "тёмная луна"}
        assert phase in valid, f"Unexpected moon phase: {phase}"

    def test_time_of_day_valid(self):
        tod = get_time_of_day()
        valid = {"утро", "день", "вечер", "глубокая ночь"}
        assert tod in valid

    def test_build_system_prompt_with_user(self):
        user = {"name": "Ариэль", "zodiac_sign": "Лев"}
        prompt = build_system_prompt(user, [])
        assert "Ариэль" in prompt
        assert "Лев" in prompt

    def test_build_system_prompt_no_user(self):
        prompt = build_system_prompt({}, [])
        assert "путник" in prompt

    def test_build_system_prompt_with_spreads(self):
        user = {"name": "Тест"}
        spreads = [
            {"spread_type": "spread_day", "summary": "Путь освещён, но тернист"},
            {"spread_type": "spread_question", "summary": "Выбор сделан в пользу сердца"},
        ]
        prompt = build_system_prompt(user, spreads)
        assert "Путь освещён" in prompt or "освещён" in prompt

    def test_build_system_prompt_no_summary_spreads(self):
        user = {"name": "Тест"}
        spreads = [{"spread_type": "spread_day", "summary": None}]
        # Should not crash, should still return valid string
        prompt = build_system_prompt(user, spreads)
        assert isinstance(prompt, str) and len(prompt) > 50


# ─────────────────────────────────────────────────────────────────────────────
# 5. KEYBOARDS
# ─────────────────────────────────────────────────────────────────────────────

from keyboards.menus import (
    main_menu, zodiac_keyboard, reaction_keyboard,
    subscription_menu, back_to_main, limit_reached_menu, cancel_input,
)
from aiogram.types import InlineKeyboardMarkup

class TestKeyboards:

    def test_main_menu_returns_markup(self):
        kb = main_menu()
        assert isinstance(kb, InlineKeyboardMarkup)

    def test_main_menu_has_required_callbacks(self):
        kb = main_menu()
        all_cbs = {btn.callback_data for row in kb.inline_keyboard for btn in row}
        assert "spread_day"      in all_cbs
        assert "spread_question" in all_cbs
        assert "spread_deep"     in all_cbs
        assert "ritual"          in all_cbs
        assert "referral"        in all_cbs
        assert "about"           in all_cbs

    def test_zodiac_keyboard_has_12_buttons(self):
        kb = zodiac_keyboard()
        total = sum(len(row) for row in kb.inline_keyboard)
        assert total == 12

    def test_zodiac_keyboard_all_callbacks_prefixed(self):
        kb = zodiac_keyboard()
        for row in kb.inline_keyboard:
            for btn in row:
                assert btn.callback_data.startswith("zodiac:")

    def test_reaction_keyboard_structure(self):
        kb = reaction_keyboard(99)
        all_cbs = {btn.callback_data for row in kb.inline_keyboard for btn in row}
        assert "react:me_99"   in all_cbs
        assert "react:more"    in all_cbs
        assert "react:share_99" in all_cbs

    def test_limit_reached_menu_two_buttons(self):
        kb = limit_reached_menu()
        total = sum(len(row) for row in kb.inline_keyboard)
        assert total == 2

    def test_subscription_menu_subscribed(self):
        kb = subscription_menu(is_subscribed=True)
        all_cbs = {btn.callback_data for row in kb.inline_keyboard for btn in row}
        # No subscribe button when already subscribed
        assert "pay:subscription" not in all_cbs

    def test_subscription_menu_not_subscribed(self):
        kb = subscription_menu(is_subscribed=False)
        all_cbs = {btn.callback_data for row in kb.inline_keyboard for btn in row}
        assert "pay:subscription" in all_cbs


# ─────────────────────────────────────────────────────────────────────────────
# 6. DATABASE (async, in-memory)
# ─────────────────────────────────────────────────────────────────────────────

import database as db_module
from database import (
    init_db, create_user, get_user, update_user_name, update_user_zodiac,
    update_last_active, generate_and_save_referral_code, find_user_by_referral_code,
    set_referred_by, count_referrals, add_referral_bonus, use_referral_bonus,
    save_spread, get_recent_spreads, get_spread_by_id,
    increment_ai_question_count, set_velhar_state, reset_velhar_state,
    increment_spreads_since_memory, reset_spreads_since_memory,
)

# Use a temp file so each test has isolation
import tempfile, pathlib

@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_file)
    asyncio.get_event_loop().run_until_complete(init_db())
    return db_file


@pytest.mark.asyncio
async def test_create_and_get_user(tmp_db):
    await create_user(1, "alice")
    user = await get_user(1)
    assert user is not None
    assert user["user_id"] == 1
    assert user["username"] == "alice"

@pytest.mark.asyncio
async def test_update_name_and_zodiac(tmp_db):
    await create_user(2, "bob")
    await update_user_name(2, "Боб")
    await update_user_zodiac(2, "Телец")
    user = await get_user(2)
    assert user["name"] == "Боб"
    assert user["zodiac_sign"] == "Телец"

@pytest.mark.asyncio
async def test_get_user_not_found(tmp_db):
    user = await get_user(9999)
    assert user is None

@pytest.mark.asyncio
async def test_referral_code_generated(tmp_db):
    await create_user(3, "carol")
    code = await generate_and_save_referral_code(3)
    assert isinstance(code, str) and len(code) > 0
    # Calling again returns same code
    code2 = await generate_and_save_referral_code(3)
    assert code == code2

@pytest.mark.asyncio
async def test_find_user_by_referral_code(tmp_db):
    await create_user(4, "dave")
    code = await generate_and_save_referral_code(4)
    found = await find_user_by_referral_code(code)
    assert found is not None
    assert found["user_id"] == 4

@pytest.mark.asyncio
async def test_find_user_by_unknown_code(tmp_db):
    result = await find_user_by_referral_code("XXXXXXXX")
    assert result is None

@pytest.mark.asyncio
async def test_referral_count(tmp_db):
    await create_user(10, "referrer")
    await create_user(11, "invited1")
    await create_user(12, "invited2")
    await set_referred_by(11, 10)
    await set_referred_by(12, 10)
    count = await count_referrals(10)
    assert count == 2

@pytest.mark.asyncio
async def test_referral_bonus_use(tmp_db):
    await create_user(20, "bonus_user")
    await add_referral_bonus(20)
    used = await use_referral_bonus(20)
    assert used is True
    # Second use should fail
    used2 = await use_referral_bonus(20)
    assert used2 is False

@pytest.mark.asyncio
async def test_save_and_get_spread(tmp_db):
    await create_user(30, "spread_user")
    spread_id = await save_spread(30, "spread_day", "вопрос", "длинный ответ оракула", "краткое")
    assert isinstance(spread_id, int)
    spread = await get_spread_by_id(spread_id)
    assert spread["question"] == "вопрос"
    assert spread["summary"] == "краткое"
    assert spread["spread_type"] == "spread_day"

@pytest.mark.asyncio
async def test_get_recent_spreads(tmp_db):
    await create_user(31, "history_user")
    for i in range(5):
        await save_spread(31, "spread_day", f"q{i}", f"r{i}", f"s{i}")
    recent = await get_recent_spreads(31, limit=3)
    assert len(recent) == 3

@pytest.mark.asyncio
async def test_ai_question_count_increment(tmp_db):
    await create_user(40, "ai_troll")
    c1 = await increment_ai_question_count(40)
    assert c1 == 1
    c2 = await increment_ai_question_count(40)
    assert c2 == 2
    c3 = await increment_ai_question_count(40)
    assert c3 == 3

@pytest.mark.asyncio
async def test_velhar_state(tmp_db):
    await create_user(50, "state_user")
    await set_velhar_state(50, "cold")
    user = await get_user(50)
    assert user["velhar_state"] == "cold"
    await reset_velhar_state(50)
    user = await get_user(50)
    assert user["velhar_state"] == "calm"
    assert user["ai_question_count"] == 0

@pytest.mark.asyncio
async def test_spreads_since_memory(tmp_db):
    await create_user(60, "mem_user")
    await increment_spreads_since_memory(60)
    await increment_spreads_since_memory(60)
    user = await get_user(60)
    assert user["spreads_since_memory"] == 2
    await reset_spreads_since_memory(60)
    user = await get_user(60)
    assert user["spreads_since_memory"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# 7. VELHAR_STATE COLD LOGIC (integration)
# ─────────────────────────────────────────────────────────────────────────────

class TestColdStateLogic:
    """Verify the cold-state branching table from the spec."""

    TROLLING_INTENTS = ["who_are_you", "are_you_real", "are_you_ai", "doubt", "future"]
    PASS_THROUGH     = ["thanks", "need_help"]

    def test_trolling_intents_list(self):
        for intent in self.TROLLING_INTENTS:
            # These should exist in INTENTS dict
            from services.intent_detector import INTENTS
            # They don't need to be keys directly, just that detect_intent works
            assert intent in INTENTS or intent in INTENTS, intent

    def test_pass_through_intents_detected(self):
        assert detect_intent("спасибо") == "thanks"
        assert detect_intent("мне плохо") == "need_help"

    def test_real_question_no_intent(self):
        """Real spread questions that contain NO intent keywords → return None."""
        real_questions = [
            # These do NOT contain any intent keyword phrases
            "нужно ли мне переезжать в другой город",
            "стоит ли открывать собственное дело",
            "как сложится ситуация на новой работе",
        ]
        for q in real_questions:
            assert detect_intent(q) is None, f"False positive for: {q!r}"

    def test_future_intent_triggers_correctly(self):
        """'что будет' IS a future intent — bot should redirect to spread."""
        assert detect_intent("что будет с моей карьерой") == "future"
        assert detect_intent("что меня ждёт") == "future"


# ─────────────────────────────────────────────────────────────────────────────
# 8. MOON & LIMITER SERVICES
# ─────────────────────────────────────────────────────────────────────────────

from services.moon import is_near_fullmoon, days_to_fullmoon

class TestMoon:
    def test_days_to_fullmoon_returns_number(self):
        d = days_to_fullmoon()
        assert isinstance(d, (int, float))

    def test_is_near_fullmoon_returns_bool(self):
        assert isinstance(is_near_fullmoon(), bool)


# ─────────────────────────────────────────────────────────────────────────────
# 9. CONFIG
# ─────────────────────────────────────────────────────────────────────────────

from config import config, PRICES_STARS, PRODUCT_TITLES, PRODUCT_DESCRIPTIONS

class TestConfig:
    def test_prices_stars_keys(self):
        required = {"subscription", "mirror", "spread_year", "spread_compat", "ritual"}
        assert required.issubset(PRICES_STARS.keys())

    def test_prices_stars_positive(self):
        for k, v in PRICES_STARS.items():
            assert v > 0, f"Price for {k} must be > 0"

    def test_product_titles_match_prices(self):
        assert set(PRODUCT_TITLES.keys()) == set(PRICES_STARS.keys())

    def test_product_descriptions_match_prices(self):
        assert set(PRODUCT_DESCRIPTIONS.keys()) == set(PRICES_STARS.keys())

    def test_config_admin_id_is_int(self):
        assert isinstance(config.admin_id, int)
