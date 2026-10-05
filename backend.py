from datetime import datetime, timedelta
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

URL = "https://nutrition.fultonschools.org/MenuCalendar"

MEAL_PRICES = {
    "Student Lunch": "$3.35",
    "Reduced Lunch": "$0.00",
    "Adult Lunch": "$5.25",
    "Extra Milk": "$0.75"
}


def get_innovation_html():
    html = urlopen(URL).read().decode("utf-8", errors="ignore")

    viewstate = re.search(
        r'id="__VIEWSTATE" value="([^"]+)"',
        html
    ).group(1)

    eventvalidation = re.search(
        r'id="__EVENTVALIDATION" value="([^"]+)"',
        html
    ).group(1)

    data = {
        "__VIEWSTATE": viewstate,
        "__EVENTVALIDATION": eventvalidation,
        "__EVENTTARGET": "",
        "__EVENTARGUMENT": "",
        "ctl00$MainContent$DdlSites": "7023",
        "ctl00$MainContent$DdlMealPeriod": "Lunch"
    }

    request = Request(
        URL,
        data=urlencode(data).encode(),
        method="POST"
    )

    return urlopen(request).read().decode(
        "utf-8",
        errors="ignore"
    )


def clean(text):
    text = text.replace("*NEW*", "").strip()
    text = re.sub(r",\s*Big Daddy's \(8\)$", "", text).strip()

    if "$" in text:
        return None

    if "Meal Prices" in text:
        return None

    bad_words = [
        "Menu",
        "Interactive Menus",
        "Rate your Experience",
        "Select School",
        "Select Month",
        "Select Meal Period",
        "FULTON COUNTY SCHOOL NUTRITION",
    ]

    for word in bad_words:
        if word in text:
            return None

    if len(text) < 3:
        return None

    return text


def get_diet_badge(food):
    food = food.lower()

    meat = [
        "chicken",
        "beef",
        "turkey",
        "pepperoni",
        "ham",
        "sausage",
        "shrimp",
        "burger",
        "hot dog",
        "nuggets",
        "drumstick",
        "meat lovers",
        "kielbasa",
        "corndog",
        "grande",
        "wings",
        "bbq"
    ]

    dairy = [
        "cheese",
        "yogurt",
        "milk",
        "mozzarella",
        "parmesan",
        "stuffed"
    ]

    badges = []

    contains_meat = any(word in food for word in meat)
    contains_dairy = any(word in food for word in dairy)

    if (
        not contains_meat
        and not contains_dairy
        and any(
            word in food
            for word in [
                "fruit",
                "broccoli",
                "beans",
                "peas",
                "carrots",
                "cucumber",
                "tomatoes",
                "salad",
                "corn",
                "broccoli",
            ]
        )
    ):
        badges.append("Vegan")

    if (
        not contains_meat
        and (
            contains_dairy
            or "pizza" in food
            or "nachos" in food
            or "mac n" in food
        )
    ):
        badges.append("Veggie")

    gluten_words = [
        "bread",
        "breadstick",
        "pizza",
        "cookie",
        "waffle",
        "croissant",
        "pasta",
        "bun",
        "burger",
        "chicken",
        "shrimp",
        "mac",
        "corndog",
        "nachos",
        "wings",
        "sandwich",
        "fries",
        "boil",
        "wheat",
        "pasta",
        "jerk",
        "bake"
    ]

    if not any(word in food for word in gluten_words):
        badges.append("GF")

    return badges


# Automatically selects the current week's menu.
def get_current_week_menu():
    html = get_innovation_html()
    text = re.sub(r"<[^>]+>", "\n", html)

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    #today = datetime.now() - timedelta(days=7)
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    week_headers = []
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

    for index in range(5):
        day = monday + timedelta(days=index)
        week_headers.append(f"{day_names[index]} {day.day}")

    start_index = None
    monday_header = week_headers[0]

    for index, menu_line in enumerate(lines):
        if menu_line == monday_header:
            start_index = index
            break

    if start_index is None:
        return {
            "Error": [
                f"Could not locate week beginning {week_headers[0]}"
            ]
        }

    menu = {}
    current_day = None

    for line in lines[start_index:]:
        if line in week_headers:
            current_day = line
            menu[current_day] = []
            continue

        is_day_header = re.fullmatch(
            r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday) \d{1,2}",
            line
        )
        if current_day and is_day_header and line not in week_headers:
            break

        item = clean(line)

        if item:
            if (
                menu[current_day]
                and (
                    item.lower().startswith("w/")
                    or item.lower().startswith("with ")
                )
            ):
                menu[current_day][-1] += " " + item
            else:
                menu[current_day].append(item)

    return menu


def get_line(food):
    food = food.lower()

    academy_eats = [
        "nacho",
        "teriyaki",
        "tangerine",
        "sriracha",
        "general",
        "rice",
        "sichuan",
        "chow mein"
    ]

    hot_spot = [
        "pizza",
        "wings",
        "breaded",
        "pasta",
        "tender",
        "bbq",
        "wild mikes",
        "parmesan",
        "boil",
        "waffle",
        "roll",
        "bake",
        "ranch",
        "breadstick",
        "mac",
        "bites"
    ]

    go_gourmet = [
        "hamburger",
        "cheeseburger",
        "basket",
        "sandwich",
        "hot dog",
        "corndog"
    ]

    chop_it = []

    sides = [
        "tater",
        "assorted",
        "bean",
        "fries",
        "corn",
        "steamed",
        "salad",
        "slushies",
        "mashed",
        "carrot",
        "tomatoes",
        "cucumber",
        "edamame",
        "cauliflower"
    ]

    snacks = [
        "cookie",
        "ice cream",
        "popcorn",
        "chips",
        "soda",
        "diet"
    ]

    if any(word in food for word in academy_eats):
        return "Academy Eats"

    if any(word in food for word in hot_spot):
        return "Hot Spot"

    if any(word in food for word in go_gourmet):
        return "Go Go Gourmet"

    if any(word in food for word in chop_it):
        return "Lettuce Chop It"

    if any(word in food for word in sides):
        return "Sides"

    if any(word in food for word in snacks):
        return "Snacks"

    return "Other"


def school_is_out(foods):
    ignore_words = [
        "milk",
        "breakfast",
        "lunch",
        "adult",
        "reduced"
    ]

    real_food_count = 0

    for food in foods:
        text = food.lower()

        if any(word in text for word in ignore_words):
            continue

        real_food_count += 1

    return real_food_count <= 1
