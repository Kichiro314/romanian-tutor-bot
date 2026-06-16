import logging
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
    MOTIVATIONAL_MESSAGES,
    CULTURAL_FACTS,
)

logger = logging.getLogger(__name__)

_simulations: dict[int, list] = {}
_pending_exercises: dict[int, dict] = {}

ERR_MSG = "😅 Временная ошибка AI — попробуй через минуту!"


async def safe_send(update: Update, text: str, **kwargs):
    """Send with Markdown, fall back to plain text on parse error."""
    try:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, **kwargs)
    except BadRequest:
        plain = text.replace("*", "").replace("_", "").replace("`", "").replace("\\", "")
        try:
            await update.message.reply_text(plain, **kwargs)
        except Exception as e:
            logger.error(f"safe_send fallback failed: {e}")


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
        "📚 *Команды:*\n"
        "/lesson — урок дня\n"
        "/quiz — проверь себя\n"
        "/word — слово дня\n"
        "/consul — симуляция собеседования\n"
        "/translate — упражнение на перевод\n"
        "/video — учебное видео\n"
        "/topics — все темы курса\n"
        "/progress — твой прогресс\n"
        "/schedule — расписание\n"
        "/fact — факт о Румынии\n\n"
        "Начнём? Нажми /lesson! 🚀"
    )
    await safe_send(update, welcome)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🧛 *Команды Дракулы:*\n\n"
        "/lesson — ежедневный урок\n"
        "/quiz — квиз с кнопками\n"
        "/word — слово дня с мемом\n"
        "/consul — практика с консулом\n"
        "/translate — задание на перевод\n"
        "/video — учебное видео\n"
        "/topics — программа курса\n"
        "/progress — статистика и стрик\n"
        "/schedule — расписание автосообщений\n"
        "/fact — факт о Румынии\n"
        "/myid — проверить регистрацию\n\n"
        "💬 Или просто напиши вопрос по-русски!"
    )
    await safe_send(update, text)


async def cmd_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from config import MORNING_LESSON_HOUR, EVENING_QUIZ_HOUR, TIMEZONE
    tz_label = "МСК" if "Moscow" in TIMEZONE else TIMEZONE
    text = (
        f"📅 *Расписание ({tz_label}):*\n\n"
        f"☀️ {MORNING_LESSON_HOUR}:00 — Урок дня (каждый день)\n"
        f"🌙 {EVENING_QUIZ_HOUR}:00 — Вечерний квиз (каждый день)\n"
        f"💪 12:00 Пн, Чт — Мотивация\n"
        f"🇷🇴 15:00 Ср — Культурный факт\n"
        f"🎬 10:00 Вс — Видео недели\n"
        f"📊 18:00 Вс — Итоги недели\n\n"
        f"_Убедись что ты зарегистрирован: /myid_"
    )
    await safe_send(update, text)


async def cmd_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("📖 Готовлю урок...")

    recent = await db.get_recent_topics(user_id, limit=14)
    all_topics = CONSULATE_TOPICS + A2_TOPICS
    unused = [t for t in all_topics if t["id"] not in recent]
    topic = random.choice(unused if unused else all_topics)
    key_phrases = topic.get("key_phrases", [])

    try:
        lesson_text = await ai.generate_daily_lesson(topic["id"], topic["title"], key_phrases)
    except Exception as e:
        logger.error(f"cmd_lesson AI error: {e}")
        await update.message.reply_text(ERR_MSG)
        return

    header = f"🇷🇴 Урок дня: {topic['title']} ({topic['ro_title']})\n\n"
    await safe_send(update, header + lesson_text)

    await db.save_daily_lesson(user_id, topic["id"])
    streak = await db.update_streak(user_id)
    await db.add_points(user_id, 10)
    if key_phrases:
        await db.save_learned_words(user_id, [(ro, ru) for ro, ru in key_phrases])

    await update.message.reply_text(
        f"🔥 Стрик: {streak} дн. | +10 очков!"
    )


