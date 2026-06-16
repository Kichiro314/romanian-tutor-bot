# Romanian language curriculum: Consulate interview prep + A2 level

CONSULATE_TOPICS = [
    {
        "id": "greeting",
        "title": "Приветствие и представление",
        "ro_title": "Salut și prezentare",
        "description": "Первое, что скажешь консулу. Критично!",
        "key_phrases": [
            ("Bună ziua", "Добрый день"),
            ("Mă numesc...", "Меня зовут..."),
            ("Sunt cetățean...", "Я гражданин..."),
            ("Am venit pentru...", "Я пришёл для..."),
            ("Vă rog", "Пожалуйста"),
            ("Mulțumesc", "Спасибо"),
        ],
    },
    {
        "id": "personal_info",
        "title": "Личные данные",
        "ro_title": "Date personale",
        "description": "Дата рождения, адрес, семейное положение",
        "key_phrases": [
            ("Data nașterii mele este...", "Дата моего рождения..."),
            ("Locuiesc în...", "Я живу в..."),
            ("Sunt căsătorit/ă", "Я женат/замужем"),
            ("Sunt necăsătorit/ă", "Я не женат/не замужем"),
            ("Am copii", "У меня есть дети"),
            ("Nu am copii", "У меня нет детей"),
        ],
    },
    {
        "id": "family_roots",
        "title": "Румынские корни",
        "ro_title": "Rădăcini românești",
        "description": "Объяснить связь с Румынией — ключевая тема консула!",
        "key_phrases": [
            ("Bunicii mei sunt din România", "Мои бабушка/дедушка из Румынии"),
            ("Părinții mei au origini românești", "Мои родители румынского происхождения"),
            ("Familia mea este din Moldova istorică", "Моя семья из исторической Молдовы"),
            ("Am documente care dovedesc...", "У меня есть документы, которые доказывают..."),
            ("Suntem de origine română", "Мы румынского происхождения"),
        ],
    },
    {
        "id": "documents",
        "title": "Документы",
        "ro_title": "Documente",
        "description": "Что принести, как объяснить документы",
        "key_phrases": [
            ("Pașaport", "Паспорт"),
            ("Certificat de naștere", "Свидетельство о рождении"),
            ("Certificat de căsătorie", "Свидетельство о браке"),
            ("Acte de stare civilă", "Документы гражданского состояния"),
            ("Copie legalizată", "Нотариально заверенная копия"),
            ("Traducere autorizată", "Авторизованный перевод"),
        ],
    },
    {
        "id": "romania_basics",
        "title": "Базовые знания о Румынии",
        "ro_title": "Cunoștințe de bază despre România",
        "description": "Флаг, столица, история — консул может спросить",
        "key_phrases": [
            ("Capitala României este București", "Столица Румынии — Бухарест"),
            ("Steagul României este albastru, galben și roșu", "Флаг Румынии синий, жёлтый и красный"),
            ("Imnul național se numește Deșteaptă-te, române!", "Гимн называется 'Проснись, румын!'"),
            ("România este membră a Uniunii Europene", "Румыния — член Европейского союза"),
            ("Limba oficială este limba română", "Официальный язык — румынский"),
        ],
    },
    {
        "id": "numbers_dates",
        "title": "Числа и даты",
        "ro_title": "Numere și date",
        "description": "Числа 1-31, месяцы, годы — для дат документов",
        "key_phrases": [
            ("unu, doi, trei, patru, cinci", "один, два, три, четыре, пять"),
            ("șase, șapte, opt, nouă, zece", "шесть, семь, восемь, девять, десять"),
            ("ianuarie, februarie, martie", "январь, февраль, март"),
            ("aprilie, mai, iunie", "апрель, май, июнь"),
            ("iulie, august, septembrie", "июль, август, сентябрь"),
            ("octombrie, noiembrie, decembrie", "октябрь, ноябрь, декабрь"),
        ],
    },
]

A2_TOPICS = [
    {
        "id": "daily_routine",
        "title": "Распорядок дня",
        "ro_title": "Rutina zilnică",
        "description": "Рассказать о своём дне по-румынски",
    },
    {
        "id": "food_shopping",
        "title": "Еда и магазины",
        "ro_title": "Mâncare și cumpărături",
        "description": "Заказать еду, купить продукты",
    },
    {
        "id": "transport",
        "title": "Транспорт и путешествия",
        "ro_title": "Transport și călătorii",
        "description": "Как добраться, купить билет",
    },
    {
        "id": "work_hobbies",
        "title": "Работа и хобби",
        "ro_title": "Muncă și hobby-uri",
        "description": "Рассказать о себе, своих интересах",
    },
    {
        "id": "weather",
        "title": "Погода",
        "ro_title": "Vremea",
        "description": "Обсудить погоду — классический small talk",
    },
    {
        "id": "health",
        "title": "Здоровье",
        "ro_title": "Sănătate",
        "description": "Описать симптомы, посетить врача",
    },
    {
        "id": "directions",
        "title": "Ориентация в городе",
        "ro_title": "Orientare în oraș",
        "description": "Спросить дорогу, описать маршрут",
    },
    {
        "id": "emotions",
        "title": "Эмоции и чувства",
        "ro_title": "Emoții și sentimente",
        "description": "Выразить как ты себя чувствуешь",
    },
]

