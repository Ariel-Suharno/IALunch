from datetime import datetime, timedelta
import json
import re
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

URL = "https://nutrition.fultonschools.org/MenuCalendar"

MEAL_PRICES = {
    "Student Lunch": "$3.35",
    "Reduced Lunch": "$0.00",
    "Adult Lunch": "$5.25",
    "Extra Milk": "$0.75"
}

CHEF_SELECTION_CATEGORIES = {
    "Chef Selection Hot Sandwich",
    "Chef Selection Crispy Chicken Basket",
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


def get_item_allergens(item):
    allergens = []
    for allergen in item.get("allergens", []):
        value = allergen.get("value")
        if value is not True and str(value).casefold() not in {"true", "1", "yes"}:
            continue

        name = allergen.get("name", "").strip()
        if name:
            name = re.sub(r"^[A-Z]{1,3}\s*-\s*(?=processed in )", "", name, flags=re.IGNORECASE)
            if name.casefold().startswith("processed in "):
                name = name[0].upper() + name[1:]
            allergens.append(name)

    return list(dict.fromkeys(
        name for name in allergens
        if name.casefold() != "no major allergens"
    ))


def get_item_dietary_tags(item):
    name = item.get("item_Name", "").strip().casefold()
    item_type = item.get("item_Type", "").strip().casefold()

    if "vegan" in item_type or re.search(r"\(vegan\)\s*$", name):
        return ["Vegan"]
    if "vegetarian" in item_type or re.search(r"\(v\)\s*$", name):
        return ["Vegetarian"]
    return []


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

        if current_day and line.casefold().startswith((
            "due to supply chain issues",
            "student meal prices for",
        )):
            break

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


def get_mealviewer_week_menu():
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    start_date = monday.strftime("%m-%d-%Y")
    end_date = sunday.strftime("%m-%d-%Y")
    url = (
        "https://api.mealviewer.com/api/v4/school/"
        f"InnovationAcademyHigh/{start_date}/{end_date}/1"
    )
    request = Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
    )

    try:
        with urlopen(request, timeout=20) as response:
            data = json.load(response)
    except (URLError, TimeoutError, json.JSONDecodeError):
        return {"Error": ["MealViewer menu is currently unavailable."]}

    menu = {}
    for schedule in data.get("menuSchedules", []):
        date_info = schedule.get("dateInformation", {})
        date = datetime.strptime(date_info["dateFull"][:10], "%Y-%m-%d")
        if date.weekday() > 4:
            continue

        foods = []
        snacks = []
        allergens_by_food = {}
        dietary_by_food = {}
        chef_selections = {
            category: [] for category in CHEF_SELECTION_CATEGORIES
        }
        seen = set()
        for block in schedule.get("menuBlocks", []):
            block_name = block.get("blockName", "").casefold()
            if block_name not in {"lunch", "a la carte"}:
                continue
            is_snack = block_name == "a la carte"

            for line in block.get("cafeteriaLineList", {}).get("data", []):
                items = line.get("foodItemList", {}).get("data", [])
                previous_food = None
                for item in items:
                    name = item.get("item_Name", "").strip()
                    item_type = item.get("item_Type", "").strip().lower()
                    if (
                        name
                        and item_type != "condiments"
                        and item.get("mvS_Visible", True)
                    ):
                        category = item.get("item_Type", "").strip()
                        category_items = chef_selections.get(category)
                        item_allergens = get_item_allergens(item)
                        item_dietary_tags = get_item_dietary_tags(item)
                        if name.lower().startswith(("w/", "with ")):
                            if previous_food:
                                foods[-1] += " " + name
                                combined_food = foods[-1]
                                allergens_by_food[combined_food] = list(
                                    dict.fromkeys(
                                        allergens_by_food.pop(previous_food, [])
                                        + item_allergens
                                    )
                                )
                                dietary_by_food[combined_food] = list(
                                    dict.fromkeys(
                                        dietary_by_food.pop(previous_food, [])
                                        + item_dietary_tags
                                    )
                                )
                                if (
                                    category_items
                                    and category_items[-1] == previous_food
                                ):
                                    category_items[-1] = combined_food
                                elif category_items is not None:
                                    category_items.append(name)
                                if is_snack:
                                    if previous_food in snacks:
                                        snacks[snacks.index(previous_food)] = combined_food
                                    elif combined_food not in snacks:
                                        snacks.append(combined_food)
                                previous_food = combined_food
                            else:
                                foods.append(name)
                                allergens_by_food[name] = item_allergens
                                if category_items is not None:
                                    category_items.append(name)
                                if is_snack and name not in snacks:
                                    snacks.append(name)
                                previous_food = name
                        else:
                            if name in seen:
                                allergens_by_food[name] = list(
                                    dict.fromkeys(
                                        allergens_by_food.get(name, [])
                                        + item_allergens
                                    )
                                )
                                dietary_by_food[name] = list(
                                    dict.fromkeys(
                                        dietary_by_food.get(name, [])
                                        + item_dietary_tags
                                    )
                                )
                                if is_snack and name not in snacks:
                                    snacks.append(name)
                                previous_food = name
                                continue
                            foods.append(name)
                            allergens_by_food[name] = item_allergens
                            if item_dietary_tags:
                                dietary_by_food[name] = item_dietary_tags
                            if category_items is not None:
                                category_items.append(name)
                            if is_snack:
                                snacks.append(name)
                            seen.add(name)
                            previous_food = name

        menu[f"{date.strftime('%A')} {date.day}"] = {
            "foods": foods,
            "snacks": snacks,
            "chef_selections": chef_selections,
            "allergens": allergens_by_food,
            "dietary": dietary_by_food,
        }

    return menu


