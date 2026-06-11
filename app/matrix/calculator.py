from datetime import datetime


def normalize_arcana(value: int) -> int:
    while value > 22:
        value -= 22
    while value <= 0:
        value += 22
    return value


def digit_sum(value: int) -> int:
    return sum(int(d) for d in str(value))


def parse_birth_date(date_text: str) -> tuple[int, int, int]:
    value = date_text.strip()

    if len(value) != 10 or value[2] != "." or value[5] != ".":
        raise ValueError("Дата должна быть в формате ДД.ММ.ГГГГ")

    try:
        dt = datetime.strptime(value, "%d.%m.%Y")
    except ValueError:
        raise ValueError("Такой даты не существует. Проверьте день, месяц и год.")

    current_year = datetime.now().year

    if dt.year < 1900 or dt.year > current_year:
        raise ValueError(f"Год рождения должен быть в диапазоне 1900–{current_year}")

    return dt.day, dt.month, dt.year


def calculate_personal_matrix(date_text: str) -> dict:
    day, month, year = parse_birth_date(date_text)

    day_arcana = normalize_arcana(day)
    month_arcana = normalize_arcana(month)
    year_arcana = normalize_arcana(digit_sum(year))

    destiny_arcana = normalize_arcana(day_arcana + month_arcana + year_arcana)
    center_arcana = normalize_arcana(day_arcana + month_arcana + year_arcana + destiny_arcana)

    karma_arcana = normalize_arcana(day_arcana + year_arcana)
    money_arcana = normalize_arcana(month_arcana + year_arcana)
    relationship_arcana = normalize_arcana(day_arcana + month_arcana)
    talent_arcana = normalize_arcana(destiny_arcana + relationship_arcana)
    comfort_zone_arcana = normalize_arcana(destiny_arcana + karma_arcana)

    return {
        "birth_date": date_text.strip(),
        "day": day,
        "month": month,
        "year": year,
        "base": {
            "day_arcana": day_arcana,
            "month_arcana": month_arcana,
            "year_arcana": year_arcana,
            "destiny_arcana": destiny_arcana,
            "center_arcana": center_arcana,
        },
        "channels": {
            "karma_arcana": karma_arcana,
            "money_arcana": money_arcana,
            "relationship_arcana": relationship_arcana,
            "talent_arcana": talent_arcana,
            "comfort_zone_arcana": comfort_zone_arcana,
        },
    }


def calculate_compatibility_matrix(date1: str, date2: str) -> dict:
    person1 = calculate_personal_matrix(date1)
    person2 = calculate_personal_matrix(date2)

    pair_center = normalize_arcana(
        person1["base"]["center_arcana"] + person2["base"]["center_arcana"]
    )
    pair_destiny = normalize_arcana(
        person1["base"]["destiny_arcana"] + person2["base"]["destiny_arcana"]
    )
    pair_relationship = normalize_arcana(
        person1["channels"]["relationship_arcana"] + person2["channels"]["relationship_arcana"]
    )

    return {
        "date1": person1["birth_date"],
        "date2": person2["birth_date"],
        "person1": person1,
        "person2": person2,
        "pair": {
            "center_arcana": pair_center,
            "destiny_arcana": pair_destiny,
            "relationship_arcana": pair_relationship,
        },
    }
