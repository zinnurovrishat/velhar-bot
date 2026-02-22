import random
from openai import AsyncOpenAI
from config import config
from services.context import BASE_SYSTEM_PROMPT

client = AsyncOpenAI(api_key=config.openai_api_key)

# Alias for legacy imports
SYSTEM_PROMPT = BASE_SYSTEM_PROMPT

# Full Rider-Waite deck for reference (oracle picks randomly)
MAJOR_ARCANA = [
    "Шут", "Маг", "Верховная Жрица", "Императрица", "Император",
    "Иерофант", "Влюблённые", "Колесница", "Сила", "Отшельник",
    "Колесо Фортуны", "Справедливость", "Повешенный", "Смерть",
    "Умеренность", "Дьявол", "Башня", "Звезда", "Луна", "Солнце",
    "Суд", "Мир",
]
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


# ─── Spread generators ────────────────────────────────────────────────────────

async def generate_card_of_day(question: str, system_prompt: str | None = None) -> str:
    card = draw_cards(1)[0]
    prompt = (
        f"Пользователь просит карту дня. Его запрос или ситуация: «{question}»\n\n"
        f"Выпавшая карта: {card}\n\n"
        "Дай послание на день. Длина: 100-150 слов."
    )
    return await _ask_velhar(prompt)


async def generate_three_paths(question: str, system_prompt: str | None = None) -> str:
    cards = draw_cards(3)
    prompt = (
        f"Пользователь просит расклад на три пути. Его запрос: «{question}»\n\n"
        f"Карты:\n"
        f"  1. Прошлое — {cards[0]}\n"
        f"  2. Настоящее — {cards[1]}\n"
        f"  3. Будущее — {cards[2]}\n\n"
        "Дай полный расклад. Длина: 250-350 слов."
    )
    return await _ask_velhar(prompt, system_prompt)


async def generate_mirror_of_fate(question: str, system_prompt: str | None = None) -> str:
    cards = draw_cards(5)
    positions = ["Суть ситуации", "Скрытые силы", "Препятствие", "Ресурс", "Итог"]
    cards_block = "\n".join(f"  {i+1}. {pos} — {card}"
                            for i, (pos, card) in enumerate(zip(positions, cards)))
    prompt = (
        f"Пользователь заказал расклад «Зеркало судьбы». Его запрос: «{question}»\n\n"
        f"Карты:\n{cards_block}\n\n"
        "Дай глубокий расклад. Длина: 500-700 слов."
    )
    return await _ask_velhar(prompt, system_prompt)


async def generate_year_under_stars(question: str, system_prompt: str | None = None) -> str:
    cards = draw_cards(12)
    months = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
    ]
    cards_block = "\n".join(f"  {month} — {card}"
                            for month, card in zip(months, cards))
    prompt = (
        f"Пользователь заказал расклад «Год под звёздами». Его запрос: «{question}»\n\n"
        f"12 карт по месяцам:\n{cards_block}\n\n"
        "Дай краткое, но ёмкое мистическое послание на каждый месяц (2-4 предложения на месяц). "
        "Начни с вступления 2-3 предложения, затем каждый месяц с новой строки."
    )
    return await _ask_velhar(prompt, system_prompt)


async def generate_fullmoon_ritual(question: str, system_prompt: str | None = None) -> str:
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
    return await _ask_velhar(prompt, system_prompt)


async def generate_compatibility(question: str, system_prompt: str | None = None) -> str:
    cards = draw_cards(6)
    positions = [
        "Энергия первой души", "Энергия второй души", "Что притягивает",
        "Что разделяет", "Скрытая нить", "Послание союза",
    ]
    cards_block = "\n".join(
        f"  {i+1}. {pos} — {card}"
        for i, (pos, card) in enumerate(zip(positions, cards))
    )
    prompt = (
        f"Пользователь просит расклад на совместимость двух людей. Запрос: «{question}»\n\n"
        f"Шесть карт:\n{cards_block}\n\n"
        "Дай глубокий расклад на совместимость. Длина: 400-550 слов."
    )
    return await _ask_velhar(prompt, system_prompt)


async def generate_subscription_spread(question: str, system_prompt: str | None = None) -> str:
    cards = draw_cards(4)
    positions = ["Энергия месяца", "Главный урок", "Скрытая возможность", "Итог месяца"]
    cards_block = "\n".join(f"  {i+1}. {pos} — {card}"
                            for i, (pos, card) in enumerate(zip(positions, cards)))
    prompt = (
        f"Пользователь (подписчик) просит расклад на месяц вперёд. Его запрос: «{question}»\n\n"
        f"Карты:\n{cards_block}\n\n"
        "Дай расклад на месяц. Длина: 300-450 слов."
    )
    return await _ask_velhar(prompt, system_prompt)


# ─── Core API call ────────────────────────────────────────────────────────────

async def _ask_velhar(user_prompt: str, system_prompt: str | None = None) -> str:
    response = await client.chat.completions.create(
        model="gpt-4o",
        max_tokens=2048,
        messages=[
            {"role": "system", "content": system_prompt or SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


async def generate_summary(full_response: str) -> str:
    """Generate a 1-sentence summary of a spread for memory context."""
    try:
        resp = await client.chat.completions.create(
            model="gpt-4o",
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
