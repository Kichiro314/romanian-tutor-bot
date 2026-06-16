import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from telegram.error import BadRequest

import database as db
import ai_tutor as ai
from curriculum import (
    CONSULATE_TOPICS,
    A2_TOPICS,
    LEARNING_VIDEOS,
    MOTIVATIONAL_MESSAGES,
    CULTURAL_FACTS,
)

# Track active consulate simulations: user_id -> conversation history
_simulations: dict[int, list] = {}
# Track pending translation exercises: user_id -> exercise dict
_pending_exercises: dict[int, dict] = {}


async def safe_send(update: Update, text: str, **kwargs):
    """Send with Markdown, fall back to plain text if parsing fails."""
    try:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, **kwargs)
    except BadRequest:
        # Strip markdown and resend as plain text
        plain = text.replace("*", "").replace("_", "").replace("`", "").replace("\\", "")
        await update.message.reply_text(plain, **kwargs)


def _escape_md(text: str) -> str:
    """Escape special chars for MarkdownV2."""
    for ch in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.upsert_user(user.id, user.username or "", user.first_name or "")

    welcome = (
        f"🧛 *Bună ziua, {user.first_name}!* Добро пожаловать!\n\n"
        "Я — Дракула, твой личный репетитор румынского языка!\n"
        "_(Не бойся — кусаю только плохую грамматику)_ 😄\n\n"
        "🎯 *Наша цель:*\n"
        "• Сдать собеседование с консулом Румынии\n"
        "• Достичь уровня A2\n\n"
        "📚 *Что умею:*\n"
        "/lesson — урок дня\n"
        "/quiz — проверь себя!\n"
        "/word — слово дня\n"
        "/consul — симуляция собеседования\n"
        "/translate — упражнение на перевод\n"
        "/video — учебное видео\n"
        "/topics — все темы курса\n"
        "/progress — твой прогресс\n"
        "/fact — интересный факт о Румынии\n"
        "/help — помощь\n\n"
        "Начнём с урока? Нажми /lesson! 🚀"
    )
    await update.message.reply_text(welcome, parse_mode=ParseMode.MARKDOWN)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🧛 *Команды Дракулы:*\n\n"
        "/lesson — ежедневный урок (тема по расписанию)\n"
        "/quiz — квиз с кнопками по теме урока\n"
        "/word — слово дня с мемом\n"
        "/consul — практика собеседования с консулом\n"
        "/translate — задание на перевод\n"
        "/video — видео для изучения\n"
        "/topics — программа курса\n"
        "/progress — статистика и стрик\n"
        "/schedule — расписание автосообщений\n"
        "/fact — культурный факт о Румынии\n"
        "/myid — проверить регистрацию\n\n"
        "💬 Или просто напиши любой вопрос по-русски — отвечу!"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from config import MORNING_LESSON_HOUR, EVENING_QUIZ_HOUR, TIMEZONE
    tz_label = "МСК" if "Moscow" in TIMEZONE else TIMEZONE
    text = (
        f"📅 *Расписание автосообщений ({tz_label}):*\n\n"
        f"☀️ *{MORNING_LESSON_HOUR}:00* — Урок дня (каждый день)\n"
        f"🌙 *{EVENING_QUIZ_HOUR}:00* — Вечерний квиз (каждый день)\n"
        f"💪 *12:00* Пн, Чт — Мотивационное сообщение\n"
        f"🇷🇴 *15:00* Ср — Культурный факт о Румынии\n"
        f"🎬 *10:00* Вс — Видео недели\n"
        f"📊 *18:00* Вс — Итоги недели от Дракулы\n\n"
        f"_Сообщения придут автоматически если ты зарегистрирован (/myid)_"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("📖 Готовлю урок... *Момент!*", parse_mode=ParseMode.MARKDOWN)

    # Pick topic based on recent history
    recent = await db.get_recent_topics(user_id, limit=6)
    all_topics = CONSULATE_TOPICS + A2_TOPICS
    unused = [t for t in all_topics if t["id"] not in recent]
    topic = random.choice(unused if unused else all_topics)

    key_phrases = topic.get("key_phrases", [])
    lesson_text = await ai.generate_daily_lesson(topic["id"], topic["title"], key_phrases)

    header = (
        f"🇷🇴 *Урок дня: {topic['title']}*\n"
        f"_{topic['ro_title']}_\n\n"
    )

    await safe_send(update, header + lesson_text)

    # Update DB
    await db.save_daily_lesson(user_id, topic["id"])
    streak = await db.update_streak(user_id)
    await db.add_points(user_id, 10)

    # Save key phrases as learned words
    if key_phrases:
        await db.save_learned_words(user_id, [(ro, ru) for ro, ru in key_phrases])

    streak_msg = f"\n🔥 Стрик: *{streak} {'день' if streak == 1 else 'дня' if streak < 5 else 'дней'}*! +10 очков!"
    await update.message.reply_text(streak_msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("🎯 Генерирую квиз...", parse_mode=ParseMode.MARKDOWN)

    recent = await db.get_recent_topics(user_id, limit=3)
    all_topics = CONSULATE_TOPICS + A2_TOPICS
    topic = next((t for t in all_topics if t["id"] in recent), random.choice(all_topics))

    try:
        quiz = await ai.generate_quiz(topic["id"], topic["title"])
    except Exception:
        await update.message.reply_text("😅 Квиз временно недоступен. Попробуй /lesson!")
        return

    # Store quiz in context for callback
    context.user_data["active_quiz"] = quiz

    question_text = (
        f"❓ *Вопрос:*\n{quiz['question']}\n\n"
        f"🇷🇴 _{quiz.get('romanian_context', '')}_"
    )

    options = quiz["options"]
    keyboard = [
        [InlineKeyboardButton(f"{chr(65+i)}) {opt}", callback_data=f"quiz_{i}")]
        for i, opt in enumerate(options)
    ]
    await safe_send(update, question_text, reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chosen = int(query.data.split("_")[1])
    quiz = context.user_data.get("active_quiz")
    if not quiz:
        await query.edit_message_text("⚠️ Квиз истёк. Запусти /quiz заново.")
        return

    user_id = query.from_user.id
    correct_idx = quiz["correct_index"]
    is_correct = chosen == correct_idx

    await db.save_quiz_result(user_id, quiz["question"], is_correct)

    if is_correct:
        await db.add_points(user_id, 15)
        result_icon = "✅"
        result_text = "Правильно! +15 очков 🎉"
    else:
        result_icon = "❌"
        result_text = f"Неправильно. Правильный ответ: {chr(65 + correct_idx)}) {quiz['options'][correct_idx]}"

    explanation = quiz.get("explanation", "")
    full_text = (
        f"{result_icon} *{result_text}*\n\n"
        f"💡 {explanation}\n\n"
        "Продолжай! /quiz для ещё одного вопроса"
    )
    try:
        await query.edit_message_text(full_text, parse_mode=ParseMode.MARKDOWN)
    except BadRequest:
        plain = full_text.replace("*", "").replace("_", "").replace("`", "")
        await query.edit_message_text(plain)
    context.user_data.pop("active_quiz", None)


async def cmd_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("🔤 Ищу слово дня...", parse_mode=ParseMode.MARKDOWN)

    try:
        word = await ai.generate_word_of_day()
    except Exception:
        await update.message.reply_text("😅 Словарь временно не отвечает. Попробуй снова!")
        return

    await db.save_learned_words(user_id, [(word["romanian"], word["russian"])])
    await db.add_points(user_id, 5)

    text = (
        f"📝 *Слово дня:*\n\n"
        f"🇷🇴 *{word['romanian']}* — {word['russian']}\n"
        f"🔊 Произношение: _{word.get('pronunciation', '?')}_\n\n"
        f"📖 *Пример:*\n"
        f"_{word.get('example_ro', '')}_\n"
        f"_{word.get('example_ru', '')}_\n\n"
        f"😂 *Мем:* {word.get('meme_caption', '')}\n\n"
        f"🧠 *Как запомнить:* {word.get('memory_tip', '')}\n\n"
        f"+5 очков!"
    )
    await safe_send(update, text)


async def cmd_consul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    _simulations[user_id] = []

    intro = (
        "🏛️ *Симуляция собеседования с консулом*\n\n"
        "Ты входишь в кабинет консульства Румынии.\n"
        "Консул смотрит на твои документы...\n\n"
        "_Напиши своё приветствие, и консул ответит!_\n"
        "_(Для выхода напиши /stop_consul)_"
    )
    await update.message.reply_text(intro, parse_mode=ParseMode.MARKDOWN)

    # Start conversation
    opening = await ai.generate_consulate_simulation(
        "Начни собеседование как консул — поприветствуй кандидата на румынском и задай первый вопрос.",
        []
    )
    _simulations[user_id].append({"role": "assistant", "content": opening})
    await safe_send(update, f"🏛️ *Консул:*\n\n{opening}")


async def handle_consulate_message(user_id: int, text: str, update: Update):
    history = _simulations.get(user_id, [])
    history.append({"role": "user", "content": text})

    response = await ai.generate_consulate_simulation(text, history[:-1])
    history.append({"role": "assistant", "content": response})
    _simulations[user_id] = history[-10:]  # Keep last 10 messages

    await safe_send(update, f"🏛️ *Консул:*\n\n{response}")


async def cmd_stop_consul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    turns = len(_simulations.pop(user_id, [])) // 2
    await db.add_points(user_id, turns * 5)
    await update.message.reply_text(
        f"✅ Симуляция завершена! Ты дал {turns} ответов. +{turns * 5} очков!\n\n"
        "💪 Продолжай практиковаться — реальный консул будет не страшнее!",
        parse_mode=ParseMode.MARKDOWN
    )


async def cmd_translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("✏️ Готовлю задание на перевод...", parse_mode=ParseMode.MARKDOWN)

    try:
        exercise = await ai.generate_translation_exercise()
    except Exception:
        await update.message.reply_text("😅 Не могу создать задание. Попробуй позже!")
        return

    _pending_exercises[user_id] = exercise

    text = (
        f"✏️ *Переведи на румынский:*\n\n"
        f"🇷🇺 _{exercise['russian_text']}_\n\n"
        f"💡 Подсказка: {exercise.get('hint', 'нет')}\n"
        f"📍 Контекст: {exercise.get('context', '')}\n\n"
        f"_Напиши свой перевод в ответе_"
    )
    await safe_send(update, text)


async def handle_translation_answer(user_id: int, text: str, update: Update):
    exercise = _pending_exercises.pop(user_id)
    feedback = await ai.check_translation(text, exercise["correct_romanian"], exercise["russian_text"])

    correct = exercise["correct_romanian"].lower().strip()
    user_ans = text.lower().strip()
    is_correct = correct in user_ans or user_ans in correct

    if is_correct:
        await db.add_points(user_id, 20)
    await db.save_quiz_result(user_id, exercise["russian_text"], is_correct)

    points_msg = "\n\n+20 очков! 🏆" if is_correct else ""
    await safe_send(update, feedback + points_msg + "\n\n➡️ Ещё задание: /translate")


TOPIC_SEARCHES = {
    "greeting":       ("romanian greetings beginners", "Приветствие"),
    "personal_info":  ("romanian personal information lesson", "Личные данные"),
    "family_roots":   ("romanian family vocabulary", "Семья"),
    "documents":      ("romanian citizenship interview preparation", "Документы"),
    "romania_basics": ("romania history culture basics", "Румыния"),
    "numbers_dates":  ("romanian numbers dates lesson", "Числа и даты"),
    "daily_routine":  ("romanian daily routine vocabulary", "Распорядок дня"),
    "food_shopping":  ("romanian food shopping phrases", "Еда и магазины"),
    "transport":      ("romanian transport travel phrases", "Транспорт"),
    "work_hobbies":   ("romanian work hobbies vocabulary", "Работа и хобби"),
    "weather":        ("romanian weather vocabulary", "Погода"),
    "health":         ("romanian health doctor vocabulary", "Здоровье"),
    "directions":     ("romanian directions city phrases", "Ориентация"),
    "emotions":       ("romanian emotions feelings vocabulary", "Эмоции"),
}

async def cmd_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    recent = await db.get_recent_topics(user_id, limit=3)
    topic_id = recent[0] if recent else random.choice(list(TOPIC_SEARCHES.keys()))
    search_query, topic_label = TOPIC_SEARCHES.get(
        topic_id, ("learn romanian beginners A1", "Румынский A1")
    )
    url = "https://www.youtube.com/results?search_query=" + search_query.replace(" ", "+")

    text = (
        f"🎬 *Видео по теме «{topic_label}»:*\n\n"
        f"🔗 {url}\n\n"
        f"📺 *Лучшие каналы:*\n"
        f"• Romanian With Anca\n"
        f"• Learn Romanian With Vlad\n"
        f"• RomanianPod101\n\n"
        f"После просмотра проверь себя: /quiz 🎯"
    )
    await safe_send(update, text)


async def cmd_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    consulate_list = "\n".join(
        [f"{'✅' if i < 3 else '📌'} {t['title']} — _{t['ro_title']}_"
         for i, t in enumerate(CONSULATE_TOPICS)]
    )
    a2_list = "\n".join(
        [f"📌 {t['title']} — _{t['ro_title']}_" for t in A2_TOPICS]
    )
    text = (
        f"📚 *Программа курса:*\n\n"
        f"🏛️ *Блок 1: Консульское собеседование*\n{consulate_list}\n\n"
        f"🎓 *Блок 2: Уровень A2*\n{a2_list}\n\n"
        f"Каждый день /lesson даёт новую тему!"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats = await db.get_user_stats(user_id)

    accuracy = 0
    if stats["quiz_total"] > 0:
        accuracy = round(stats["quiz_correct"] / stats["quiz_total"] * 100)

    streak_emoji = "🔥" if stats["streak"] >= 3 else "✨"
    level = "🌱 Начинающий"
    if stats["points"] >= 500:
        level = "📗 A1 уверенный"
    if stats["points"] >= 1500:
        level = "📘 Почти A2!"

    text = (
        f"📊 *Твой прогресс, ученик Дракулы:*\n\n"
        f"{streak_emoji} Стрик: *{stats['streak']} дней*\n"
        f"⭐ Очков: *{stats['points']}*\n"
        f"📖 Уроков пройдено: *{stats['lessons']}*\n"
        f"🧠 Слов изучено: *{stats['words_learned']}*\n"
        f"🎯 Квизов: {stats['quiz_total']} (точность: {accuracy}%)\n\n"
        f"🏆 Уровень: {level}\n\n"
        f"{'Отличный темп! Продолжай! 💪' if stats['streak'] >= 3 else 'Занимайся каждый день чтобы поднять стрик! 🎯'}"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = await db.get_user(user.id)
    if user_data:
        text = (
            f"✅ Ты в базе!\n\n"
            f"🆔 ID: `{user.id}`\n"
            f"👤 Имя: {user.first_name}\n"
            f"📅 Зарегистрирован: {user_data['joined_at'][:10]}"
        )
    else:
        text = (
            f"❌ Тебя нет в базе!\n\n"
            f"🆔 Твой ID: `{user.id}`\n\n"
            f"Напиши /start чтобы зарегистрироваться."
        )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_fact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fact = random.choice(CULTURAL_FACTS)
    text = (
        f"🇷🇴 *Факт о Румынии:*\n\n{fact}\n\n"
        f"_Знания о стране помогут и на собеседовании!_"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if text.startswith("/"):
        return

    # Check if in consulate simulation
    if user_id in _simulations:
        await handle_consulate_message(user_id, text, update)
        return

    # Check if pending translation
    if user_id in _pending_exercises:
        await handle_translation_answer(user_id, text, update)
        return

    # General question — ask AI
    await update.message.reply_text("🧛 Думаю...")
    response = await ai.answer_question(text)
    await safe_send(update, response)