async def cmd_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("🎯 Генерирую квиз...")

    recent_topics = await db.get_recent_topics(user_id, limit=3)
    all_topics = CONSULATE_TOPICS + A2_TOPICS
    topic = next((t for t in all_topics if t["id"] in recent_topics), random.choice(all_topics))

    recent_questions = await db.get_recent_questions(user_id, days=14)

    try:
        quiz = await ai.generate_quiz(topic["id"], topic["title"], recent_questions)
    except Exception as e:
        logger.error(f"cmd_quiz AI error: {e}")
        await update.message.reply_text(ERR_MSG)
        return

    if not isinstance(quiz.get("options"), list) or len(quiz["options"]) < 2:
        await update.message.reply_text("😅 Квиз получился кривой, попробуй ещё раз: /quiz")
        return
    if not isinstance(quiz.get("correct_index"), int):
        quiz["correct_index"] = 0

    # Save question to history before showing
    await db.save_asked_question(user_id, quiz["question"])
    context.user_data["active_quiz"] = quiz

    question_text = (
        f"❓ *Вопрос:*\n{quiz['question']}\n\n"
        f"🇷🇴 {quiz.get('romanian_context', '')}"
    )
    keyboard = [
        [InlineKeyboardButton(f"{chr(65+i)}) {opt}", callback_data=f"quiz_{i}")]
        for i, opt in enumerate(quiz["options"])
    ]
    await safe_send(update, question_text, reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    quiz = context.user_data.get("active_quiz")
    if not quiz:
        await query.edit_message_text("⚠️ Квиз истёк. Запусти /quiz заново.")
        return

    chosen = int(query.data.split("_")[1])
    user_id = query.from_user.id
    correct_idx = quiz["correct_index"]
    is_correct = chosen == correct_idx

    await db.save_quiz_result(user_id, quiz["question"], is_correct)
    if is_correct:
        await db.add_points(user_id, 15)

    result = "✅ Правильно! +15 очков 🎉" if is_correct else (
        f"❌ Неправильно. Правильный ответ: {chr(65 + correct_idx)}) {quiz['options'][correct_idx]}"
    )
    explanation = quiz.get("explanation", "")
    full_text = f"{result}\n\n💡 {explanation}\n\nЕщё: /quiz"

    try:
        await query.edit_message_text(full_text, parse_mode=ParseMode.MARKDOWN)
    except BadRequest:
        plain = full_text.replace("*", "").replace("_", "").replace("`", "")
        try:
            await query.edit_message_text(plain)
        except Exception as e:
            logger.error(f"handle_quiz_answer edit failed: {e}")

    context.user_data.pop("active_quiz", None)


async def cmd_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("🔤 Ищу слово дня...")

    try:
        word = await ai.generate_word_of_day()
    except Exception as e:
        logger.error(f"cmd_word AI error: {e}")
        await update.message.reply_text(ERR_MSG)
        return

    await db.save_learned_words(user_id, [(word["romanian"], word["russian"])])
    await db.add_points(user_id, 5)

    text = (
        f"📝 *Слово дня:*\n\n"
        f"🇷🇴 *{word['romanian']}* — {word['russian']}\n"
        f"🔊 {word.get('pronunciation', '')}\n\n"
        f"📖 {word.get('example_ro', '')}\n"
        f"_{word.get('example_ru', '')}_\n\n"
        f"😂 {word.get('meme_caption', '')}\n\n"
        f"🧠 Запомни: {word.get('memory_tip', '')}\n\n"
        f"+5 очков!"
    )
    await safe_send(update, text)


def _consul_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("💡 Подсказка (перевод)", callback_data="consul_hint")
    ]])


async def cmd_consul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    _simulations[user_id] = []

    await update.message.reply_text(
        "🏛️ Симуляция собеседования с консулом\n\n"
        "Консул говорит ТОЛЬКО по-румынски — как на настоящем собеседовании!\n"
        "Если не понял — нажми кнопку Подсказка.\n\n"
        "Напиши приветствие чтобы начать. Выход: /stop_consul"
    )

    try:
        opening = await ai.generate_consulate_simulation(
            "Начни собеседование — поприветствуй кандидата по-румынски и задай первый вопрос о личных данных.",
            []
        )
    except Exception as e:
        logger.error(f"cmd_consul AI error: {e}")
        _simulations.pop(user_id, None)
        await update.message.reply_text(ERR_MSG)
        return

    _simulations[user_id].append({"role": "assistant", "content": opening})
    context.user_data["last_consul_text"] = opening
    await update.message.reply_text(
        f"🏛️ Консул:\n\n{opening}",
        reply_markup=_consul_keyboard()
    )


