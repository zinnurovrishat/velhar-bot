import random
from openai import AsyncOpenAI
from config import config
from services.context import BASE_SYSTEM_PROMPT

client = AsyncOpenAI(
    api_key=config.openrouter_api_key,
    base_url="https://openrouter.ai/api/v1",
)

# Alias for legacy imports
SYSTEM_PROMPT = BASE_SYSTEM_PROMPT

# Major Arcana card images (Rider-Waite / Wikimedia Commons)
CARD_IMAGES = {
    "Шут":            "https://upload.wikimedia.org/wikipedia/commons/9/90/RWS_Tarot_00_Fool.jpg",
    "Маг":            "https://upload.wikimedia.org/wikipedia/commons/d/de/RWS_Tarot_01_Magician.jpg",
    "Верховная Жрица":"https://upload.wikimedia.org/wikipedia/commons/8/88/RWS_Tarot_02_High_Priestess.jpg",
    "Императрица":    "https://upload.wikimedia.org/wikipedia/commons/d/d2/RWS_Tarot_03_Empress.jpg",
    "Император":      "https://upload.wikimedia.org/wikipedia/commons/c/c3/RWS_Tarot_04_Emperor.jpg",
    "Иерофант":       "https://upload.wikimedia.org/wikipedia/commons/8/8d/RWS_Tarot_05_Hierophant.jpg",
    "Влюблённые":     "https://upload.wikimedia.org/wikipedia/commons/3/3a/TheLovers.jpg",
    "Колесница":      "https://upload.wikimedia.org/wikipedia/commons/9/9b/RWS_Tarot_07_Chariot.jpg",
    "Сила":           "https://upload.wikimedia.org/wikipedia/commons/f/f5/RWS_Tarot_08_Strength.jpg",
    "Отшельник":      "https://upload.wikimedia.org/wikipedia/commons/4/4d/RWS_Tarot_09_Hermit.jpg",
    "Колесо Фортуны": "https://upload.wikimedia.org/wikipedia/commons/3/3c/RWS_Tarot_10_Wheel_of_Fortune.jpg",
    "Справедливость": "https://upload.wikimedia.org/wikipedia/commons/e/e0/RWS_Tarot_11_Justice.jpg",
    "Повешенный":     "https://upload.wikimedia.org/wikipedia/commons/2/2b/RWS_Tarot_12_Hanged_Man.jpg",
    "Смерть":         "https://upload.wikimedia.org/wikipedia/commons/d/d7/RWS_Tarot_13_Death.jpg",
    "Умеренность":    "https://upload.wikimedia.org/wikipedia/commons/f/f8/RWS_Tarot_14_Temperance.jpg",
    "Дьявол":         "https://upload.wikimedia.org/wikipedia/commons/5/55/RWS_Tarot_15_Devil.jpg",
    "Башня":          "https://upload.wikimedia.org/wikipedia/commons/5/53/RWS_Tarot_16_Tower.jpg",
    "Звезда":         "https://upload.wikimedia.org/wikipedia/commons/d/db/RWS_Tarot_17_Star.jpg",
    "Луна":           "https://upload.wikimedia.org/wikipedia/commons/7/7f/RWS_Tarot_18_Moon.jpg",
    "Солнце":         "https://upload.wikimedia.org/wikipedia/commons/1/17/RWS_Tarot_19_Sun.jpg",
    "Суд":            "https://upload.wikimedia.org/wikipedia/commons/d/dd/RWS_Tarot_20_Judgement.jpg",
    "Мир":            "https://upload.wikimedia.org/wikipedia/commons/f/ff/RWS_Tarot_21_World.jpg",
}

# Full Rider-Waite deck
MAJOR_ARCANA = list(CARD_IMAGES.keys())
MINOR_SUITS = {
    "Жезлов": ["Туз", "Двойка", "Тройка", "Четвёрка", "Пятёрка",
               "Шестёрка", "Семёрка", "Восьмёрка", "Девятка", "Десятка",
               "Паж", "Рыцарь", "Королева", "Король"],
    "Кубков": ["Туз", "Двойка", "Тройка", "Четвёрка", "Пятёрка",
               "Шестёрка", "Семёрка", "Восьмёрка", "Девятка", "Десятка",
               "Паж", "Рыцарь", "Королева", "Король"],
    "Мечей": ["Туз", "Двойка", "Тройка", "Четвёрка", "Пятёрка",
              "Шестёрка", "Семёрка", "Восьмёрка", "Девятка", "Десятка",
              "Паж", "Рыцарь", "Королева", "Король"],
    "Пентаклей": ["Туз", "Двойка", "Тройка", "Четвёрка", "Пятёрка",
                  "Шестёрка", "Семёрка", "Восьмёрка", "Девятка", "Десятка",
                  "Паж", "Рыцарь", "Королева", "Король"],
}


