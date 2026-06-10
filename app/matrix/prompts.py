def build_personal_matrix_prompt(matrix: dict) -> str:
    base = matrix["base"]
    channels = matrix["channels"]

    return f"""
Ты — AI-консультант по Матрице судьбы на основе 22 арканов.

Сделай короткий, теплый разбор личной матрицы.

Дата рождения: {matrix["birth_date"]}

Энергии:
День: {base["day_arcana"]}
Месяц: {base["month_arcana"]}
Год: {base["year_arcana"]}
Предназначение: {base["destiny_arcana"]}
Центр: {base["center_arcana"]}
Деньги: {channels["money_arcana"]}
Отношения: {channels["relationship_arcana"]}
Карма: {channels["karma_arcana"]}

Формат:
<b>✨ Портрет</b>
<b>🎯 Предназначение</b>
<b>💰 Деньги и реализация</b>
<b>❤️ Отношения</b>
<b>🧭 Совет</b>

Правила:
- русский язык;
- до 1200 символов;
- без Markdown;
- только Telegram HTML;
- не пугай;
- не обещай гарантированных событий;
- пиши конкретно, без воды.
""".strip()


def build_compatibility_prompt(data: dict) -> str:
    p1 = data["person1"]
    p2 = data["person2"]
    pair = data["pair"]

    return f"""
Ты — AI-консультант по Матрице судьбы на основе 22 арканов.

Сделай короткий, теплый анализ совместимости пары по двум датам рождения.

Партнер 1: {data["date1"]}
Центр: {p1["base"]["center_arcana"]}
Предназначение: {p1["base"]["destiny_arcana"]}
Отношения: {p1["channels"]["relationship_arcana"]}

Партнер 2: {data["date2"]}
Центр: {p2["base"]["center_arcana"]}
Предназначение: {p2["base"]["destiny_arcana"]}
Отношения: {p2["channels"]["relationship_arcana"]}

Энергии союза:
Центр пары: {pair["center_arcana"]}
Предназначение пары: {pair["destiny_arcana"]}
Канал отношений: {pair["relationship_arcana"]}

Формат:
<b>❤️ Динамика пары</b>
<b>🤝 Сильные стороны</b>
<b>⚠️ Точки напряжения</b>
<b>🧭 Совет</b>

Правила:
- русский язык;
- до 1200 символов;
- без Markdown;
- только Telegram HTML;
- не пугай;
- не обещай гарантированных событий;
- пиши конкретно, без воды.
""".strip()


def build_money_channel_prompt(matrix: dict) -> str:
    base = matrix["base"]
    channels = matrix["channels"]

    return f"""
Ты — AI-консультант по Матрице судьбы на основе 22 арканов.

Сделай короткий, теплый и практичный разбор денежного канала по дате рождения.

Дата рождения: {matrix["birth_date"]}

Энергии:
День: {base["day_arcana"]}
Месяц: {base["month_arcana"]}
Год: {base["year_arcana"]}
Предназначение: {base["destiny_arcana"]}
Центр: {base["center_arcana"]}
Денежный канал: {channels["money_arcana"]}
Таланты: {channels["talent_arcana"]}
Карма: {channels["karma_arcana"]}

Формат:
<b>💰 Денежный канал</b>
<b>💼 Как легче зарабатывать</b>
<b>⚠️ Что может блокировать деньги</b>
<b>🚀 Что усиливает финансовый поток</b>
<b>🧭 Практический совет</b>

Правила:
- русский язык;
- до 1200 символов;
- без Markdown;
- только Telegram HTML;
- не обещай гарантированного дохода;
- не давай инвестиционных рекомендаций;
- не пугай;
- пиши конкретно, без воды.
""".strip()
