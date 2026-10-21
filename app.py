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


def render_item_badges(allergens, dietary_tags=()):
    badges = [
        f'<span class="badge dietary">{escape(tag)}</span>'
        for tag in dietary_tags
    ]

    if not allergens:
        allergens = ["Allergen data unavailable"]

    for allergen in allergens:
        badges.append(
            f'<span class="badge allergen">{escape(allergen)}</span>'
        )

    return " ".join(badges)


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
        f'<span class="badge allergen">{escape(tag)}</span>'
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
    tags = [
        tag for tag in get_menu_tags(menu)
        if tag.casefold() != "no major allergens"
        and tag.casefold() != "allergen data unavailable"
    ]
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
            else:
                foods = day_data
                allergens_by_food = {}
                dietary_by_food = {}

            if day.startswith(today_name):
                card_class = 'class="card today-card"'
            else:
                card_class = 'class="card future-day" style="display:none;"'

            day_name, day_number = day.split()
            pretty_day = f"{day_name} ({current_month} {day_number})"
            output.append(f'<div {card_class}><h2>{pretty_day}</h2>')

            if school_is_out(foods):
                output.append(
                    '<div class="line-card"><h3>School Closed</h3>'
                    '<ul><li>No lunch menu available. Have a nice break!</li>'
                    '</ul></div></div>'
                )
                continue

            lines = {}
            for food in dict.fromkeys(foods):
                line_name = get_line(food)
                lines.setdefault(line_name, []).append(food)

            lines.setdefault("Lettuce Chop It", []).append("Salad Bar")

            output.append('<div class="line-container">')
            for line_name in display_order:
                if line_name not in lines:
                    continue

                output.append(
                    f'<div class="line-card"><h3>{line_name}</h3><ul>'
                )
                for food in lines[line_name]:
                    allergens = allergens_by_food.get(food, [])
                    filter_tags = [
                        tag for tag in allergens
                        if tag.casefold() != "no major allergens"
                    ]
                    output.append(
                        f'<li class="menu-item" '
                        f'data-tags="{escape(json.dumps(filter_tags), quote=True)}">'
                        f'{escape(food)} '
                        f'{render_item_badges(allergens_by_food.get(food), dietary_by_food.get(food, []))}'
                        '</li>'
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
