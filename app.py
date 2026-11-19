from datetime import datetime
from html import escape
import json
import os
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from itertools import count
from string import Template

from backend import (
    MEAL_PRICES,
    get_current_week_menu,
    get_line,
    get_mealviewer_week_menu,
    get_school_closure_reason,
    merge_week_menus,
    school_is_out,
)

SNACK_DROPDOWN_THRESHOLD = 45
ITEM_INFO_IDS = count()
MEAT_TAGS = frozenset({"beef", "chicken", "turkey", "pork", "seafood"})
SALAD_BAR_INFO_NOTE = (
    "Salad bar nutrition and allergen values vary depending on each student's "
    "selections and customizations."
)


def get_allergen_badge_class(allergen):
    allergen_name = allergen.casefold()
    color_families = (
        "shellfish",
        "tree nut",
        "peanut",
        "sesame",
        "wheat",
        "milk",
        "egg",
        "soy",
        "fish",
        "seafood",
        "beef",
        "pork",
        "chicken",
        "turkey",
    )
    for family in color_families:
        if family in allergen_name:
            return f"allergen-{family.replace(' ', '-')}"
    return "allergen-other"


def get_dietary_badge_class(tag):
    tag_name = str(tag).strip()
    tag_key = tag_name.casefold()
    if tag_key == "vegetarian":
        return "dietary-vegetarian"
    if tag_key == "vegan":
        return "dietary"

    color_class = get_allergen_badge_class(tag_name)
    if color_class != "allergen-other":
        return color_class

    return "dietary"


def render_item_badges(allergens, dietary_tags=()):
    badges = []
    for tag in dietary_tags:
        badge_class = get_dietary_badge_class(tag)
        if badge_class.startswith("dietary"):
            badges.append(f'<span class="badge {badge_class}">{escape(tag)}</span>')
        else:
            badges.append(
                f'<span class="badge allergen {badge_class}">{escape(tag)}</span>'
            )

    for allergen in allergens or ():
        badges.append(
            f'<span class="badge allergen {get_allergen_badge_class(allergen)}">'
            f'{escape(allergen)}</span>'
        )

    return " ".join(badges)


def get_snack_category(food):
    name = food.casefold()
    if any(
        re.search(rf"(?<!\w){re.escape(term)}(?!\w)", name)
        for term in ("ice cream", "icecream", "sundae")
    ):
        return "Ice Cream"

    drink_terms = (
        "beverage", "20oz", "10oz", "soda", "coke", "cola", "gatorade",
        "juice", "tea", "lemonade", "latte", "powerade", "sprite", "fanta",
        "mello yello", "pibb", "sparkling ice", "vitamin water", "dasani",
        "propel", "smartwater", "water",
    )
    if any(
        re.search(rf"(?<!\w){re.escape(term)}(?!\w)", name)
        for term in drink_terms
    ):
        return "Drinks"
    return "Snacks"


def render_menu_item(
    food,
    allergens_by_food,
    dietary_by_food,
    calories_by_food,
    info_note=None,
):
    allergens = allergens_by_food.get(food, [])
    item_tags = dietary_by_food.get(food, [])
    meat_tags = [tag for tag in item_tags if tag.casefold() in MEAT_TAGS]
    dietary_tags = [tag for tag in item_tags if tag.casefold() not in MEAT_TAGS]
    filter_tags = list(dict.fromkeys([*allergens, *item_tags]))
    if allergens:
        allergen_details = render_item_badges(allergens)
    elif food in allergens_by_food:
        allergen_details = "No allergens listed."
    else:
        allergen_details = "Allergen information unavailable."

    calories = calories_by_food.get(food)
    calories_details = (
        f"{escape(str(calories))} calories"
        if calories is not None
        else "Calories unavailable."
    )
    meat_details = (
        '<strong>Meat tags</strong>'
        f'<div class="item-meat-tags">{render_item_badges((), meat_tags)}</div>'
        if meat_tags
        else ""
    )
    info_id = f"item-info-{next(ITEM_INFO_IDS)}"
    info_unavailable = food not in allergens_by_food and calories is None
    if info_note:
        info_control = (
            '<button type="button" class="item-info-trigger" '
            f'aria-label="Show information about {escape(food, quote=True)}" '
            f'aria-describedby="{info_id}">i</button>'
            f'<div id="{info_id}" class="item-info-content" role="tooltip" hidden>'
            f'<p>{escape(info_note)}</p>'
            '</div>'
        )
    elif info_unavailable:
        info_control = (
            '<button type="button" class="item-info-trigger item-info-unavailable" '
            'aria-label="Allergen and calorie information unavailable" disabled>×</button>'
        )
    else:
        info_control = (
            f'<button type="button" class="item-info-trigger" '
            f'aria-label="Show calories, allergens, and meat tags for {escape(food, quote=True)}" '
            f'aria-describedby="{info_id}">i</button>'
            f'<div id="{info_id}" class="item-info-content" role="tooltip" hidden>'
            f'<p>{calories_details}</p>'
            '<strong>Allergens</strong>'
            f'<div class="item-allergens">{allergen_details}</div>'
            f'{meat_details}'
            '</div>'
        )
    return (
        f'<li class="menu-item" '
        f'data-tags="{escape(json.dumps(filter_tags), quote=True)}">'
        f'<span class="menu-item-label">{escape(food)} '
        f'{render_item_badges((), dietary_tags)}</span>'
        f'{info_control}'
        '</li>'
    )


