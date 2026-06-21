import random
import logging
from datetime import datetime
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

import database as db
import ai_tutor as ai
from curriculum import (
    CONSULATE_TOPICS,
    A2_TOPICS,
    MOTIVATIONAL_MESSAGES,
    CULTURAL_FACTS,
)
from config import TIMEZONE, MORNING_LESSON_HOUR, EVENING_QUIZ_HOUR
from handlers import store_scheduled_quiz

logger = logging.getLogger(__name__)


async def _safe_send(bot: Bot, user_id: int, text: str):
    try:
        await bot.send_message(user_id, text)
        return True
    except TelegramError as e:
        logger.warning(f"Cannot send to {user_id}: {e}")
        return False


async def send_morning_lesson(bot: Bot):
    user_ids = await db.get_all_user_ids()
    logger.info(f"[SCHEDULER] Morning lesson — users: {len(user_ids)}")
    if not user_ids:
        logger.warning("[SCHEDULER] No users in DB! Did everyone run /start?")
        return

    all_topics = CONSULATE_TOPICS + A2_TOPICS
    topic = random.choice(all_topics)
    key_phrases = topic.get("key_phrases", [])

    try:
        lesson_text = await ai.generate_daily_lesson(topic["id"], topic["title"], key_phrases)
    except Exception as e:
        logger.error(f"[SCHEDULER] Failed to generate lesson: {e}")
        lesson_text = f"Тема: {topic['title']}\n\nВременно недоступно, попробуй /lesson"

    message = (
        f"☀️ Доброе утро! Урок дня:\n"
        f"🇷🇴 {topic['title']} ({topic['ro_title']})\n\n"
        f"{lesson_text}\n\n"
        f"🎯 Проверь себя: /quiz\n"
        f"✏️ Переведи: /translate\n"
        f"✍️ Вставь слово: /fillword"
    )

    sent = 0
    for user_id in user_ids:
        if await _safe_send(bot, user_id, message):
            await db.save_daily_lesson(user_id, topic["id"])
            await db.update_streak(user_id)
            await db.add_points(user_id, 5)
            sent += 1
    logger.info(f"[SCHEDULER] Morning lesson sent to {sent}/{len(user_ids)} users")


async def send_evening_quiz(bot: Bot):
    user_ids = await db.get_all_user_ids()
    logger.info(f"[SCHEDULER] Evening quiz — users: {len(user_ids)}")
    if not user_ids:
        return

    topic = random.choice(CONSULATE_TOPICS)
    sent = 0
    for user_id in user_ids:
        try:
            recent_questions = await db.get_recent_questions(user_id, days=14)
            quiz = await ai.generate_quiz(topic["id"], topic["title"], recent_questions)
            if not isinstance(quiz.get("options"), list) or len(quiz["options"]) < 2:
                continue
            if not isinstance(quiz.get("correct_index"), int):
                quiz["correct_index"] = 0

            await db.save_asked_question(user_id, quiz["question"])
            store_scheduled_quiz(user_id, quiz)

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{chr(65+i)}) {opt}", callback_data=f"quiz_{i}")]
                for i, opt in enumerate(quiz["options"])
            ])
            message = (
                f"🌙 Вечерний квиз!\n\n"
                f"❓ {quiz['question']}\n\n"
                f"🇷🇴 {quiz.get('romanian_context', '')}"
            )
            try:
                await bot.send_message(user_id, message, reply_markup=keyboard)
                sent += 1
            except TelegramError as e:
                logger.warning(f"Cannot send quiz to {user_id}: {e}")
        except Exception as e:
            logger.warning(f"[SCHEDULER] Quiz error for {user_id}: {e}")
    logger.info(f"[SCHEDULER] Evening quiz sent to {sent}/{len(user_ids)} users")


async def send_motivational_message(bot: Bot):
    user_ids = await db.get_all_user_ids()
    logger.info(f"[SCHEDULER] Motivator — users: {len(user_ids)}")
    if not user_ids:
        return
    motivator = random.choice(MOTIVATIONAL_MESSAGES)
    for user_id in user_ids:
        await _safe_send(bot, user_id, motivator)


