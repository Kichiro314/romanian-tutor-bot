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
_pending_fillblanks: dict[int, dict] = {}
_pending_finderrors: dict[int, dict] = {}
_pending_buildsentences: dict[int, dict] = {}
_pending_verbquizzes: dict[int, dict] = {}
_scheduled_quizzes: dict[int, dict] = {}


def store_scheduled_quiz(user_id: int, quiz: dict):
    _scheduled_quizzes[user_id] = quiz

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
        f"🧛 Bună ziua, {user.first_name}! Добро пожаловать!\n\n"
        "Я — Дракула, твой личный репетитор румынского языка.\n"
        "Не бойся — кусаю только плохую грамматику 😄\n\n"
        "🎯 Наша цель:\n"
        "• Сдать собеседование с консулом Румынии\n"
        "• Достичь уровня B2\n\n"
        "📚 Уроки и теория:\n"
        "/lesson — урок дня с ключевыми фразами\n"
        "/word — слово дня с мемом и способом запомнить\n"
        "/topics — вся программа курса\n\n"
        "✏️ Упражнения:\n"
        "/quiz — выбери правильный ответ\n"
        "/fillword — вставь пропущенное слово\n"
        "/finderror — найди ошибку в предложении\n"
        "/buildsentence — составь предложение из слов\n"
        "/translate — переведи фразу с русского\n\n"
        "🔤 Глаголы:\n"
        "/verb — глагол дня со спряжением (база растёт!)\n"
        "/verbquiz — проверка изученных глаголов\n"
        "/myverbs — все изученные глаголы таблицей\n\n"
        "🏛️ Практика:\n"
        "/consul — собеседование с консулом (добрый или злой)\n\n"
        "📊 Прочее:\n"
        "/progress — стрик, очки, статистика\n"
        "/schedule — расписание автосообщений\n"
        "/video — учебное видео\n"
        "/fact — интересный факт о Румынии\n\n"
        "Начнём? Нажми /lesson! 🚀"
    )
    await safe_send(update, welcome)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🧛 Команды Дракулы:\n\n"
        "УРОКИ:\n"
        "/lesson — полный урок + глагол + 2 упражнения\n"
        "/word — слово дня с мемом\n"
        "/topics — программа курса\n\n"
        "УПРАЖНЕНИЯ:\n"
        "/quiz — квиз с кнопками\n"
        "/fillword — вставь пропущенное слово\n"
        "/finderror — найди ошибку в предложении\n"
        "/buildsentence — составь предложение из слов\n"
        "/translate — задание на перевод\n\n"
        "ГЛАГОЛЫ:\n"
        "/verb — глагол дня со спряжением\n"
        "/verbquiz — проверка изученных глаголов\n"
        "/myverbs — все изученные глаголы таблицей\n\n"
        "ПРАКТИКА:\n"
        "/consul — собеседование с консулом (добрый/злой)\n\n"
        "ПРОЧЕЕ:\n"
        "/progress — стрик, очки, статистика\n"
        "/schedule — расписание автосообщений\n"
        "/video — учебное видео\n"
        "/fact — факт о Румынии\n"
        "/myid — проверить регистрацию\n\n"
        "Или просто напиши вопрос по-русски (или голосом)!"
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


async def _send_fillword(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    recent = await db.get_recent_questions(user_id, days=14)
    exercise = await ai.generate_fill_blank(recent)
    _pending_fillblanks[user_id] = exercise
    await db.save_asked_question(user_id, exercise["sentence_with_blank"])
    context.user_data["fillword_hint"] = exercise.get("hint", "нет подсказки")
    context.user_data["fillword_translation"] = exercise.get("translation", "")

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("💡 Подсказка", callback_data="fillword_hint"),
        InlineKeyboardButton("🇷🇺 Перевод", callback_data="fillword_translation"),
    ]])
    await update.message.reply_text(
        f"✍️ Упражнение — вставь пропущенное слово:\n\n"
        f"🇷🇴 {exercise['sentence_with_blank']}\n\n"
        f"Напиши одно слово в ответе:",
        reply_markup=keyboard
    )