def get_menu_tags(menu):
    tags = set()
    for day_data in menu.values():
        if isinstance(day_data, dict):
            for item_allergens in day_data.get("allergens", {}).values():
                tags.update(item_allergens)
            for item_tags in day_data.get("dietary", {}).values():
                tags.update(item_tags)
    return sorted(tags)


def render_allergen_legend(menu):
    tags = get_menu_tags(menu)
    dietary_tags = {
        tag
        for day_data in menu.values()
        if isinstance(day_data, dict)
        for item_tags in day_data.get("dietary", {}).values()
        for tag in item_tags
    }
    legend_tags = sorted({*tags, *dietary_tags}, key=lambda value: value.casefold())
    badges = []
    seen = set()
    for tag in legend_tags:
        if tag in seen:
            continue
        seen.add(tag)
        badge_class = get_dietary_badge_class(tag)
        if badge_class.startswith("dietary"):
            badges.append(f'<span class="badge {badge_class}">{escape(tag)}</span>')
        else:
            badges.append(
                f'<span class="badge allergen {badge_class}">{escape(tag)}</span>'
            )
    if not badges:
        badges.append('<span class="badge allergen">No tags available</span>')
    return (
        '<p class="tag-disclaimer">'
        'Click or tap the info icon next to a menu item to open its allergens '
        'and calories. For allergy concerns, contact school nutrition; '
        'menu information may change.'
        '</p>'
        '<div class="tag-list">' + " ".join(badges) + '</div>'
    )


def render_filter_options(menu):
    tags = get_menu_tags(menu)
    return "".join(
        '<label class="filter-option">'
        f'<input type="checkbox" class="ingredient-filter" '
        'onchange="applyIngredientFilters()" '
        f'value="{escape(tag, quote=True)}">'
        f'<span>{escape(tag)}</span></label>'
        for tag in tags
    ) or '<p>No ingredient tags available.</p>'