# Curated YouTube video links for Romanian learning
LEARNING_VIDEOS = [
    {
        "title": "Румынский алфавит и произношение",
        "url": "https://www.youtube.com/watch?v=g0bKFxnkOHU",
        "topic": "pronunciation",
        "level": "beginner",
        "description": "Учим алфавит — первый шаг к румынскому!",
    },
    {
        "title": "100 основных слов румынского языка",
        "url": "https://www.youtube.com/watch?v=pFJ98csDRsw",
        "topic": "vocabulary",
        "level": "beginner",
        "description": "Самые нужные слова для старта",
    },
    {
        "title": "Румынский за 30 минут",
        "url": "https://www.youtube.com/watch?v=sZoMFPlHmZk",
        "topic": "overview",
        "level": "beginner",
        "description": "Быстрый обзор языка — идеально для начала",
    },
    {
        "title": "Диалоги на румынском A1",
        "url": "https://www.youtube.com/watch?v=s3xqoI1FDBM",
        "topic": "speaking",
        "level": "beginner",
        "description": "Живые диалоги чтобы привыкнуть к звучанию",
    },
    {
        "title": "Румынская музыка — Zdob și Zdub",
        "url": "https://www.youtube.com/watch?v=LJJiCnk7QFI",
        "topic": "culture",
        "level": "any",
        "description": "Учим язык через крутую румынскую музыку!",
    },
    {
        "title": "Румынские числа 1-100",
        "url": "https://www.youtube.com/watch?v=kXsupNWHKqs",
        "topic": "numbers",
        "level": "beginner",
        "description": "Числа нужны для дат в документах консула",
    },
    {
        "title": "Present tense в румынском",
        "url": "https://www.youtube.com/watch?v=SsJyAQ1TSSY",
        "topic": "grammar",
        "level": "beginner",
        "description": "Как говорить о том что происходит сейчас",
    },
    {
        "title": "Румынские фразы для путешествий",
        "url": "https://www.youtube.com/watch?v=4s4k5mSnf5Q",
        "topic": "travel",
        "level": "beginner",
        "description": "Практичные фразы которые сразу можно использовать",
    },
]

MOTIVATIONAL_MESSAGES = [
    "🔥 Каждое слово по-румынски — это шаг к паспорту ЕС! Не останавливайся!",
    "🇷🇴 Буна зиуа, чемпион! Консул уже не знает, что его ждёт!",
    "💪 Ты учишь язык, которому 2000 лет! Это серьёзно — и ты тоже серьёзный!",
    "🎯 Один день без румынского — и консул выигрывает. Не дай ему шанс!",
    "🌟 Латинский язык с горными традициями — ты освоишь это, я уверен!",
    "📚 Бабушки-румынки учили язык без интернета. У тебя AI-репетитор — ты в плюсе!",
    "🚀 А2 — это не предел! После консула — Бухарест, паэлья... ой, мамалыга! 🍲",
    "✨ Fii mândru! Будь горд — ты выбрал один из самых красивых языков мира!",
    "🎪 Факт: румынский похож на итальянский. Учишь один — считай, бонус получил!",
    "🏆 Streak не сломан — честь семьи в безопасности! Продолжай!",
]

# Romanian cultural facts
CULTURAL_FACTS = [
    "🏰 Замок Бран (известный как 'замок Дракулы') — реальное место в Трансильвании. Влад Цепеш там почти не бывал, но легенда живёт!",
    "🍲 Мамалыга (mămăligă) — румынская полента из кукурузы. Национальная душа в тарелке!",
    "🐦 Румыния — дом для 60% популяции белых пеликанов Европы в дельте Дуная.",
    "🎻 Румынская народная музыка (doină) признана UNESCO нематериальным наследием человечества.",
    "💎 Румынский — единственный романский язык в Восточной Европе. Острова латыни среди славян!",
    "🌳 Румыния имеет одни из последних нетронутых лесов Европы — в Карпатах!",
    "⚽ Георге Хаджи — 'Карпатский Марадона' — лучший румынский футболист всех времён.",
    "🏛️ Дворец Парламента в Бухаресте — второе по величине здание в мире после Пентагона!",
    "🧛 Дракула в книге Брэма Стокера говорит с акцентом, но не по-румынски — автор никогда не был в Румынии 😂",
    "🎄 В Румынии Новый год отмечают с традицией 'урат' — ходить по домам с пожеланиями и получать монеты и орехи.",
]
