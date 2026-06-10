import json
import random

CARDS_FILE = "/opt/bots/tarot_bot/data/tarot_cards.json"


def load_cards():
    with open(CARDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def draw_card():
    deck = load_cards()

    card = random.choice(deck)

    orientation = random.choice(
        ["прямая", "перевернутая"]
    )

    return {
        "name": card["name"],
        "image": card["image"],
        "orientation": orientation
    }


def draw_three_cards():
    deck = load_cards()

    cards = random.sample(deck, 3)

    result = []

    for card in cards:
        result.append(
            {
                "name": card["name"],
                "image": card["image"],
                "orientation": random.choice(
                    ["прямая", "перевернутая"]
                )
            }
        )

    return result
