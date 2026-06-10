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

    day_energy = normalize_arcana(day)
    month_energy = normalize_arcana(month)
    year_energy = normalize_arcana(digit_sum(year))

    destiny_energy = normalize_arcana(day_energy + month_energy + year_energy)
    karma_energy = normalize_arcana(day_energy + year_energy)
    money_energy = normalize_arcana(month_energy + year_energy)
    relationship_energy = normalize_arcana(day_energy + month_energy)
    talent_energy = normalize_arcana(destiny_energy + relationship_energy)
    comfort_zone_energy = normalize_arcana(destiny_energy + karma_energy)

    return {
        "birth_date": date_text,
        "day_energy": day_energy,
        "month_energy": month_energy,
        "year_energy": year_energy,
        "destiny_energy": destiny_energy,
        "karma_energy": karma_energy,
        "money_energy": money_energy,
        "relationship_energy": relationship_energy,
        "talent_energy": talent_energy,
        "comfort_zone_energy": comfort_zone_energy,
    }