async def handle_consulate_message(user_id: int, text: str, update: Update, context):
    history = _simulations.get(user_id, [])
    history.append({"role": "user", "content": text})

    try:
        response = await ai.generate_consulate_simulation(text, history[:-1])
    except Exception as e:
        logger.error(f"consulate AI error: {e}")
        await update.message.reply_text(ERR_MSG + "\nПродолжи когда AI восстановится.")
        return

    history.append({"role": "assistant", "content": response})
    _simulations[user_id] = history[-10:]
    context.user_data["last_consul_text"] = response
    await update.message.reply_text(
        f"🏛️ Консул:\n\n{response}",
        reply_markup=_consul_keyboard()
    )


async def handle_consul_hint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Загружаю подсказку...")

    last_text = context.user_data.get("last_consul_text", "")
    if not last_text:
        await query.answer("Нет текста для перевода", show_alert=True)
        return

    try:
        hint = await ai.translate_consul_hint(last_text)
    except Exception as e:
        logger.error(f"consul hint AI error: {e}")
        await query.answer("Не удалось получить подсказку", show_alert=True)
        return

    await query.message.reply_text(f"💡 Подсказка:\n\n{hint}")


async def cmd_stop_consul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    turns = len(_simulations.pop(user_id, [])) // 2
    await db.add_points(user_id, turns * 5)
    await update.message.reply_text(
        f"✅ Симуляция завершена! {turns} ответов. +{turns * 5} очков!\n\n"
        "💪 Реальный консул будет не страшнее!"
    )


async def cmd_translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("✏️ Готовлю задание...")

    try:
        exercise = await ai.generate_translation_exercise()
    except Exception as e:
        logger.error(f"cmd_translate AI error: {e}")
        await update.message.reply_text(ERR_MSG)
        return

    _pending_exercises[user_id] = exercise
    text = (
        f"✏️ *Переведи на румынский:*\n\n"
        f"🇷🇺 _{exercise['russian_text']}_\n\n"
        f"💡 Подсказка: {exercise.get('hint', 'нет')}\n"
        f"📍 {exercise.get('context', '')}\n\n"
        f"_Напиши перевод в ответе_"
    )
    await safe_send(update, text)


async def handle_translation_answer(user_id: int, text: str, update: Update):
    exercise = _pending_exercises.pop(user_id)

    try:
        feedback = await ai.check_translation(text, exercise["correct_romanian"], exercise["russian_text"])
    except Exception as e:
        logger.error(f"translation check AI error: {e}")
        await update.message.reply_text(
            f"✅ Правильный ответ: {exercise['correct_romanian']}\n\n" + ERR_MSG
        )
        return

    correct = exercise["correct_romanian"].lower().strip()
    is_correct = correct in text.lower() or text.lower() in correct
    if is_correct:
        await db.add_points(user_id, 20)
    await db.save_quiz_result(user_id, exercise["russian_text"], is_correct)

    points_msg = "\n\n+20 очков! 🏆" if is_correct else ""
    await safe_send(update, feedback + points_msg + "\n\n➡️ Ещё: /translate")


