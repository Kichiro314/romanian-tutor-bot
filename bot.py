import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

from config import TELEGRAM_BOT_TOKEN
import database as db
from handlers import (
    cmd_start,
    cmd_help,
    cmd_lesson,
    cmd_quiz,
    cmd_fillword,
    cmd_finderror,
    cmd_word,
    cmd_consul,
    cmd_stop_consul,
    cmd_translate,
    cmd_video,
    cmd_topics,
    cmd_progress,
    cmd_fact,
    cmd_myid,
    cmd_schedule,
    handle_quiz_answer,
    handle_consul_mode,
    handle_consul_hint,
    handle_fillword_hint,
    handle_fillword_translation,
    handle_finderror_hint,
    handle_finderror_translation,
    cmd_buildsentence,
    handle_buildsentence_hint,
    handle_buildsentence_translation,
    cmd_verb,
    cmd_verbquiz,
    cmd_myverbs,
    handle_verbquiz_hint,
    handle_text,
    handle_voice,
    cmd_test_notify,
    cmd_dialog,
    cmd_stopdialog,
    handle_dialog_scenario,
    handle_dialog_translation,
)
from scheduler import setup_scheduler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Unhandled error: {context.error}", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "😅 Что-то пошло не так. Попробуй ещё раз через минуту!"
        )


async def post_init(application: Application):
    await db.init_db()
    scheduler = setup_scheduler(application.bot)
    scheduler.start()
    logger.info("Scheduler started. Bot is ready!")
    await application.bot.set_my_commands([
        ("start", "Начать обучение"),
        ("lesson", "Урок дня"),
        ("quiz", "Квиз — выбери ответ"),
        ("fillword", "Вставь пропущенное слово"),
        ("finderror", "Найди ошибку в предложении"),
        ("buildsentence", "Составь предложение из слов"),
        ("verb", "Глагол дня с спряжением"),
        ("verbquiz", "Проверка изученных глаголов"),
        ("myverbs", "Все изученные глаголы"),
        ("word", "Слово дня"),
        ("translate", "Перевод с русского"),
        ("consul", "Собеседование с консулом"),
        ("video", "Учебное видео"),
        ("topics", "Программа курса"),
        ("progress", "Мой прогресс"),
        ("schedule", "Расписание сообщений"),
        ("fact", "Факт о Румынии"),
        ("dialog", "Голосовой диалог на румынском"),
        ("stopdialog", "Завершить диалог"),
        ("myid", "Проверить регистрацию"),
        ("help", "Помощь"),
    ])


def main():
    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("lesson", cmd_lesson))
    app.add_handler(CommandHandler("quiz", cmd_quiz))
    app.add_handler(CommandHandler("fillword", cmd_fillword))
    app.add_handler(CommandHandler("finderror", cmd_finderror))
    app.add_handler(CommandHandler("buildsentence", cmd_buildsentence))
    app.add_handler(CommandHandler("verb", cmd_verb))
    app.add_handler(CommandHandler("verbquiz", cmd_verbquiz))
    app.add_handler(CommandHandler("myverbs", cmd_myverbs))
    app.add_handler(CommandHandler("word", cmd_word))
    app.add_handler(CommandHandler("consul", cmd_consul))
    app.add_handler(CommandHandler("stop_consul", cmd_stop_consul))
    app.add_handler(CommandHandler("translate", cmd_translate))
    app.add_handler(CommandHandler("video", cmd_video))
    app.add_handler(CommandHandler("topics", cmd_topics))
    app.add_handler(CommandHandler("progress", cmd_progress))
    app.add_handler(CommandHandler("fact", cmd_fact))
    app.add_handler(CommandHandler("myid", cmd_myid))
    app.add_handler(CommandHandler("schedule", cmd_schedule))
    app.add_handler(CommandHandler("test_notify", cmd_test_notify))
    app.add_handler(CommandHandler("dialog", cmd_dialog))
    app.add_handler(CommandHandler("stopdialog", cmd_stopdialog))

    # Inline button callbacks
    app.add_handler(CallbackQueryHandler(handle_quiz_answer, pattern=r"^quiz_\d$"))
    app.add_handler(CallbackQueryHandler(handle_consul_mode, pattern=r"^consul_mode_"))
    app.add_handler(CallbackQueryHandler(handle_consul_hint, pattern=r"^consul_hint$"))
    app.add_handler(CallbackQueryHandler(handle_fillword_hint, pattern=r"^fillword_hint$"))
    app.add_handler(CallbackQueryHandler(handle_fillword_translation, pattern=r"^fillword_translation$"))
    app.add_handler(CallbackQueryHandler(handle_finderror_hint, pattern=r"^finderror_hint$"))
    app.add_handler(CallbackQueryHandler(handle_finderror_translation, pattern=r"^finderror_translation$"))
    app.add_handler(CallbackQueryHandler(handle_buildsentence_hint, pattern=r"^buildsentence_hint$"))
    app.add_handler(CallbackQueryHandler(handle_buildsentence_translation, pattern=r"^buildsentence_translation$"))
    app.add_handler(CallbackQueryHandler(handle_verbquiz_hint, pattern=r"^verbquiz_hint$"))
    app.add_handler(CallbackQueryHandler(handle_dialog_translation, pattern=r"^dialog_translation$"))
    app.add_handler(CallbackQueryHandler(handle_dialog_scenario, pattern=r"^dialog_"))

    # Free text — questions, consulate replies, translation answers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    # Voice messages — transcribed via OpenAI Whisper then routed as text
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # Global error handler
    app.add_error_handler(error_handler)

    logger.info("Starting Romanian Tutor Bot...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