def render_menu(menu):
    output = ['<div class="container today-view">']

    if menu.get("Error"):
        output.append(
            '<div class="card today-card"><h2>Menu unavailable</h2>'
            f'<p>{escape(menu["Error"][0])}</p></div>'
        )
    else:
        today_name = datetime.now().strftime("%A")
        current_month = datetime.now().strftime("%b")
        display_order = [
            "Academy Eats",
            "Hot Spot",
            "Lettuce Chop It",
            "Go Go Gourmet",
            "Cold Meals (Available in refrigerated section in all lines)",
            "Sides",
            "Snacks",
            "Other",
        ]

        for day, day_data in menu.items():
            if isinstance(day_data, dict):
                foods = day_data.get("foods", [])
                allergens_by_food = day_data.get("allergens", {})
                dietary_by_food = day_data.get("dietary", {})
                calories_by_food = day_data.get("calories", {})
                cold_meals = set(day_data.get("cold_meals", []))
                snack_foods = set(day_data.get("snacks", []))
                line_overrides = day_data.get("line_overrides", {})
                allergen_data_unavailable = day_data.get(
                    "allergen_data_unavailable",
                    False,
                )
            else:
                foods = day_data
                allergens_by_food = {}
                dietary_by_food = {}
                calories_by_food = {}
                cold_meals = set()
                snack_foods = set()
                line_overrides = {}
                allergen_data_unavailable = False

            if day.startswith(today_name):
                card_class = 'class="card today-card"'
            else:
                card_class = 'class="card future-day" style="display:none;"'

            day_name, day_number = day.split()
            pretty_day = f"{day_name} ({current_month} {day_number})"
            thanksgiving = any(
                food.casefold() == "thanksgiving"
                for food in foods
            )
            if thanksgiving:
                foods = [food for food in foods if food.casefold() != "thanksgiving"]
                pretty_day = f"{pretty_day} - Thanksgiving"
            output.append(f'<div {card_class}><h2>{pretty_day}</h2>')

            if school_is_out(foods):
                closure_reason = get_school_closure_reason(foods)
                output.append(
                    '<div class="line-card"><h3>School Closed</h3>'
                    '<ul><li>No lunch menu available.'
                    ' Have a nice break!'
                )
                if closure_reason:
                    output.append(
                        '<ul>'
                        f'<li>Reason: {escape(closure_reason)}</li>'
                        '</ul>'
                    )
                output.append('</li></ul></div></div>')
                continue

            if allergen_data_unavailable:
                output.append(
                    '<p class="allergen-warning" role="status">'
                    'Allergen information is unavailable for this day.'
                    '</p>'
                )

            lines = {}
            for food in dict.fromkeys(foods):
                if food in line_overrides:
                    line_name = line_overrides[food]
                elif food in cold_meals:
                    line_name = (
                        "Cold Meals (Available in refrigerated section in all lines)"
                    )
                else:
                    line_name = "Snacks" if food in snack_foods else get_line(food)
                lines.setdefault(line_name, []).append(food)

            lines.setdefault("Lettuce Chop It", []).append("Salad Bar")

            output.append('<div class="line-container">')
            for line_name in display_order:
                if line_name not in lines:
                    continue

                output.append(
                    f'<div class="line-card"><h3>{line_name}</h3>'
                )
                if line_name == "Snacks":
                    large_snack_list = (
                        len(snack_foods) > SNACK_DROPDOWN_THRESHOLD
                    )
                    if large_snack_list:
                        output.append(
                            '<details class="snack-dropdown">'
                            f'<summary>View {len(snack_foods)} snack items</summary>'
                            '<div class="snack-dropdown-content">'
                        )

                    snack_groups = {
                        category: []
                        for category in ("Snacks", "Drinks", "Ice Cream")
                    }
                    for food in lines[line_name]:
                        snack_groups[get_snack_category(food)].append(food)

                    for category, foods_in_category in snack_groups.items():
                        if not foods_in_category:
                            continue
                        output.append(
                            f'<h4 class="snack-group-title">{category}</h4>'
                            '<ul class="snack-group-items">'
                        )
                        output.extend(
                            render_menu_item(
                                food,
                                allergens_by_food,
                                dietary_by_food,
                                calories_by_food,
                            )
                            for food in foods_in_category
                        )
                        output.append('</ul>')
                    if large_snack_list:
                        output.append('</div></details>')
                    output.append('</div>')
                else:
                    output.append('<ul>')
                    for food in lines[line_name]:
                        output.append(
                            render_menu_item(
                                food,
                                allergens_by_food,
                                dietary_by_food,
                                calories_by_food,
                                info_note=(
                                    SALAD_BAR_INFO_NOTE
                                    if food == "Salad Bar"
                                    else None
                                ),
                            )
                        )
                    output.append('</ul></div>')
            output.append('</div></div>')

    output.append('</div>')
    return "\n".join(output)


def render_page(menu):
    template_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(template_path, encoding="utf-8") as template_file:
        template = Template(template_file.read())

    prices = "".join(
        f"<p>{escape(meal)}: {escape(price)}</p>"
        for meal, price in MEAL_PRICES.items()
    )
    return template.substitute(
        menu_tags=render_allergen_legend(menu),
        prices=prices,
        filters=render_filter_options(menu),
        menu=render_menu(menu),
    )


class MenuHandler(BaseHTTPRequestHandler):
    def do_GET(self):

        if self.path == "/Phoenix_Vector.svg":
            with open("Phoenix_Vector.svg", "rb") as f:
                self.send_response(200)
                self.send_header("Content-Type", "image/svg+xml")
                self.end_headers()
                self.wfile.write(f.read())
            return

        if self.path == "/style.css":
            with open(os.path.join(os.path.dirname(__file__), "style.css"), "rb") as f:
                self.send_response(200)
                self.send_header("Content-Type", "text/css; charset=utf-8")
                self.end_headers()
                self.wfile.write(f.read())
            return

        menu = merge_week_menus(
            get_current_week_menu(),
            get_mealviewer_week_menu(),
        )
        html = render_page(menu)

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/html"
        )
        self.end_headers()
        self.wfile.write(html.encode())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Server running at http://localhost:{port}")
    HTTPServer(("0.0.0.0", port), MenuHandler).serve_forever()
