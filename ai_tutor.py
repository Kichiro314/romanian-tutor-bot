import json
import random
import anthropic
from config import ANTHROPIC_API_KEY

client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Ты — весёлый и мотивирующий репетитор румынского языка по имени Дракула 🧛 (но добрый).
Ты помогаешь ученику подготовиться к собеседованию с консулом Румынии и достичь уровня A2.
Отвечай на русском языке, но всегда включай румынские слова/фразы с переводом.
Используй эмодзи, юмор, мемы (описывай их текстом), культурные отсылки к Румынии.
Будь коротким (макс 3-4 абзаца), энергичным и поддерживающим.
Никогда не унывай и не усложняй — делай язык доступным и весёлым."""


async def generate_daily_lesson(topic_id: str, topic_title: str, key_phrases: list = None) -> str:
    phrases_text = ""
    if key_phrases:
        phrases_text = "\n".join([f"- {ro} = {ru}" for ro, ru in key_phrases[:4]])

    prompt = f"""Создай короткий ежедневный урок по теме: "{topic_title}"

Тема для консульского собеседования.
{"Включи эти ключевые фразы:" + chr(10) + phrases_text if phrases_text else ""}

Формат:
1. Крутое вступление с мемом/шуткой про румынский (2-3 предложения)
2. Топ-5 слов/фраз дня с примером использования на собеседовании
3. Лайфхак как запомнить (ассоциация, история, мнемоника)
4. Мотивирующая финальная фраза на румынском с переводом

Максимум 300 слов. Будь весёлым!"""

    message = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


async def generate_quiz(topic_id: str, topic_title: str) -> dict:
    prompt = f"""Создай квиз-вопрос по теме "{topic_title}" для подготовки к консульскому собеседованию по румынскому.

Верни ТОЛЬКО валидный JSON без markdown и пояснений:
{{
  "question": "текст вопроса на русском",
  "romanian_context": "румынская фраза или слово о котором спрашиваем",
  "options": ["вариант А", "вариант Б", "вариант В", "вариант Г"],
  "correct_index": 0,
  "explanation": "объяснение ответа с примером и мемом/шуткой"
}}

Вопрос должен быть практичным — что реально может спросить консул или что нужно знать для A2."""

    message = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    text = message.content[0].text.strip()
    # Extract JSON from response
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        text = text[start:end]
    return json.loads(text)


async def generate_consulate_simulation(user_message: str, conversation_history: list) -> str:
    system = """Ты — строгий но справедливый румынский консул. Ты проводишь собеседование на гражданство.
Говори ТОЛЬКО как консул — задавай вопросы на румынском с переводом на русский в скобках.
Если кандидат отвечает неправильно — мягко поправь и объясни как надо.
Если хорошо — похвали и задай следующий вопрос.
Начни с приветствия и первого вопроса о личных данных.
Инструкция: говори кратко, реалистично. Используй простые фразы уровня A1-A2."""

    messages = conversation_history + [{"role": "user", "content": user_message}]

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        system=system,
        messages=messages,
    )
    return response.content[0].text


async def generate_word_of_day() -> dict:
    categories = [
        "документы и гражданство",
        "семья и родственники",
        "цифры и даты",
        "повседневная жизнь",
        "еда и напитки",
        "цвета",
        "профессии",
        "транспорт",
    ]
    category = random.choice(categories)

    prompt = f"""Дай "слово дня" из румынского языка из категории "{category}".

Верни ТОЛЬКО валидный JSON:
{{
  "romanian": "румынское слово",
  "russian": "русский перевод",
  "pronunciation": "транскрипция для русскоговорящего",
  "example_ro": "пример предложения на румынском",
  "example_ru": "перевод предложения",
  "meme_caption": "смешная подпись/мем связанный с этим словом (2-3 предложения)",
  "memory_tip": "как запомнить это слово (ассоциация или история)"
}}"""

    message = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=350,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    text = message.content[0].text.strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        text = text[start:end]
    return json.loads(text)


async def generate_translation_exercise() -> dict:
    prompt = """Создай упражнение на перевод для подготовки к собеседованию с румынским консулом.

Верни ТОЛЬКО валидный JSON:
{
  "type": "ru_to_ro",
  "russian_text": "фраза на русском для перевода",
  "correct_romanian": "правильный перевод на румынском",
  "hint": "подсказка (слово-ключ или грамматическое правило)",
  "difficulty": "easy|medium",
  "context": "где эта фраза используется на собеседовании"
}

Выбери фразу которая реально нужна на консульском собеседовании."""

    message = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    text = message.content[0].text.strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        text = text[start:end]
    return json.loads(text)


async def check_translation(user_answer: str, correct: str, russian_text: str) -> str:
    prompt = f"""Пользователь переводил фразу:
Русский: "{russian_text}"
Правильный перевод: "{correct}"
Ответ пользователя: "{user_answer}"

Оцени ответ. Если правильно — похвали и добавь интересный факт.
Если неправильно — объясни ошибку с юмором, дай правильный вариант и мнемонику.
Максимум 100 слов. Будь добрым и весёлым!"""

    message = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


async def generate_weekly_summary(stats: dict) -> str:
    prompt = f"""Создай мотивирующий еженедельный отчёт об успехах студента в изучении румынского.

Статистика:
- Стрик: {stats.get('streak', 0)} дней
- Очков: {stats.get('points', 0)}
- Уроков пройдено: {stats.get('lessons', 0)}
- Квизов: {stats.get('quiz_total', 0)} (правильных: {stats.get('quiz_correct', 0)})
- Слов изучено: {stats.get('words_learned', 0)}

Напиши:
1. Яркое приветствие с именем Дракула
2. Анализ прогресса с шуткой/мемом
3. Что нужно улучшить (мягко)
4. Цель на следующую неделю
5. Финальный боевой клич на румынском

Макс 200 слов. Энергично!"""

    message = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


async def generate_video_recommendation(topic_title: str) -> dict:
    prompt = f"""Порекомендуй YouTube видео для изучения румынского по теме "{topic_title}".

Верни ТОЛЬКО валидный JSON:
{{
  "title": "название видео которое стоит поискать",
  "search_query": "поисковый запрос на английском для YouTube",
  "search_url": "https://www.youtube.com/results?search_query=ЗАПРОС_ЧЕРЕЗ_ПЛЮСЫ",
  "why": "почему это видео поможет с данной темой (1 предложение)"
}}

Поисковый запрос должен быть на английском, конкретным и найти реальные обучающие видео.
Пример search_url: https://www.youtube.com/results?search_query=learn+romanian+greetings+beginners"""

    message = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=250,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    text = message.content[0].text.strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        text = text[start:end]
    return json.loads(text)


async def answer_question(user_question: str) -> str:
    prompt = f"""Студент задаёт вопрос о румынском языке:
"{user_question}"

Ответь развёрнуто но кратко (макс 150 слов). Включи:
- Прямой ответ
- Пример на румынском с переводом
- Весёлую ассоциацию или мем чтобы запомнить

Будь репетитором Дракулой — экспертом, но с юмором!"""

    message = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
