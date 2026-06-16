import random
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot
from telegram.constants import ParseMode

import database as db
import ai_tutor as ai
from curriculum import (
    CONSULATE_TOPICS,
    A2_TOPICS,
    LEARNING_VIDEOS,
    MOTIVATIONAL_MESSAGES,
    CULTURAL_FACTS,
)
from config import TIMEZONE, MORNING_LESSON_HOUR, EVENING_QUIZ_HOUR

logger = logging.getLogger(__name__)


async def send_morning_lesson(bot: Bot):
    user_ids = await db.get_all_user_ids()
    if not user_ids:
        return

    all_topics = CONSULATE_TOPICS + A2_TOPICS
    # Pick a random topic (different for different timing — randomize per broadcast)
    topic = random.choice(all_topics)
    key_phrases = topic.get("key_phrases", [])

    try:
        lesson_text = await ai.generate_daily_lesson(topic["id"], topic["title"], key_phrases)
    except Exception as e:
        logger.error(f"Failed to generate morning lesson: {e}")
        return

    message = (
        f"☀️ *Доброе утро! Урок дня:*\n"
        f"🇷🇴 *{topic['title']}* — _{topic['ro_title']}_\n\n"
        f"{lesson_text}\n\n"
        f"🎯 Проверь себя: /quiz\n"
        f"✏️ Переведи: /translate"
    )

    for user_id in user_ids:
        try:
            await bot.send_message(user_id, message, parse_mode=ParseMode.MARKDOWN)
            await db.save_daily_lesson(user_id, topic["id"])
            await db.update_streak(user_id)
            await db.add_points(user_id, 5)
        except Exception as e:
            logger.warning(f"Cannot send to {user_id}: {e}")


async def send_evening_quiz(bot: Bot):
    user_ids = await db.get_all_user_ids()
    if not user_ids:
        return

    topic = random.choice(CONSULATE_TOPICS)

    try:
        quiz = await ai.generate_quiz(topic["id"], topic["title"])
    except Exception as e:
        logger.error(f"Failed to generate evening quiz: {e}")
        return

    message = (
        f"🌙 *Вечерний квиз!*\n\n"
        f"❓ {quiz['question']}\n\n"
        f"🇷🇴 _{quiz.get('romanian_context', '')}_\n\n"
        + "\n".join([f"{chr(65+i)}) {opt}" for i, opt in enumerate(quiz['options'])])
        + f"\n\n_Ответ: открой /quiz для интерактивного квиза!_"
    )

    for user_id in user_ids:
        try:
            await bot.send_message(user_id, message, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.warning(f"Cannot send quiz to {user_id}: {e}")


async def send_motivational_message(bot: Bot):
    user_ids = await db.get_all_user_ids()
    motivator = random.choice(MOTIVATIONAL_MESSAGES)

    for user_id in user_ids:
        try:
            await bot.send_message(user_id, motivator, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.warning(f"Cannot send motivator to {user_id}: {e}")


async def send_weekly_video(bot: Bot):
    user_ids = await db.get_all_user_ids()
    video = random.choice(LEARNING_VIDEOS)

    message = (
        f"🎬 *Видео недели для изучения румынского:*\n\n"
        f"📺 *{video['title']}*\n"
        f"_{video['description']}_\n\n"
        f"🔗 {video['url']}\n\n"
        f"Посмотри и потом тестируй себя: /quiz 🎯"
    )

    for user_id in user_ids:
        try:
            await bot.send_message(user_id, message, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.warning(f"Cannot send video to {user_id}: {e}")


async def send_cultural_fact(bot: Bot):
    user_ids = await db.get_all_user_ids()
    fact = random.choice(CULTURAL_FACTS)

    message = f"🇷🇴 *Факт среды о Румынии:*\n\n{fact}\n\n_Знание культуры помогает на собеседовании!_"

    for user_id in user_ids:
        try:
            await bot.send_message(user_id, message, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.warning(f"Cannot send fact to {user_id}: {e}")


async def send_weekly_summary(bot: Bot):
    user_ids = await db.get_all_user_ids()

    for user_id in user_ids:
        try:
            stats = await db.get_user_stats(user_id)
            summary = await ai.generate_weekly_summary(stats)
            await bot.send_message(
                user_id,
                f"📊 *Итоги недели от Дракулы:*\n\n{summary}",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.warning(f"Cannot send summary to {user_id}: {e}")


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)

    # Morning lesson every day at configured hour
    scheduler.add_job(
        send_morning_lesson,
        CronTrigger(hour=MORNING_LESSON_HOUR, minute=0, timezone=TIMEZONE),
        args=[bot],
        id="morning_lesson",
        name="Morning Romanian Lesson",
        replace_existing=True,
    )

    # Evening quiz every day
    scheduler.add_job(
        send_evening_quiz,
        CronTrigger(hour=EVENING_QUIZ_HOUR, minute=0, timezone=TIMEZONE),
        args=[bot],
        id="evening_quiz",
        name="Evening Quiz",
        replace_existing=True,
    )

    # Motivational message Mon/Thu at noon
    scheduler.add_job(
        send_motivational_message,
        CronTrigger(day_of_week="mon,thu", hour=12, minute=0, timezone=TIMEZONE),
        args=[bot],
        id="motivator",
        name="Motivational Message",
        replace_existing=True,
    )

    # Weekly video every Sunday morning
    scheduler.add_job(
        send_weekly_video,
        CronTrigger(day_of_week="sun", hour=10, minute=0, timezone=TIMEZONE),
        args=[bot],
        id="weekly_video",
        name="Weekly Learning Video",
        replace_existing=True,
    )

    # Cultural fact every Wednesday at 15:00
    scheduler.add_job(
        send_cultural_fact,
        CronTrigger(day_of_week="wed", hour=15, minute=0, timezone=TIMEZONE),
        args=[bot],
        id="cultural_fact",
        name="Cultural Fact Wednesday",
        replace_existing=True,
    )

    # Weekly summary every Sunday evening
    scheduler.add_job(
        send_weekly_summary,
        CronTrigger(day_of_week="sun", hour=18, minute=0, timezone=TIMEZONE),
        args=[bot],
        id="weekly_summary",
        name="Weekly Progress Summary",
        replace_existing=True,
    )

    return scheduler