def merge_week_menus(fulton_menu, mealviewer_menu):
    if fulton_menu.get("Error"):
        if mealviewer_menu and not mealviewer_menu.get("Error"):
            return {
                day: {
                    "foods": details["foods"],
                    "snacks": details.get("snacks", []),
                    "allergens": details.get("allergens", {}),
                    "dietary": details.get("dietary", {}),
                }
                for day, details in mealviewer_menu.items()
            }
        return fulton_menu

    if mealviewer_menu.get("Error"):
        mealviewer_menu = {}

    merged_menu = {}
    days = list(fulton_menu)
    days.extend(day for day in mealviewer_menu if day not in fulton_menu)

    for day in days:
        fulton_foods = fulton_menu.get(day, [])
        mealviewer_data = mealviewer_menu.get(day, {})
        if isinstance(mealviewer_data, dict):
            mealviewer_foods = mealviewer_data.get("foods", [])
            chef_selections = mealviewer_data.get("chef_selections", {})
            allergens_by_food = mealviewer_data.get("allergens", {})
            dietary_by_food = mealviewer_data.get("dietary", {})
            snack_foods = set(mealviewer_data.get("snacks", []))
        else:
            mealviewer_foods = []
            chef_selections = {}
            allergens_by_food = {}
            dietary_by_food = {}
            snack_foods = set()

        def normalize(food):
            food = re.sub(r"\s*\([^)]*\)", "", food.casefold())
            return re.sub(r"[^a-z0-9]", "", food)

        merged_foods = []
        merged_allergens = {}
        merged_dietary = {}
        merged_snacks = []
        seen = {}

        def add_food(food, allergens=None, has_allergen_data=False, dietary_tags=None, is_snack=False):
            key = normalize(food)
            if not key:
                return

            if key in seen:
                existing_food = seen[key]
                if is_snack and existing_food not in merged_snacks:
                    merged_snacks.append(existing_food)
                if has_allergen_data:
                    merged_allergens[existing_food] = list(
                        dict.fromkeys(
                            merged_allergens.get(existing_food, [])
                            + (allergens or [])
                        )
                    )
                if dietary_tags:
                    merged_dietary[existing_food] = list(
                        dict.fromkeys(
                            merged_dietary.get(existing_food, []) + dietary_tags
                        )
                    )
                return

            merged_foods.append(food)
            seen[key] = food
            if is_snack:
                merged_snacks.append(food)
            if has_allergen_data:
                merged_allergens[food] = list(allergens or [])
            if dietary_tags:
                merged_dietary[food] = list(dict.fromkeys(dietary_tags))

        for food in fulton_foods:
            category = food.strip()
            replacements = chef_selections.get(category, [])
            if replacements:
                for replacement in replacements:
                    add_food(
                        replacement,
                        allergens_by_food.get(replacement),
                        replacement in allergens_by_food,
                        dietary_by_food.get(replacement),
                    )
            else:
                add_food(food)

        for food in mealviewer_foods:
            add_food(
                food,
                allergens_by_food.get(food),
                food in allergens_by_food,
                dietary_by_food.get(food),
                food in snack_foods,
            )

        merged_menu[day] = {
            "foods": merged_foods,
            "snacks": merged_snacks,
            "allergens": merged_allergens,
            "dietary": merged_dietary,
            "allergen_data_unavailable": bool(fulton_foods) and not any(
                food not in snack_foods for food in mealviewer_foods
            ),
        }

    return merged_menu


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
        "chipotle bites",
        "chipotle chicken",
        "shrimp",
        "jerk chicken topper"
    ]

    go_gourmet = [
        "hamburger",
        "cheeseburger",
        "basket",
        "sandwich",
        "hot dog",
        "corndog",
        "chicken bites",
        "popcorn chicken",
        "nashville hot chicken nuggets"
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
        "cauliflower",
        "juice",
        "cubes",
        "applesauce",
        "frozen",
        "fruit",
        "tidbits",
        "frost",
        "peaches",
        "squash"
    ]

    snacks = [
        "cookie",
        "ice cream",
        "popcorn",
        "chips",
        "soda",
        "diet",
        "dole whip"
    ]

    if any(word in food for word in academy_eats):
        return "Academy Eats"

    if any(word in food for word in go_gourmet):
        return "Go Go Gourmet"

    if any(word in food for word in hot_spot):
        return "Hot Spot"

    if any(word in food for word in chop_it):
        return "Lettuce Chop It"

    if "chef salad" in food or "salad plate" in food:
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