def draw_cards(n: int) -> list[str]:
    """Draw n unique cards from the full Rider-Waite deck."""
    all_cards = list(MAJOR_ARCANA)
    for suit, ranks in MINOR_SUITS.items():
        for rank in ranks:
            all_cards.append(f"{rank} {suit}")
    return random.sample(all_cards, min(n, len(all_cards)))


# ─── Spread generators — return (drawn_cards, text) ───────────────────────────

async def generate_card_of_day(question: str, system_prompt: str | None = None) -> tuple[list[str], str]:
    card = draw_cards(1)[0]
    prompt = (
        f"Пользователь просит карту дня. Его запрос или ситуация: «{question}»\n\n"
        f"Выпавшая карта: {card}\n\n"
        "Дай послание на день. Длина: 100-150 слов."
    )
    return [card], await _ask_velhar(prompt, system_prompt)


async def generate_three_paths(question: str, system_prompt: str | None = None) -> tuple[list[str], str]:
    cards = draw_cards(3)
    prompt = (
        f"Пользователь просит расклад на три пути. Его запрос: «{question}»\n\n"
        f"Карты:\n"
        f"  1. Прошлое — {cards[0]}\n"
        f"  2. Настоящее — {cards[1]}\n"
        f"  3. Будущее — {cards[2]}\n\n"
        "Дай полный расклад. Длина: 250-350 слов."
    )
    return cards, await _ask_velhar(prompt, system_prompt)


async def generate_mirror_of_fate(question: str, system_prompt: str | None = None) -> tuple[list[str], str]:
    cards = draw_cards(5)
    positions = ["Текущая энергия", "Скрытые влияния", "Возможные вызовы", "Ресурсы", "Потенциальное направление"]
    cards_block = "\n".join(f"  {i+1}. {pos} — {card}"
                            for i, (pos, card) in enumerate(zip(positions, cards)))
    prompt = (
        f"Пользователь заказал расклад «Зеркало судьбы». Его запрос: «{question}»\n\n"
        f"Карты:\n{cards_block}\n\n"
        "Дай глубокий расклад. Длина: 500-700 слов."
    )
    return cards, await _ask_velhar(prompt, system_prompt)


async def generate_year_under_stars(question: str, system_prompt: str | None = None) -> tuple[list[str], str]:
    cards = draw_cards(12)
    months = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
    ]
    cards_block = "\n".join(f"  {month} — {card}" for month, card in zip(months, cards))
    prompt = (
        f"Пользователь заказал расклад «Год под звёздами». Его запрос: «{question}»\n\n"
        f"12 карт по месяцам:\n{cards_block}\n\n"
        "Дай краткое, но ёмкое мистическое послание на каждый месяц (2-4 предложения на месяц). "
        "Начни с вступления 2-3 предложения, затем каждый месяц с новой строки."
    )
    return cards, await _ask_velhar(prompt, system_prompt)


async def generate_fullmoon_ritual(question: str, system_prompt: str | None = None) -> tuple[list[str], str]:
    cards = draw_cards(7)
    positions = [
        "Что отпустить", "Что принять", "Тайный союзник",
        "Испытание", "Дар луны", "Послание предков", "Путь к свету",
    ]
    cards_block = "\n".join(f"  {i+1}. {pos} — {card}"
                            for i, (pos, card) in enumerate(zip(positions, cards)))
    prompt = (
        f"Пользователь совершает «Ритуал полнолуния». Его запрос: «{question}»\n\n"
        f"Семь карт:\n{cards_block}\n\n"
        "Дай торжественный ритуальный расклад. Длина: 600-800 слов. "
        "Помни — это особое, редкое послание луны."
    )
    return cards, await _ask_velhar(prompt, system_prompt)


