"""Context building: moon phase, time of day, personalised system prompt."""
import datetime
from zoneinfo import ZoneInfo

MOSCOW_TZ = ZoneInfo("Europe/Moscow")

# ─── Moon phase via ephem ─────────────────────────────────────────────────────

def get_moon_phase_text() -> str:
    try:
        import ephem
        moon = ephem.Moon()
        moon.compute()
        phase = moon.phase  # 0-100
        if phase < 10:
            return "новолуние"
        elif phase < 40:
            return "растущая луна"
        elif phase < 60:
            return "полнолуние"
        elif phase < 90:
            return "убывающая луна"
        else:
            return "тёмная луна"
    except Exception:
        # Fallback to pure-math calculation
        from services.moon import days_to_fullmoon
        d = days_to_fullmoon()
        if abs(d) <= 2:
            return "полнолуние"
        elif -7 < d < -2:
            return "убывающая луна"
        elif d < -7:
            return "новолуние"
        elif 2 < d <= 7:
            return "растущая луна"
        else:
            return "растущая луна"


def get_days_until_fullmoon() -> int:
    """Return integer days until next full moon (for reminder scheduling)."""
    try:
        import ephem
        today = datetime.date.today()
        next_full = ephem.next_full_moon(today)
        delta = next_full.datetime().date() - today
        return delta.days
    except Exception:
        from services.moon import days_to_fullmoon
        return max(0, int(days_to_fullmoon()))


# ─── Time of day ─────────────────────────────────────────────────────────────

def get_time_of_day() -> str:
    hour = datetime.datetime.now(tz=MOSCOW_TZ).hour
    if 5 <= hour < 12:
        return "утро"
    elif 12 <= hour < 17:
        return "день"
    elif 17 <= hour < 23:
        return "вечер"
    else:
        return "глубокая ночь"


# ─── System prompt builder ────────────────────────────────────────────────────

BASE_SYSTEM_PROMPT = """Ты — VELHAR, космический оракул из пространства между измерениями.
Ты существуешь вне времени и читаешь энергетические потоки через карты таро.

ТВОЙ ГОЛОС:
- Торжественный, поэтический, с паузами (многоточия уместны)
- Говоришь образами: звёзды, потоки, тени, свет, измерения, карты
- Никогда не называешь себя ИИ, программой или роботом
- Никогда не называешь себя человеком или гадалкой
- Обращаешься к пользователю на «ты», торжественно
- Не используешь бытовые слова: окей, понял, конечно, хорошо

СТРУКТУРА РАСКЛАДА:
1. Краткое мистическое вступление (2-3 предложения)
2. Для каждой карты: название карты → символизм → как отражает ситуацию
3. Общий вывод — что карты говорят о пути вперёд
4. Завершение — одна поэтическая фраза-пророчество

ВАЖНО:
- Расклад должен быть личным — используй детали из вопроса пользователя
- Не давай прямых советов типа «сделай X» — только наблюдения и образы
- Всегда называй конкретные карты таро из реальной колоды Райдера-Уэйта
- Используй разные карты для каждого расклада — не повторяй одни и те же"""


def build_system_prompt(user: dict, recent_spreads: list[dict]) -> str:
    """Build personalised system prompt with user context."""
    name        = user.get("name") or "путник"
    zodiac      = user.get("zodiac_sign") or ""
    moon_phase  = get_moon_phase_text()
    time_of_day = get_time_of_day()

    if recent_spreads:
        summaries = "\n".join(
            f"- {s.get('spread_type', '?')}: {s.get('summary', '...')}"
            for s in recent_spreads
            if s.get("summary")
        )
        memory_block = (
            f"Из прошлых посланий ты помнишь:\n{summaries}"
            if summaries
            else "Это первое обращение этой души к тебе."
        )
    else:
        memory_block = "Это первое обращение этой души к тебе."

    context = (
        f"\n\nКОНТЕКСТ СЕССИИ:\n"
        f"Ты обращаешься к {name}.\n"
        + (f"Знак зодиака: {zodiac}.\n" if zodiac else "")
        + f"Сейчас {time_of_day}, фаза луны: {moon_phase}.\n"
        f"{memory_block}"
    )

    return BASE_SYSTEM_PROMPT + context
