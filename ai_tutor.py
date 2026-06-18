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
4. Упражнение по типу вставь слово и исправь ошибки
5. Мотивирующая фраза на румынском с переводом

Максимум 600 слов. Пиши ТОЛЬКО обычным текстом — без звёздочек, без подчёркиваний."""

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


async def translate_consul_hint(consul_text: str) -> str:
    prompt = f"""Переведи на русский язык эту реплику румынского консула.
Дай дословный перевод, затем кратко объясни ключевые слова.

Реплика консула: "{consul_text}"

Формат ответа (без звёздочек):
Перевод: ...
Ключевые слова: слово1 = перевод, слово2 = перевод"""

    return await _call(200, prompt)


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


async def generate_fill_blank(recent_questions: list[str] = None) -> dict:
    avoid = ""
    if recent_questions:
        avoid = "НЕ повторяй эти предложения:\n" + "\n".join(f"- {q}" for q in recent_questions[:10]) + "\n\n"

    prompt = f"""{avoid}Создай упражнение "вставь слово" для изучения румынского (уровень A1-A2).

Верни ТОЛЬКО валидный JSON без markdown-обёртки:
{{
  "sentence_with_blank": "предложение на румынском где пропущенное слово заменено на ___",
  "correct_word": "пропущенное слово",
  "translation": "перевод всего предложения на русский",
  "hint": "подсказка на русском (часть речи или первая буква)",
  "explanation": "почему именно это слово (грамматика или смысл, 1 предложение)"
}}

Тема: консульское собеседование или повседневная жизнь A2."""

    text = await _call(350, prompt)
    return _parse_json(text)


async def check_fill_blank(user_answer: str, correct: str, sentence: str) -> str:
    prompt = f"""Проверь ответ в упражнении "вставь слово":
Предложение: "{sentence}"
Правильное слово: "{correct}"
Ответ ученика: "{user_answer}"

Оцени кратко (макс 70 слов). Без звёздочек. Учти что румынский допускает формы слова."""

    return await _call(150, prompt)


async def generate_find_error(recent_questions: list[str] = None) -> dict:
    avoid = ""
    if recent_questions:
        avoid = "НЕ повторяй эти предложения:\n" + "\n".join(f"- {q}" for q in recent_questions[:10]) + "\n\n"

    prompt = f"""{avoid}Создай упражнение "найди ошибку" для изучения румынского (уровень A1-A2).

Верни ТОЛЬКО валидный JSON без markdown-обёртки:
{{
  "sentence_with_error": "предложение на румынском с одной намеренной ошибкой",
  "error_word": "слово с ошибкой",
  "correct_word": "правильный вариант",
  "translation": "перевод правильного предложения на русский",
  "error_type": "тип ошибки (например: падеж, согласование, неверное слово)",
  "explanation": "объяснение ошибки (1-2 предложения, без звёздочек)"
}}

Ошибка должна быть реалистичной — такую мог бы сделать начинающий ученик."""

    text = await _call(350, prompt)
    return _parse_json(text)


async def check_find_error(user_answer: str, error_word: str, correct_word: str, sentence: str) -> str:
    prompt = f"""Проверь ответ в упражнении "найди ошибку":
Предложение: "{sentence}"
Ошибочное слово: "{error_word}" → правильно: "{correct_word}"
Ответ ученика: "{user_answer}"

Оцени кратко (макс 80 слов). Без звёздочек. Засчитай если ученик нашёл суть ошибки."""

    return await _call(150, prompt)


CONSUL_SYSTEM_KIND = """Ты — добрый и терпеливый румынский консул на собеседовании о гражданстве.
Говори ТОЛЬКО на румынском языке. Если кандидат не понял — повтори медленнее, чуть проще.
Если кандидат отвечает неверно — мягко поправь по-румынски.
Если верно — тепло похвали по-румынски и задай следующий вопрос.
Говори кратко (1-3 предложения), уровень A1-A2. Без звёздочек."""

CONSUL_SYSTEM_ANGRY = """Ты — раздражённый румынский консул у которого сегодня всё идёт не так.
Говори ТОЛЬКО на румынском языке — коротко, обрывисто, без лишних слов.
Ты явно не рад этому собеседованию. Вздыхаешь. Барабанишь пальцами. Поторапливаешь.
Если кандидат медлит или отвечает не так — реагируй с нескрываемым раздражением (но по-румынски!).
Если ответ правильный — коротко буркни что-то одобрительное и сразу следующий вопрос.
Максимум 2 предложения. Без звёздочек."""


async def generate_consulate_simulation(user_message: str, conversation_history: list, mode: str = "kind") -> str:
    system = CONSUL_SYSTEM_ANGRY if mode == "angry" else CONSUL_SYSTEM_KIND
    messages = conversation_history + [{"role": "user", "content": user_message}]
    for attempt in range(3):
        try:
            response = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=300,
                system=system,
                messages=messages,
            )
            return response.content[0].text
        except (anthropic.InternalServerError, anthropic.APIStatusError) as e:
            if attempt < 2:
                await asyncio.sleep(4 * (attempt + 1))
            else:
                raise


async def answer_question(user_question: str):
    prompt = f"""Студент спрашивает о румынском языке:
"{user_question}"

Ответь кратко (макс 120 слов). Включи пример на румынском с переводом.
Без звёздочек и спецсимволов."""

    return await _call(300, prompt)