async def generate_compatibility(question: str, system_prompt: str | None = None) -> tuple[list[str], str]:
    cards = draw_cards(6)
    positions = [
        "Энергия первой души", "Энергия второй души", "Что притягивает",
        "Что разделяет", "Скрытая нить", "Послание союза",
    ]
    cards_block = "\n".join(f"  {i+1}. {pos} — {card}"
                            for i, (pos, card) in enumerate(zip(positions, cards)))
    prompt = (
        f"Пользователь просит расклад на совместимость двух людей. Запрос: «{question}»\n\n"
        f"Шесть карт:\n{cards_block}\n\n"
        "Дай глубокий расклад на совместимость. Длина: 400-550 слов."
    )
    return cards, await _ask_velhar(prompt, system_prompt)


async def generate_subscription_spread(question: str, system_prompt: str | None = None) -> tuple[list[str], str]:
    cards = draw_cards(4)
    positions = ["Энергия месяца", "Главный урок", "Скрытая возможность", "Итог месяца"]
    cards_block = "\n".join(f"  {i+1}. {pos} — {card}"
                            for i, (pos, card) in enumerate(zip(positions, cards)))
    prompt = (
        f"Пользователь (подписчик) просит расклад на месяц вперёд. Его запрос: «{question}»\n\n"
        f"Карты:\n{cards_block}\n\n"
        "Дай расклад на месяц. Длина: 300-450 слов."
    )
    return cards, await _ask_velhar(prompt, system_prompt)


JOURNEY_THEMES = [
    ("Твоя текущая энергия",     "Раскрой, какая энергия реально присутствует в жизни этого человека прямо сейчас."),
    ("Скрытые влияния",          "Раскрой, какие силы или паттерны действуют под поверхностью."),
    ("Предстоящее испытание",    "Назови и освети то, с чем нужно встретиться или через что пройти."),
    ("Внутренняя сила",          "Раскрой ресурсы, дары и стойкость, которые несёт этот человек."),
    ("Точка перелома",           "Покажи, где возможна трансформация — где путь может измениться."),
    ("Что нужно отпустить",      "Освети то, что больше не служит — что пришло время отпустить."),
    ("Путь вперёд",              "Укажи на направление, которое зовёт эту душу."),
]


async def generate_journey_day(day: int, system_prompt: str | None = None) -> tuple[list[str], str]:
    """Генерирует расклад на один день пути (1–7)."""
    idx = max(0, min(day - 1, 6))
    theme, instruction = JOURNEY_THEMES[idx]
    card = draw_cards(1)[0]
    prompt = (
        f"Это День {day} из 7 личного внутреннего путешествия.\n"
        f"Тема дня: {theme}\n"
        f"Выпавшая карта: {card}\n\n"
        f"{instruction}\n"
        "Длина: 150–200 слов. Говори напрямую, как будто обращаешься именно к этому человеку."
    )
    return [card], await _ask_velhar(prompt, system_prompt)


# ─── Core API call ────────────────────────────────────────────────────────────

async def _ask_velhar(user_prompt: str, system_prompt: str | None = None) -> str:
    response = await client.chat.completions.create(
        model="openai/gpt-4o-mini",
        max_tokens=2048,
        messages=[
            {"role": "system", "content": system_prompt or SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


async def generate_share_card(spread_text: str) -> str:
    """Из расклада генерирует 3–4 поэтические строки для пересылки."""
    resp = await client.chat.completions.create(
        model="openai/gpt-4o-mini",
        max_tokens=120,
        messages=[
            {
                "role": "system",
                "content": (
                    "Ты — Велхар. Из текста расклада извлеки универсальное послание: "
                    "3–4 короткие поэтические строки, которые могут резонировать с любым человеком. "
                    "Никаких личных деталей. Никаких вступлений. "
                    "Только суть — загадочно, глубоко, атмосферно. На русском языке."
                ),
            },
            {"role": "user", "content": spread_text},
        ],
    )
    return resp.choices[0].message.content.strip()


async def generate_summary(full_response: str) -> str:
    """Generate a 1-sentence summary of a spread for memory context."""
    try:
        resp = await client.chat.completions.create(
            model="openai/gpt-4o-mini",
            max_tokens=60,
            messages=[
                {
                    "role": "system",
                    "content": "Сократи таро-расклад до одного предложения (не более 15 слов). Только суть послания, без вступлений.",
                },
                {"role": "user", "content": full_response},
            ],
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return full_response[:100] + "..."