async def _send_finderror(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    recent = await db.get_recent_questions(user_id, days=14)
    exercise = await ai.generate_find_error(recent)
    _pending_finderrors[user_id] = exercise
    await db.save_asked_question(user_id, exercise["sentence_with_error"])
    context.user_data["finderror_hint"] = exercise.get("error_type", "грамматическая ошибка")
    context.user_data["finderror_translation"] = exercise.get("translation", "")

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("💡 Тип ошибки", callback_data="finderror_hint"),
        InlineKeyboardButton("🇷🇺 Перевод", callback_data="finderror_translation"),
    ]])
    await update.message.reply_text(
        f"🔍 Упражнение — найди ошибку:\n\n"
        f"🇷🇴 {exercise['sentence_with_error']}\n\n"
        f"Напиши: неправильное слово → как должно быть:",
        reply_markup=keyboard
    )


async def _send_buildsentence(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    recent = await db.get_recent_questions(user_id, days=14)
    exercise = await ai.generate_build_sentence(recent)
    _pending_buildsentences[user_id] = exercise
    await db.save_asked_question(user_id, " ".join(exercise["words"]))
    context.user_data["buildsentence_hint"] = exercise.get("hint", "нет подсказки")
    context.user_data["buildsentence_translation"] = exercise.get("translation", "")

    shuffled = exercise["words"][:]
    random.shuffle(shuffled)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("💡 Подсказка", callback_data="buildsentence_hint"),
        InlineKeyboardButton("🇷🇺 Перевод", callback_data="buildsentence_translation"),
    ]])
    await update.message.reply_text(
        f"🔤 Упражнение — составь предложение:\n\n"
        f"Слова: {' | '.join(shuffled)}\n\n"
        f"Добавь артикли и составь правильное предложение:",
        reply_markup=keyboard
    )