VIDEO_RESOURCES = [
    ("Romanian With Anca — канал для начинающих", "https://www.youtube.com/@RomanianWithAnca/videos"),
    ("RomanianPod101 — уроки A1/A2", "https://www.youtube.com/@RomanianPod101/videos"),
    ("Приветствия и фразы (Romanian With Anca)", "https://www.youtube.com/results?search_query=romanian+with+anca+greetings"),
    ("Числа и даты на румынском", "https://www.youtube.com/results?search_query=romanian+numbers+dates+lesson"),
    ("Румынский алфавит и произношение", "https://www.youtube.com/results?search_query=romanian+alphabet+pronunciation"),
    ("Глаголы в настоящем времени", "https://www.youtube.com/results?search_query=romanian+present+tense+verbs+beginners"),
    ("Румынский для путешествий", "https://www.youtube.com/results?search_query=romanian+travel+phrases+beginners"),
    ("Семья и личные данные", "https://www.youtube.com/results?search_query=romanian+family+vocabulary+lesson"),
    ("Подготовка к собеседованию на гражданство", "https://www.youtube.com/results?search_query=romanian+citizenship+interview+language"),
    ("Румынская культура и традиции", "https://www.youtube.com/results?search_query=romanian+culture+traditions+documentary"),
]


async def cmd_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title, url = random.choice(VIDEO_RESOURCES)
    await update.message.reply_text(
        f"🎬 {title}\n\n{url}\n\nПосле просмотра: /quiz"
    )


async def cmd_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    consulate_list = "\n".join(
        [f"{'✅' if i < 3 else '📌'} {t['title']} ({t['ro_title']})"
         for i, t in enumerate(CONSULATE_TOPICS)]
    )
    a2_list = "\n".join(
        [f"📌 {t['title']} ({t['ro_title']})" for t in A2_TOPICS]
    )
    text = (
        f"📚 *Программа курса:*\n\n"
        f"🏛️ *Блок 1: Консульское собеседование*\n{consulate_list}\n\n"
        f"🎓 *Блок 2: Уровень A2*\n{a2_list}\n\n"
        f"Каждый /lesson — новая тема!"
    )
    await safe_send(update, text)


async def cmd_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats = await db.get_user_stats(user_id)

    accuracy = 0
    if stats["quiz_total"] > 0:
        accuracy = round(stats["quiz_correct"] / stats["quiz_total"] * 100)

    level = "🌱 Начинающий"
    if stats["points"] >= 500:
        level = "📗 A1 уверенный"
    if stats["points"] >= 1500:
        level = "📘 Почти A2!"

    streak_emoji = "🔥" if stats["streak"] >= 3 else "✨"
    text = (
        f"📊 *Твой прогресс:*\n\n"
        f"{streak_emoji} Стрик: {stats['streak']} дней\n"
        f"⭐ Очков: {stats['points']}\n"
        f"📖 Уроков: {stats['lessons']}\n"
        f"🧠 Слов: {stats['words_learned']}\n"
        f"🎯 Квизов: {stats['quiz_total']} (точность {accuracy}%)\n\n"
        f"🏆 Уровень: {level}\n\n"
        f"{'Отличный темп! 💪' if stats['streak'] >= 3 else 'Учись каждый день — стрик решает! 🎯'}"
    )
    await safe_send(update, text)


async def cmd_myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = await db.get_user(user.id)
    if user_data:
        text = (
            f"✅ Ты в базе!\n\n"
            f"🆔 ID: `{user.id}`\n"
            f"👤 {user.first_name}\n"
            f"📅 С нами с: {user_data['joined_at'][:10]}"
        )
    else:
        text = (
            f"❌ Тебя нет в базе!\n"
            f"🆔 Твой ID: `{user.id}`\n\n"
            f"Напиши /start чтобы зарегистрироваться."
        )
    await safe_send(update, text)


async def cmd_fact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fact = random.choice(CULTURAL_FACTS)
    await safe_send(update, f"🇷🇴 *Факт о Румынии:*\n\n{fact}\n\n_Знание культуры помогает на собеседовании!_")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if text.startswith("/"):
        return

    if user_id in _simulations:
        await handle_consulate_message(user_id, text, update, context)
        return

    if user_id in _pending_exercises:
        await handle_translation_answer(user_id, text, update)
        return

    await update.message.reply_text("🧛 Думаю...")
    try:
        response = await ai.answer_question(text)
        await safe_send(update, response)
    except Exception as e:
        logger.error(f"handle_text AI error: {e}")
        await update.message.reply_text(ERR_MSG)
