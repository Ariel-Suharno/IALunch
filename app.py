from datetime import datetime
from html import escape
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from string import Template

from backend import (
    MEAL_PRICES,
    get_current_week_menu,
    get_line,
    get_mealviewer_week_menu,
    merge_week_menus,
    school_is_out,
)

SNACK_DROPDOWN_THRESHOLD = 45


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
        "beef",
        "pork",
    )
    for family in color_families:
        if family in allergen_name:
            return f"allergen-{family.replace(' ', '-')}"
    return "allergen-other"


def render_item_badges(allergens, dietary_tags=()):
    badges = [
        f'<span class="badge dietary">{escape(tag)}</span>'
        for tag in dietary_tags
    ]

    for allergen in allergens or ():
        badges.append(
            f'<span class="badge allergen {get_allergen_badge_class(allergen)}">'
            f'{escape(allergen)}</span>'
        )

    return " ".join(badges)


def get_snack_category(food):
    name = food.casefold()
    if any(term in name for term in ("ice cream", "icecream", "sundae")):
        return "Ice Cream"

    drink_terms = (
        "beverage", "20oz", "10oz", "soda", "coke", "cola", "gatorade",
        "juice", "tea", "lemonade", "latte", "powerade", "sprite", "fanta",
        "mello yello", "pibb", "sparkling ice", "vitamin water", "dasani",
        "propel", "smartwater", "water",
    )
    if any(term in name for term in drink_terms):
        return "Drinks"
    return "Snacks"


def render_menu_item(food, allergens_by_food, dietary_by_food):
    allergens = allergens_by_food.get(food)
    filter_tags = allergens or []
    dietary_tags = dietary_by_food.get(food, [])
    return (
        f'<li class="menu-item" '
        f'data-tags="{escape(json.dumps(filter_tags), quote=True)}">'
        f'{escape(food)} '
        f'{render_item_badges(allergens, dietary_tags)}'
        '</li>'
    )


def get_menu_tags(menu):
    tags = set()
    for day_data in menu.values():
        if isinstance(day_data, dict):
            for item_allergens in day_data.get("allergens", {}).values():
                tags.update(item_allergens)
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
    badges = [
        f'<span class="badge allergen {get_allergen_badge_class(tag)}">'
        f'{escape(tag)}</span>'
        for tag in tags
    ]
    badges.extend(
        f'<span class="badge dietary">{escape(tag)}</span>'
        for tag in sorted(dietary_tags)
    )
    if not badges:
        badges.append('<span class="badge allergen">No tags available</span>')
    return '<div class="tag-list">' + " ".join(badges) + '</div>'


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
            "Sides",
            "Snacks",
            "Other",
        ]

        for day, day_data in menu.items():
            if isinstance(day_data, dict):
                foods = day_data.get("foods", [])
                allergens_by_food = day_data.get("allergens", {})
                dietary_by_food = day_data.get("dietary", {})
                snack_foods = set(day_data.get("snacks", []))
                allergen_data_unavailable = day_data.get(
                    "allergen_data_unavailable",
                    False,
                )
            else:
                foods = day_data
                allergens_by_food = {}
                dietary_by_food = {}
                snack_foods = set()
                allergen_data_unavailable = False

            if day.startswith(today_name):
                card_class = 'class="card today-card"'
            else:
                card_class = 'class="card future-day" style="display:none;"'

            day_name, day_number = day.split()
            pretty_day = f"{day_name} ({current_month} {day_number})"
            output.append(f'<div {card_class}><h2>{pretty_day}</h2>')
            if allergen_data_unavailable:
                output.append(
                    '<p class="allergen-warning" role="status">'
                    'Allergen information is unavailable for this day.'
                    '</p>'
                )

            if school_is_out(foods):
                output.append(
                    '<div class="line-card"><h3>School Closed</h3>'
                    '<ul><li>No lunch menu available. Have a nice break!</li>'
                    '</ul></div></div>'
                )
                continue

            lines = {}
            for food in dict.fromkeys(foods):
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
