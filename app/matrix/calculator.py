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
    try:
        dt = datetime.strptime(date_text.strip(), "%d.%m.%Y")
        return dt.day, dt.month, dt.year
    except ValueError:
        raise ValueError("Дата должна быть в формате ДД.ММ.ГГГГ")


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
