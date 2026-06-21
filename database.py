import aiosqlite
from datetime import date, datetime

import os
DB_PATH = os.environ.get("DB_PATH", "tutor.db")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
                streak INTEGER DEFAULT 0,
                last_active TEXT,
                total_points INTEGER DEFAULT 0,
                lesson_count INTEGER DEFAULT 0,
                level TEXT DEFAULT 'beginner'
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS learned_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                romanian TEXT,
                russian TEXT,
                learned_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS quiz_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                question TEXT,
                correct INTEGER,
                answered_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS daily_lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                topic TEXT,
                sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS asked_quiz_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                question TEXT,
                asked_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS shown_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                fact_index INTEGER,
                shown_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, fact_index),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS learned_verbs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                verb_ro TEXT,
                meaning_ru TEXT,
                example_ro TEXT DEFAULT '',
                learned_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, verb_ro),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        await db.commit()


async def upsert_user(user_id: int, username: str, first_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name
        """, (user_id, username, first_name))
        await db.commit()


async def get_user(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def update_streak(user_id: int):
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT last_active, streak FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
        if not row:
            return 0
        last_active = row["last_active"]
        streak = row["streak"]
        yesterday = (date.today().replace(day=date.today().day - 1)).isoformat() if date.today().day > 1 else None
        if last_active == today:
            return streak
        elif last_active == yesterday:
            streak += 1
        else:
            streak = 1
        await db.execute(
            "UPDATE users SET streak = ?, last_active = ?, lesson_count = lesson_count + 1 WHERE user_id = ?",
            (streak, today, user_id)
        )
        await db.commit()
        return streak


async def add_points(user_id: int, points: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET total_points = total_points + ? WHERE user_id = ?", (points, user_id))
        await db.commit()


async def save_quiz_result(user_id: int, question: str, correct: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO quiz_results (user_id, question, correct) VALUES (?, ?, ?)",
            (user_id, question, int(correct))
        )
        await db.commit()


async def save_learned_words(user_id: int, words: list[tuple[str, str]]):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany(
            "INSERT OR IGNORE INTO learned_words (user_id, romanian, russian) VALUES (?, ?, ?)",
            [(user_id, w[0], w[1]) for w in words]
        )
        await db.commit()


async def get_all_user_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


async def get_user_stats(user_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
        async with db.execute(
            "SELECT COUNT(*) as cnt, SUM(correct) as correct FROM quiz_results WHERE user_id = ?", (user_id,)
        ) as cursor:
            quiz = await cursor.fetchone()
        async with db.execute(
            "SELECT COUNT(DISTINCT romanian) as words FROM learned_words WHERE user_id = ?", (user_id,)
        ) as cursor:
            words = await cursor.fetchone()
        async with db.execute(
            "SELECT COUNT(*) as verbs FROM learned_verbs WHERE user_id = ?", (user_id,)
        ) as cursor:
            verbs = await cursor.fetchone()
        return {
            "streak": user["streak"] if user else 0,
            "points": user["total_points"] if user else 0,
            "lessons": user["lesson_count"] if user else 0,
            "quiz_total": quiz["cnt"] or 0,
            "quiz_correct": int(quiz["correct"] or 0),
            "words_learned": words["words"] or 0,
            "verbs_learned": verbs["verbs"] or 0,
        }


async def save_daily_lesson(user_id: int, topic: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO daily_lessons (user_id, topic) VALUES (?, ?)", (user_id, topic))
        await db.commit()


async def get_recent_topics(user_id: int, limit: int = 7) -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT topic FROM daily_lessons WHERE user_id = ? ORDER BY sent_at DESC LIMIT ?",
            (user_id, limit)
        ) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


async def save_asked_question(user_id: int, question: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO asked_quiz_questions (user_id, question) VALUES (?, ?)",
            (user_id, question)
        )
        # Keep only last 50 questions per user
        await db.execute("""
            DELETE FROM asked_quiz_questions
            WHERE user_id = ? AND id NOT IN (
                SELECT id FROM asked_quiz_questions
                WHERE user_id = ?
                ORDER BY asked_at DESC LIMIT 50
            )
        """, (user_id, user_id))
        await db.commit()


async def get_shown_fact_indices(user_id: int) -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT fact_index FROM shown_facts WHERE user_id = ?", (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


async def save_shown_fact(user_id: int, fact_index: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO shown_facts (user_id, fact_index) VALUES (?, ?)",
            (user_id, fact_index)
        )
        await db.commit()


async def reset_shown_facts(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM shown_facts WHERE user_id = ?", (user_id,))
        await db.commit()


async def save_learned_verb(user_id: int, verb_ro: str, meaning_ru: str, example_ro: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO learned_verbs (user_id, verb_ro, meaning_ru, example_ro) VALUES (?, ?, ?, ?)",
            (user_id, verb_ro, meaning_ru, example_ro)
        )
        await db.commit()


async def get_learned_verbs(user_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT verb_ro, meaning_ru, example_ro, learned_at FROM learned_verbs WHERE user_id = ? ORDER BY learned_at DESC",
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_learned_verb_count(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM learned_verbs WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def get_recent_questions(user_id: int, days: int = 14) -> list[str]:
    """Return questions asked in the last N days to avoid repeats."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT question FROM asked_quiz_questions
            WHERE user_id = ?
              AND asked_at >= datetime('now', ?)
            ORDER BY asked_at DESC
        """, (user_id, f"-{days} days")) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
