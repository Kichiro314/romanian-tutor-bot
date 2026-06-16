# 🇷🇴 Romanian Tutor Bot — Инструкция по запуску

## Шаг 1 — Создать Telegram бота

1. Открой Telegram, найди **@BotFather**
2. Напиши `/newbot`
3. Задай имя: `Romanian Tutor Dracula` (или любое)
4. Задай username: `ro_tutor_bot` (или любое свободное, должно кончаться на `bot`)
5. Скопируй **токен** вида `1234567890:AAF...`

## Шаг 2 — Получить Anthropic API ключ

1. Зайди на https://console.anthropic.com
2. API Keys → Create Key
3. Скопируй ключ вида `sk-ant-api03-...`

## Шаг 3 — Настроить окружение

```bash
# Перейди в папку проекта
cd romanian_tutor_bot

# Скопируй шаблон настроек
cp .env.example .env

# Открой .env и заполни:
#   TELEGRAM_BOT_TOKEN=твой_токен_от_BotFather
#   ANTHROPIC_API_KEY=твой_ключ_от_anthropic
#   TIMEZONE=Europe/Moscow  (или Europe/Bucharest, UTC)
#   MORNING_LESSON_HOUR=9
#   EVENING_QUIZ_HOUR=19
```

## Шаг 4 — Установить зависимости

```bash
# Создай виртуальное окружение (рекомендуется)
python3 -m venv venv
source venv/bin/activate   # Mac/Linux
# или venv\Scripts\activate  # Windows

# Установи пакеты
pip install -r requirements.txt
```

## Шаг 5 — Запустить бота

```bash
python bot.py
```

Ты увидишь:
```
INFO - Scheduler started. Bot is ready!
INFO - Starting Romanian Tutor Bot...
```

Теперь найди своего бота в Telegram и напиши `/start`!

---

## Что умеет бот

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие и список команд |
| `/lesson` | Урок дня с ключевыми фразами |
| `/quiz` | Квиз с кнопками — выбери правильный ответ |
| `/word` | Слово дня с мемом и способом запомнить |
| `/consul` | Симуляция собеседования с консулом |
| `/translate` | Упражнение на перевод с русского |
| `/video` | Обучающее видео на YouTube |
| `/topics` | Вся программа курса |
| `/progress` | Стрик, очки, статистика |
| `/fact` | Интересный факт о Румынии |

## Автоматическое расписание

| Время | Событие |
|-------|---------|
| 09:00 каждый день | ☀️ Утренний урок |
| 19:00 каждый день | 🌙 Вечерний квиз |
| Пн, Чт 12:00 | 💪 Мотивационное сообщение |
| Ср 15:00 | 🇷🇴 Культурный факт |
| Вс 10:00 | 🎬 Видео недели |
| Вс 18:00 | 📊 Итоги недели |

---

## Запуск в фоне (продакшн на сервере)

```bash
# С nohup
nohup python bot.py > bot.log 2>&1 &

# Или через systemd / supervisor / pm2
```

## Структура файлов

```
romanian_tutor_bot/
├── bot.py          # Точка входа, handlers регистрация
├── handlers.py     # Обработчики команд и сообщений
├── ai_tutor.py     # Генерация контента через Claude AI
├── scheduler.py    # Расписание автоматических сообщений
├── database.py     # SQLite: пользователи, прогресс, слова
├── curriculum.py   # Темы, фразы, видео, факты
├── config.py       # Загрузка переменных окружения
├── requirements.txt
├── .env.example
└── tutor.db        # База данных (создаётся автоматически)
```
