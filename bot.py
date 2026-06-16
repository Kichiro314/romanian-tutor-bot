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
    handle_text,
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
        ("quiz", "Квиз — проверь себя"),
        ("word", "Слово дня"),
        ("consul", "Симуляция собеседования"),
        ("translate", "Задание на перевод"),
        ("video", "Видео для изучения"),
        ("topics", "Программа курса"),
        ("progress", "Мой прогресс"),
        ("schedule", "Расписание сообщений"),
        ("fact", "Факт о Румынии"),
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

    # Inline button callbacks (quiz answers)
    app.add_handler(CallbackQueryHandler(handle_quiz_answer, pattern=r"^quiz_\d$"))

    # Free text — questions, consulate replies, translation answers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Global error handler
    app.add_error_handler(error_handler)

    logger.info("Starting Romanian Tutor Bot...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