async def _dispatch_lesson_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Pop and send the next exercise from the lesson queue."""
    queue = context.user_data.get("lesson_exercise_queue", [])
    if not queue:
        return
    next_type = queue.pop(0)
    context.user_data["lesson_exercise_queue"] = queue
    try:
        if next_type == "fillword":
            await _send_fillword(update, context, user_id)
        elif next_type == "finderror":
            await _send_finderror(update, context, user_id)
        elif next_type == "buildsentence":
            await _send_buildsentence(update, context, user_id)
    except Exception as e:
        logger.error(f"lesson dispatch {next_type} error: {e}")


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

    # Verb of the day in the lesson
    learned_verbs = await db.get_learned_verbs(user_id)
    learned_verb_names = [v["verb_ro"] for v in learned_verbs]
    try:
        verb = await ai.generate_verb_of_day(learned_verb_names)
        await db.save_learned_verb(user_id, verb["verb_ro"], verb["meaning_ru"], verb.get("example_ro", ""))
        conj = verb.get("conjugation", {})
        conj_text = (
            f"eu {conj.get('eu','')} / tu {conj.get('tu','')} / el {conj.get('el/ea','')}\n"
            f"noi {conj.get('noi','')} / voi {conj.get('voi','')} / ei {conj.get('ei/ele','')}"
        )
        await update.message.reply_text(
            f"📚 Глагол урока: {verb['verb_ro']} — {verb['meaning_ru']}\n\n"
            f"{conj_text}\n\n"
            f"📖 {verb.get('example_ro','')} — {verb.get('example_ru','')}\n"
            f"🧠 {verb.get('memory_tip','')}\n\n"
            f"+5 очков!"
        )
        await db.add_points(user_id, 5)
    except Exception as e:
        logger.error(f"lesson verb error: {e}")

    await update.message.reply_text(
        f"🔥 Стрик: {streak} дн. | +10 очков!\n\n"
        f"Закрепим урок — два задания на выбор 👇"
    )

    # Pick 2 random exercise types for the lesson
    exercise_types = random.sample(["fillword", "finderror", "buildsentence"], 2)
    context.user_data["lesson_exercise_queue"] = [exercise_types[1]]
    try:
        if exercise_types[0] == "fillword":
            await _send_fillword(update, context, user_id)
        elif exercise_types[0] == "finderror":
            await _send_finderror(update, context, user_id)
        elif exercise_types[0] == "buildsentence":
            await _send_buildsentence(update, context, user_id)
    except Exception as e:
        logger.error(f"lesson first exercise error: {e}")
        context.user_data.pop("lesson_exercise_queue", None)


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

    user_id = query.from_user.id
    quiz = context.user_data.get("active_quiz") or _scheduled_quizzes.pop(user_id, None)
    if not quiz:
        await query.edit_message_text("⚠️ Квиз истёк. Запусти /quiz заново.")
        return

    chosen = int(query.data.split("_")[1])
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

    # Send meme image
    try:
        from meme_generator import create_word_meme
        img_bytes = create_word_meme(
            word_ro=word["romanian"],
            translation_ru=word["russian"],
            caption=word.get("meme_caption", ""),
            pronunciation=word.get("pronunciation", ""),
        )
        await update.message.reply_photo(photo=img_bytes)
    except Exception as e:
        logger.error(f"meme image error: {e}")

    text = (
        f"📝 Слово дня:\n\n"
        f"🇷🇴 {word['romanian']} — {word['russian']}\n"
        f"🔊 {word.get('pronunciation', '')}\n\n"
        f"📖 {word.get('example_ro', '')}\n"
        f"{word.get('example_ru', '')}\n\n"
        f"🧠 Запомни: {word.get('memory_tip', '')}\n\n"
        f"+5 очков!"
    )
    await update.message.reply_text(text)


def _consul_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("💡 Подсказка (перевод)", callback_data="consul_hint")
    ]])


async def cmd_consul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("😊 Добрый консул", callback_data="consul_mode_kind"),
        InlineKeyboardButton("😤 Злой консул", callback_data="consul_mode_angry"),
    ]])
    await update.message.reply_text(
        "🏛️ Симуляция собеседования с консулом\n\n"
        "Выбери режим:\n\n"
        "😊 Добрый — терпелив, поддерживает\n"
        "😤 Злой — у него сегодня всё не так, он торопит и раздражается\n\n"
        "Консул говорит только по-румынски. Кнопка Подсказка переведёт если не понял.",
        reply_markup=keyboard
    )


async def handle_consul_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    mode = "angry" if query.data == "consul_mode_angry" else "kind"
    user_id = query.from_user.id
    _simulations[user_id] = []
    context.user_data["consul_mode"] = mode

    mode_label = "😤 Злой консул" if mode == "angry" else "😊 Добрый консул"
    await query.edit_message_text(
        f"Режим: {mode_label}\n\n"
        f"Напиши приветствие чтобы начать. Выход: /stop_consul"
    )

    opening_prompt = "Начни собеседование — поприветствуй кандидата по-румынски и задай первый вопрос о личных данных."
    try:
        opening = await ai.generate_consulate_simulation(opening_prompt, [], mode=mode)
    except Exception as e:
        logger.error(f"cmd_consul AI error: {e}")
        _simulations.pop(user_id, None)
        await query.message.reply_text(ERR_MSG)
        return

    _simulations[user_id].append({"role": "assistant", "content": opening})
    context.user_data["last_consul_text"] = opening
    icon = "😤" if mode == "angry" else "🏛️"
    await query.message.reply_text(
        f"{icon} Консул:\n\n{opening}",
        reply_markup=_consul_keyboard()
    )


async def handle_consulate_message(user_id: int, text: str, update: Update, context):
    history = _simulations.get(user_id, [])
    history.append({"role": "user", "content": text})
    mode = context.user_data.get("consul_mode", "kind")

    try:
        response = await ai.generate_consulate_simulation(text, history[:-1], mode=mode)
    except Exception as e:
        logger.error(f"consulate AI error: {e}")
        await update.message.reply_text(ERR_MSG + "\nПродолжи когда AI восстановится.")
        return

    history.append({"role": "assistant", "content": response})
    _simulations[user_id] = history[-10:]
    context.user_data["last_consul_text"] = response
    icon = "😤" if mode == "angry" else "🏛️"
    await update.message.reply_text(
        f"{icon} Консул:\n\n{response}",
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


async def cmd_fillword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("✍️ Готовлю задание...")

    recent = await db.get_recent_questions(user_id, days=14)
    try:
        exercise = await ai.generate_fill_blank(recent)
    except Exception as e:
        logger.error(f"cmd_fillword AI error: {e}")
        await update.message.reply_text(ERR_MSG)
        return

    _pending_fillblanks[user_id] = exercise
    await db.save_asked_question(user_id, exercise["sentence_with_blank"])
    context.user_data["fillword_hint"] = exercise.get("hint", "нет подсказки")
    context.user_data["fillword_translation"] = exercise.get("translation", "")

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("💡 Подсказка", callback_data="fillword_hint"),
        InlineKeyboardButton("🇷🇺 Перевод", callback_data="fillword_translation"),
    ]])
    await update.message.reply_text(
        f"✍️ Вставь пропущенное слово:\n\n"
        f"🇷🇴 {exercise['sentence_with_blank']}\n\n"
        f"Напиши одно слово в ответе:",
        reply_markup=keyboard
    )


async def handle_fillword_hint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    hint = context.user_data.get("fillword_hint", "Подсказок нет")
    await query.message.reply_text(f"💡 Подсказка: {hint}")


async def handle_fillword_translation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    translation = context.user_data.get("fillword_translation", "Перевод недоступен")
    await query.message.reply_text(f"🇷🇺 Перевод: {translation}")


async def handle_fillword_answer(user_id: int, text: str, update: Update):
    exercise = _pending_fillblanks.pop(user_id)
    try:
        feedback = await ai.check_fill_blank(text, exercise["correct_word"], exercise["sentence_with_blank"])
    except Exception as e:
        logger.error(f"fillword check error: {e}")
        feedback = f"Правильный ответ: {exercise['correct_word']}"

    correct = exercise["correct_word"].lower().strip()
    is_correct = correct in text.lower() or text.lower().strip() == correct
    if is_correct:
        await db.add_points(user_id, 15)
    await db.save_quiz_result(user_id, exercise["sentence_with_blank"], is_correct)

    points = "\n\n+15 очков! 🏆" if is_correct else ""
    explanation = f"\n\n📖 {exercise.get('explanation', '')}"
    await update.message.reply_text(
        feedback + explanation + points + "\n\n➡️ Ещё задание: /fillword"
    )


async def cmd_finderror(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("🔍 Готовлю предложение с ошибкой...")

    recent = await db.get_recent_questions(user_id, days=14)
    try:
        exercise = await ai.generate_find_error(recent)
    except Exception as e:
        logger.error(f"cmd_finderror AI error: {e}")
        await update.message.reply_text(ERR_MSG)
        return

    _pending_finderrors[user_id] = exercise
    await db.save_asked_question(user_id, exercise["sentence_with_error"])
    context.user_data["finderror_hint"] = exercise.get("error_type", "грамматическая ошибка")
    context.user_data["finderror_translation"] = exercise.get("translation", "")

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("💡 Тип ошибки", callback_data="finderror_hint"),
        InlineKeyboardButton("🇷🇺 Перевод", callback_data="finderror_translation"),
    ]])
    await update.message.reply_text(
        f"🔍 Найди ошибку в предложении:\n\n"
        f"🇷🇴 {exercise['sentence_with_error']}\n\n"
        f"Напиши неправильное слово и как оно должно быть:",
        reply_markup=keyboard
    )


async def handle_finderror_hint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    hint = context.user_data.get("finderror_hint", "Подсказок нет")
    await query.message.reply_text(f"💡 Тип ошибки: {hint}")


async def handle_finderror_translation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    translation = context.user_data.get("finderror_translation", "Перевод недоступен")
    await query.message.reply_text(f"🇷🇺 Перевод (правильного предложения): {translation}")


async def handle_finderror_answer(user_id: int, text: str, update: Update):
    exercise = _pending_finderrors.pop(user_id)
    try:
        feedback = await ai.check_find_error(
            text, exercise["error_word"], exercise["correct_word"], exercise["sentence_with_error"]
        )
    except Exception as e:
        logger.error(f"finderror check error: {e}")
        feedback = f"Ошибка: {exercise['error_word']} → {exercise['correct_word']}"

    is_correct = (
        exercise["error_word"].lower() in text.lower()
        or exercise["correct_word"].lower() in text.lower()
    )
    if is_correct:
        await db.add_points(user_id, 15)
    await db.save_quiz_result(user_id, exercise["sentence_with_error"], is_correct)

    points = "\n\n+15 очков! 🏆" if is_correct else ""
    explanation = f"\n\n📖 {exercise.get('explanation', '')}"
    await update.message.reply_text(
        feedback + explanation + points + "\n\n➡️ Ещё задание: /finderror"
    )


async def cmd_buildsentence(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("🔤 Готовлю задание...")

    recent = await db.get_recent_questions(user_id, days=14)
    try:
        exercise = await ai.generate_build_sentence(recent)
    except Exception as e:
        logger.error(f"cmd_buildsentence AI error: {e}")
        await update.message.reply_text(ERR_MSG)
        return

    _pending_buildsentences[user_id] = exercise
    await db.save_asked_question(user_id, " ".join(exercise["words"]))
    context.user_data["buildsentence_hint"] = exercise.get("hint", "нет подсказки")
    context.user_data["buildsentence_translation"] = exercise.get("translation", "")

    shuffled = exercise["words"][:]
    random.shuffle(shuffled)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("💡 Подсказка", callback_data="buildsentence_hint"),
        InlineKeyboardButton("🇷🇺 Перевод", callback_data="buildsentence_translation"),
    ]])
    await update.message.reply_text(
        f"🔤 Составь предложение:\n\n"
        f"Слова: {' | '.join(shuffled)}\n\n"
        f"Добавь артикли и составь правильное предложение:",
        reply_markup=keyboard
    )


async def handle_buildsentence_hint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    hint = context.user_data.get("buildsentence_hint", "Подсказок нет")
    await query.message.reply_text(f"💡 Подсказка: {hint}")


async def handle_buildsentence_translation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    translation = context.user_data.get("buildsentence_translation", "Перевод недоступен")
    await query.message.reply_text(f"🇷🇺 Перевод: {translation}")


async def handle_buildsentence_answer(user_id: int, text: str, update: Update):
    exercise = _pending_buildsentences.pop(user_id)
    try:
        feedback = await ai.check_build_sentence(text, exercise["correct_sentence"], exercise["words"])
    except Exception as e:
        logger.error(f"buildsentence check error: {e}")
        feedback = f"Правильное предложение: {exercise['correct_sentence']}"

    correct_lower = exercise["correct_sentence"].lower()
    is_correct = (
        text.lower().strip() == correct_lower
        or all(w.lower() in text.lower() for w in exercise["words"])
    )
    if is_correct:
        await db.add_points(user_id, 15)
    await db.save_quiz_result(user_id, " ".join(exercise["words"]), is_correct)

    points = "\n\n+15 очков! 🏆" if is_correct else f"\n\n✅ Правильно: {exercise['correct_sentence']}"
    await update.message.reply_text(feedback + points + "\n\n➡️ Ещё: /buildsentence")


async def cmd_verb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("📚 Выбираю глагол...")

    learned_verbs = await db.get_learned_verbs(user_id)
    learned_names = [v["verb_ro"] for v in learned_verbs]

    try:
        verb = await ai.generate_verb_of_day(learned_names)
    except Exception as e:
        logger.error(f"cmd_verb AI error: {e}")
        await update.message.reply_text(ERR_MSG)
        return

    await db.save_learned_verb(user_id, verb["verb_ro"], verb["meaning_ru"], verb.get("example_ro", ""))
    await db.add_points(user_id, 5)

    conj = verb.get("conjugation", {})
    conj_text = (
        f"eu {conj.get('eu','')} / tu {conj.get('tu','')} / el {conj.get('el/ea','')}\n"
        f"noi {conj.get('noi','')} / voi {conj.get('voi','')} / ei {conj.get('ei/ele','')}"
    )
    verb_count = len(learned_names) + 1
    await update.message.reply_text(
        f"📚 Глагол #{verb_count}: {verb['verb_ro']} — {verb['meaning_ru']}\n\n"
        f"{conj_text}\n\n"
        f"📖 {verb.get('example_ro','')} — {verb.get('example_ru','')}\n\n"
        f"🧠 {verb.get('memory_tip','')}\n\n"
        f"+5 очков! Проверь знания: /verbquiz"
    )


async def cmd_verbquiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    learned_verbs = await db.get_learned_verbs(user_id)

    if len(learned_verbs) < 3:
        remaining = 3 - len(learned_verbs)
        await update.message.reply_text(
            f"📚 Пока изучено {len(learned_verbs)} гл. — нужно ещё {remaining}.\n"
            f"Учи новые: /verb"
        )
        return

    await update.message.reply_text("🎯 Генерирую задание по глаголам...")
    try:
        quiz = await ai.generate_verb_review(learned_verbs)
    except Exception as e:
        logger.error(f"cmd_verbquiz AI error: {e}")
        await update.message.reply_text(ERR_MSG)
        return

    _pending_verbquizzes[user_id] = quiz
    context.user_data["verbquiz_hint"] = quiz.get("hint", "нет подсказки")

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("💡 Подсказка", callback_data="verbquiz_hint")
    ]])
    romanian_ctx = quiz.get("romanian_context", "")
    ctx_line = f"\n🇷🇴 {romanian_ctx}" if romanian_ctx else ""
    await update.message.reply_text(
        f"🎯 Проверка глаголов — {quiz.get('verb','')}\n\n"
        f"❓ {quiz['question']}{ctx_line}\n\n"
        f"Напиши ответ:",
        reply_markup=keyboard
    )


async def cmd_myverbs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    verbs = await db.get_learned_verbs(user_id)

    if not verbs:
        await update.message.reply_text(
            "📚 Ты ещё не изучил ни одного глагола.\n"
            "Начни с /verb — получи первый глагол дня!"
        )
        return

    # Build table; split into chunks if list is long
    lines = [f"📚 Изучено глаголов: {len(verbs)}\n"]
    for i, v in enumerate(verbs, 1):
        date_str = v["learned_at"][:10]
        lines.append(f"{i:>3}. {v['verb_ro']:<18} — {v['meaning_ru']}  ({date_str})")

    # Telegram message limit is 4096 chars; send in pages of 50 verbs
    chunk_size = 50
    for start in range(0, len(lines), chunk_size):
        chunk = lines[start:start + chunk_size]
        # Use monospace for alignment
        text = "```\n" + "\n".join(chunk) + "\n```"
        await safe_send(update, text)


async def handle_verbquiz_hint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    hint = context.user_data.get("verbquiz_hint", "Подсказок нет")
    await query.message.reply_text(f"💡 Подсказка: {hint}")


async def handle_verbquiz_answer(user_id: int, text: str, update: Update):
    quiz = _pending_verbquizzes.pop(user_id)
    try:
        feedback = await ai.check_verb_review(text, quiz["correct_answer"], quiz["question"])
    except Exception as e:
        logger.error(f"verbquiz check error: {e}")
        feedback = f"Правильный ответ: {quiz['correct_answer']}"

    correct = quiz["correct_answer"].lower().strip()
    is_correct = correct in text.lower() or text.lower().strip() == correct
    if is_correct:
        await db.add_points(user_id, 15)
    await db.save_quiz_result(user_id, quiz["question"], is_correct)

    points = "\n\n+15 очков! 🏆" if is_correct else ""
    explanation = f"\n\n📖 {quiz.get('explanation', '')}"
    await update.message.reply_text(
        feedback + explanation + points + "\n\n➡️ Ещё: /verbquiz | Новый глагол: /verb"
    )


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
        f"🎓 *Блок 2: Уровень A2-B2*\n{a2_list}\n\n"
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
    if stats["points"] >= 300:
        level = "📗 A1"
    if stats["points"] >= 1000:
        level = "📘 A2"
    if stats["points"] >= 2500:
        level = "📙 B1 — уже серьёзно!"
    if stats["points"] >= 5000:
        level = "📕 Идёшь к B2!"

    streak_emoji = "🔥" if stats["streak"] >= 3 else "✨"
    text = (
        f"📊 *Твой прогресс:*\n\n"
        f"{streak_emoji} Стрик: {stats['streak']} дней\n"
        f"⭐ Очков: {stats['points']}\n"
        f"📖 Уроков: {stats['lessons']}\n"
        f"🧠 Слов: {stats['words_learned']}\n"
        f"🔤 Глаголов: {stats.get('verbs_learned', 0)}\n"
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


async def cmd_test_notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from scheduler import send_test_notification
    user_id = update.effective_user.id
    await update.message.reply_text("🔔 Проверяю планировщик...")
    try:
        await send_test_notification(context.bot, user_id)
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def cmd_fact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    shown = await db.get_shown_fact_indices(user_id)
    available = [i for i in range(len(CULTURAL_FACTS)) if i not in shown]

    reset_msg = ""
    if not available:
        await db.reset_shown_facts(user_id)
        available = list(range(len(CULTURAL_FACTS)))
        reset_msg = "🔄 Ты уже видел все факты — начинаем по новой!\n\n"

    idx = random.choice(available)
    await db.save_shown_fact(user_id, idx)
    remaining = len(available) - 1

    await update.message.reply_text(
        f"{reset_msg}🇷🇴 Факт о Румынии:\n\n{CULTURAL_FACTS[idx]}\n\n"
        f"Знание культуры помогает на собеседовании!\n"
        f"📊 Новых фактов осталось: {remaining}"
    )


async def _route_text(user_id: int, text: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route any text (typed or voice-transcribed) through the active exercise/simulation logic."""
    if user_id in _simulations:
        await handle_consulate_message(user_id, text, update, context)
        return

    if user_id in _pending_exercises:
        await handle_translation_answer(user_id, text, update)
        return

    if user_id in _pending_fillblanks:
        await handle_fillword_answer(user_id, text, update)
        await _dispatch_lesson_exercise(update, context, user_id)
        return

    if user_id in _pending_finderrors:
        await handle_finderror_answer(user_id, text, update)
        await _dispatch_lesson_exercise(update, context, user_id)
        return

    if user_id in _pending_buildsentences:
        await handle_buildsentence_answer(user_id, text, update)
        await _dispatch_lesson_exercise(update, context, user_id)
        return

    if user_id in _pending_verbquizzes:
        await handle_verbquiz_answer(user_id, text, update)
        return

    await update.message.reply_text("🧛 Думаю...")
    try:
        response = await ai.answer_question(text)
        await safe_send(update, response)
    except Exception as e:
        logger.error(f"handle_text AI error: {e}")
        await update.message.reply_text(ERR_MSG)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.startswith("/"):
        return
    await _route_text(update.effective_user.id, text, update, context)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from config import GROQ_API_KEY
    if not GROQ_API_KEY:
        await update.message.reply_text(
            "🎤 Голосовой ввод не настроен.\n"
            "Добавь GROQ_API_KEY в переменные Railway."
        )
        return

    await update.message.reply_text("🎤 Распознаю голос...")
    try:
        from groq import AsyncGroq
        groq = AsyncGroq(api_key=GROQ_API_KEY)

        tg_file = await context.bot.get_file(update.message.voice.file_id)
        ogg_bytes = await tg_file.download_as_bytearray()

        transcript = await groq.audio.transcriptions.create(
            model="whisper-large-v3",
            file=("voice.ogg", bytes(ogg_bytes), "audio/ogg"),
        )
        text = transcript.text.strip()
        if not text:
            await update.message.reply_text("🎤 Не удалось разобрать речь. Попробуй ещё раз.")
            return

        await update.message.reply_text(f"🎤 Распознано: {text}")
        await _route_text(update.effective_user.id, text, update, context)

    except Exception as e:
        logger.error(f"handle_voice error: {e}")
        await update.message.reply_text("😅 Ошибка распознавания. Попробуй написать текстом.")