WEEKLY_VIDEO_SEARCHES = [
    ("learn romanian greetings phrases beginners", "Приветствия и фразы"),
    ("romanian numbers dates lesson A1", "Числа и даты"),
    ("romanian family vocabulary beginners", "Семья"),
    ("romanian citizenship interview tips", "Подготовка к консулу"),
    ("romanian pronunciation guide beginners", "Произношение"),
    ("romanian present tense verbs lesson", "Глаголы"),
    ("romanian culture traditions facts", "Культура Румынии"),
]


async def send_weekly_video(bot: Bot):
    user_ids = await db.get_all_user_ids()
    logger.info(f"[SCHEDULER] Weekly video — users: {len(user_ids)}")
    if not user_ids:
        return
    search_query, topic_label = random.choice(WEEKLY_VIDEO_SEARCHES)
    url = "https://www.youtube.com/results?search_query=" + search_query.replace(" ", "+")
    message = (
        f"🎬 Видео недели — {topic_label}:\n\n"
        f"{url}\n\n"
        f"Лучшие каналы: Romanian With Anca, RomanianPod101\n\n"
        f"После просмотра: /quiz"
    )
    for user_id in user_ids:
        await _safe_send(bot, user_id, message)


async def send_cultural_fact(bot: Bot):
    user_ids = await db.get_all_user_ids()
    logger.info(f"[SCHEDULER] Cultural fact — users: {len(user_ids)}")
    if not user_ids:
        return
    for user_id in user_ids:
        shown = await db.get_shown_fact_indices(user_id)
        available = [i for i in range(len(CULTURAL_FACTS)) if i not in shown]
        if not available:
            await db.reset_shown_facts(user_id)
            available = list(range(len(CULTURAL_FACTS)))
        idx = random.choice(available)
        await db.save_shown_fact(user_id, idx)
        await _safe_send(bot, user_id, f"🇷🇴 Факт о Румынии:\n\n{CULTURAL_FACTS[idx]}")


async def send_weekly_summary(bot: Bot):
    user_ids = await db.get_all_user_ids()
    logger.info(f"[SCHEDULER] Weekly summary — users: {len(user_ids)}")
    if not user_ids:
        return
    for user_id in user_ids:
        try:
            stats = await db.get_user_stats(user_id)
            summary = await ai.generate_weekly_summary(stats)
            await _safe_send(bot, user_id, f"📊 Итоги недели от Дракулы:\n\n{summary}")
        except Exception as e:
            logger.warning(f"[SCHEDULER] Summary error for {user_id}: {e}")


async def send_test_notification(bot: Bot, user_id: int):
    """Send immediate test message to verify scheduler pipeline works."""
    user_ids = await db.get_all_user_ids()
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz).strftime("%H:%M:%S")
    tz_label = "МСК" if "Moscow" in TIMEZONE else TIMEZONE
    message = (
        f"✅ Тест рассылки — {now} ({tz_label})\n\n"
        f"Планировщик работает!\n"
        f"Пользователей в базе: {len(user_ids)}\n\n"
        f"Следующий урок придёт в {MORNING_LESSON_HOUR}:00 {tz_label}."
    )
    await bot.send_message(user_id, message)


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)

    scheduler.add_job(
        send_morning_lesson,
        CronTrigger(hour=MORNING_LESSON_HOUR, minute=0, timezone=TIMEZONE),
        args=[bot], id="morning_lesson", replace_existing=True,
    )
    scheduler.add_job(
        send_evening_quiz,
        CronTrigger(hour=EVENING_QUIZ_HOUR, minute=0, timezone=TIMEZONE),
        args=[bot], id="evening_quiz", replace_existing=True,
    )
    scheduler.add_job(
        send_motivational_message,
        CronTrigger(day_of_week="mon,thu", hour=12, minute=0, timezone=TIMEZONE),
        args=[bot], id="motivator", replace_existing=True,
    )
    scheduler.add_job(
        send_weekly_video,
        CronTrigger(day_of_week="sun", hour=10, minute=0, timezone=TIMEZONE),
        args=[bot], id="weekly_video", replace_existing=True,
    )
    scheduler.add_job(
        send_cultural_fact,
        CronTrigger(day_of_week="wed", hour=15, minute=0, timezone=TIMEZONE),
        args=[bot], id="cultural_fact", replace_existing=True,
    )
    scheduler.add_job(
        send_weekly_summary,
        CronTrigger(day_of_week="sun", hour=18, minute=0, timezone=TIMEZONE),
        args=[bot], id="weekly_summary", replace_existing=True,
    )

    return scheduler
