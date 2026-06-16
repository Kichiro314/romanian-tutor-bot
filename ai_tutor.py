import json
import random
import asyncio
import logging
import anthropic
from config import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)
client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Ты — весёлый и мотивирующий репетитор румынского языка по имени Дракула 🧛 (но добрый).
Ты помогаешь ученику подготовиться к собеседованию с консулом Румынии и достичь уровня A2.
Отвечай на русском языке, но всегда включай румынские слова/фразы с переводом.
Используй эмодзи, юмор, мемы (описывай их текстом), культурные отсылки к Румынии.
Будь коротким (макс 3-4 абзаца), энергичным и поддерживающим.
Никогда не унывай и не усложняй — делай язык доступным и весёлым."""


async def _call(max_tokens: int, prompt: str, system: str = SYSTEM_PROMPT, retries: int = 2) -> str:
    """Call Claude with automatic retry on transient 5xx errors."""
    messages = [{"role": "user", "content": prompt}]
    for attempt in range(retries + 1):
        try:
            response = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=max_tokens,
                system=system,
                messages=messages,
            )
            return response.content[0].text
        except (anthropic.InternalServerError, anthropic.APIStatusError) as e:
            if attempt < retries:
                wait = 4 * (attempt + 1)
                logger.warning(f"Anthropic {e.__class__.__name__} (attempt {attempt+1}), retry in {wait}s")
                await asyncio.sleep(wait)
            else:
                raise


def _parse_json(text: str) -> dict:
    """Extract and parse first JSON object from text."""
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(text[start:end])
    raise ValueError(f"No JSON found in response: {text[:200]}")


async def generate_daily_lesson(topic_id: str, topic_title: str, key_phrases: list = None) -> str:
    phrases_text = ""
    if key_phrases:
        phrases_text = "\n".join([f"- {ro} = {ru}" for ro, ru in key_phrases[:4]])

    prompt = f"""Создай короткий ежедневный урок по теме: "{topic_title}"

Тема для консульского собеседования.
{"Включи эти ключевые фразы:" + chr(10) + phrases_text if phrases_text else ""}

Формат:
1. Вступление с шуткой/мемом про румынский (2-3 предложения)
2. Топ-5 слов/фраз дня с примером на собеседовании
3. Лайфхак как запомнить (ассоциация, мнемоника)
4. Мотивирующая фраза на румынском с переводом

Максимум 300 слов. Пиши ТОЛЬКО обычным текстом — без звёздочек, без подчёркиваний."""

    return await _call(600, prompt)


async def generate_quiz(topic_id: str, topic_title: str, recent_questions: list[str] = None) -> dict:
    avoid_block = ""
    if recent_questions:
        questions_list = "\n".join(f"- {q}" for q in recent_questions[:15])
        avoid_block = f"\n\nНЕ повторяй эти вопросы (уже были заданы):\n{questions_list}\n"

    prompt = f"""Создай квиз-вопрос по теме "{topic_title}" для подготовки к консульскому собеседованию.
{avoid_block}
Верни ТОЛЬКО валидный JSON без markdown-обёртки:
{{
  "question": "текст вопроса на русском",
  "romanian_context": "румынская фраза о которой спрашиваем",
  "options": ["вариант А", "вариант Б", "вариант В", "вариант Г"],
  "correct_index": 0,
  "explanation": "объяснение ответа (без звёздочек и спецсимволов)"
}}

correct_index — целое число от 0 до 3."""

    text = await _call(400, prompt)
    return _parse_json(text)


async def generate_consulate_simulation(user_message: str, conversation_history: list) -> str:
    system = """Ты — строгий но справедливый румынский консул на собеседовании о гражданстве.
Задавай вопросы на румынском с переводом в скобках.
Если кандидат отвечает неверно — мягко поправь.
Если верно — похвали и задай следующий вопрос.
Говори кратко, уровень A1-A2. Пиши без звёздочек и спецсимволов."""

    messages = conversation_history + [{"role": "user", "content": user_message}]
    for attempt in range(3):
        try:
            response = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=400,
                system=system,
                messages=messages,
            )
            return response.content[0].text
        except (anthropic.InternalServerError, anthropic.APIStatusError) as e:
            if attempt < 2:
                await asyncio.sleep(4 * (attempt + 1))
            else:
                raise


async def generate_word_of_day() -> dict:
    categories = [
        "документы и гражданство", "семья и родственники",
        "цифры и даты", "повседневная жизнь",
        "еда и напитки", "профессии", "транспорт",
    ]
    category = random.choice(categories)

    prompt = f"""Дай "слово дня" из румынского языка из категории "{category}".

Верни ТОЛЬКО валидный JSON без markdown-обёртки:
{{
  "romanian": "слово",
  "russian": "перевод",
  "pronunciation": "транскрипция для русскоговорящего",
  "example_ro": "пример предложения на румынском",
  "example_ru": "перевод предложения",
  "meme_caption": "смешная подпись (без звёздочек)",
  "memory_tip": "как запомнить (ассоциация)"
}}"""

    text = await _call(350, prompt)
    return _parse_json(text)


async def generate_translation_exercise() -> dict:
    prompt = """Создай упражнение на перевод для собеседования с румынским консулом.

Верни ТОЛЬКО валидный JSON без markdown-обёртки:
{
  "russian_text": "фраза на русском",
  "correct_romanian": "правильный перевод",
  "hint": "подсказка",
  "context": "где используется на собеседовании"
}"""

    text = await _call(300, prompt)
    return _parse_json(text)


async def check_translation(user_answer: str, correct: str, russian_text: str) -> str:
    prompt = f"""Пользователь переводил фразу:
Русский: "{russian_text}"
Правильный перевод: "{correct}"
Ответ пользователя: "{user_answer}"

Оцени ответ кратко (макс 80 слов). Без звёздочек и спецсимволов.
Если правильно — похвали. Если нет — объясни ошибку с юмором."""

    return await _call(200, prompt)


async def generate_weekly_summary(stats: dict) -> str:
    prompt = f"""Еженедельный отчёт об успехах в изучении румынского.

Статистика:
- Стрик: {stats.get('streak', 0)} дней
- Очков: {stats.get('points', 0)}
- Уроков: {stats.get('lessons', 0)}
- Квизов: {stats.get('quiz_total', 0)} (правильных: {stats.get('quiz_correct', 0)})
- Слов: {stats.get('words_learned', 0)}

Напиши: приветствие от Дракулы, анализ прогресса, цель на неделю, клич на румынском.
Макс 150 слов. Без звёздочек и спецсимволов."""

    return await _call(400, prompt)


async def answer_question(user_question: str) -> str:
    prompt = f"""Студент спрашивает о румынском языке:
"{user_question}"

Ответь кратко (макс 120 слов). Включи пример на румынском с переводом.
Без звёздочек и спецсимволов."""

    return await _call(300, prompt)
