"""Keyword-based intent detection. No AI needed — fast and deterministic."""

INTENTS: dict[str, list[str]] = {
    "who_are_you": [
        "кто ты", "что ты", "ты кто", "кто велхар", "что такое велхар",
    ],
    "are_you_real": [
        "ты реальный", "ты настоящий", "ты живой", "ты существуешь",
    ],
    "are_you_ai": [
        "ты ии", "ты бот", "ты программа", "ты chatgpt", "ты гпт",
        "ты нейросеть", "ты робот", "искусственный интеллект",
        "нейронная сеть", "языковая модель", "llm", "ты gpt",
    ],
    "doubt": [
        "ты врёшь", "это неправда", "не работает", "это чушь",
        "не верю", "это фигня", "всё это ложь", "ерунда",
    ],
    "need_help": [
        "мне плохо", "помоги мне", "не знаю что делать",
        "всё плохо", "мне тяжело", "я в отчаянии", "мне грустно",
        "я устал", "я устала", "не могу больше",
    ],
    "future": [
        "что будет", "скажи будущее", "предскажи", "моё будущее",
        "что меня ждёт", "предсказание", "что произойдёт",
    ],
    "thanks": [
        "спасибо", "благодарю", "thank you", "спс", "сенкс", "благодарность",
    ],
}


def detect_intent(text: str | None) -> str | None:
    """Return intent name or None if no intent matched."""
    if not text:
        return None
    t = text.lower().strip()
    for intent, phrases in INTENTS.items():
        if any(phrase in t for phrase in phrases):
            return intent
    return None
