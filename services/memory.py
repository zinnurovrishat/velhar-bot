"""Topic detection and memory illusion logic for repeated-topic detection."""

TOPIC_KEYWORDS: dict[str, list[str]] = {
    "отношения": [
        "отношени", "любовь", "партнёр", "муж", "жена",
        "парень", "девушк", "расставани", "разрыв", "чувств",
    ],
    "работа": [
        "работ",    # работа, работе, работу, работой, работник
        "карьер",   # карьера, карьеру, карьерный
        "деньг",    # деньги, денег
        "бизнес", "начальник",
        "увол",     # уволили, уволен, увольнение
        "проект", "профессия",
        "зарплат",  # зарплата, зарплаты
    ],
    "выбор": [
        "выбор", "решени", "не знаю", "куда", "как поступить",
        "дилемма", "сомнени", "колеблюсь",
    ],
    "здоровье": [
        "здоровь", "болезн", "состояни", "самочувстви", "лечени",
    ],
    "семья": [
        "семья", "родител", "дети", "мама", "папа", "ребёнок",
        "сын", "дочь", "брат", "сестра",
    ],
}


def detect_topic(text: str | None) -> str | None:
    if not text:
        return None
    t = text.lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in t for kw in keywords):
            return topic
    return None


def has_recurring_topic(current_question: str, recent_spreads: list[dict]) -> bool:
    """True if the same topic appears in current question AND ≥2 recent spreads."""
    if len(recent_spreads) < 2:
        return False
    current_topic = detect_topic(current_question)
    if not current_topic:
        return False
    matching = sum(
        1 for s in recent_spreads
        if detect_topic(s.get("question") or "") == current_topic
    )
    return matching >= 2


def should_use_memory(user: dict, current_question: str, recent_spreads: list[dict]) -> bool:
    return (
        (user.get("total_spreads") or 0) >= 3
        and (user.get("spreads_since_memory") or 0) >= 3
        and has_recurring_topic(current_question, recent_spreads)
    )


MEMORY_ADDON = """

ДОПОЛНИТЕЛЬНОЕ ПРАВИЛО ДЛЯ ЭТОГО РАСКЛАДА:

Текущий вопрос пользователя перекликается с темой,
к которой он уже обращался раньше.

Ты МОЖЕШЬ аккуратно упомянуть это ощущение — один раз,
во вступлении или финальном послании.

Делай это:
- не напрямую, без фактов и дат
- только как ощущение возвращения
- не более одного раза за расклад

Примеры форм:
— «Ты возвращаешься к теме, которая уже касалась тебя…»
— «Этот узел уже проявлялся раньше…»
— «Карты чувствуют незавершённость…»

Если ощущение слабое — лучше промолчать.
Никогда не используй в: списке карт, summary, кнопках."""
