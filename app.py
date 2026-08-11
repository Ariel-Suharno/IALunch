from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from datetime import datetime, timedelta
import re

URL = "https://nutrition.fultonschools.org/MenuCalendar"

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

    #if "w/" in text:
    #    return None

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
        badges.append(
            '<span class="badge vegan">Vegan</span>'
        )

    if (
        not contains_meat
        and (
            contains_dairy
            or "pizza" in food
            or "nachos" in food
            or "mac n" in food
        )
    ):
        badges.append(
            '<span class="badge vegetarian">Veggie</span>'
        )

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
        "tater tots",
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
        "jerk"
    ]

    if not any(word in food for word in gluten_words):
        badges.append(
            '<span class="badge gf">GF</span>'
        )

    return " ".join(badges)


def get_current_week_menu():
    html = get_innovation_html()

    text = re.sub(r"<[^>]+>", "\n", html)

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    today = datetime.now()
    monday = today - timedelta(days=today.weekday())

    week_headers = []

    day_names = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday"
    ]

    for i in range(5):
        d = monday + timedelta(days=i)
        week_headers.append(
            f"{day_names[i]} {d.day}"
        )

    start_index = None

    monday_header = week_headers[0]

    for index, menu_line in enumerate(lines):

        same_day = (menu_line == monday_header)

        if same_day:
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

        if (
            current_day
            and line.startswith("Monday ")
            and line != week_headers[0]
        ):
            break

        item = clean(line)

        if item:
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
        "rice"
    ]

    hot_spot = [
        "pizza",
        "wings",
        "breaded",
        "pasta",
        "tender",
        "bbq",
        "parmesan",
        "sichuan",
        "boil",
        "waffle",
        "roll",
        "bake"
    ]

    line_3 = [
        "hamburger",
        "cheeseburger",
        "basket",
        "sandwich",
        "hot dog",
        "corndog"
    ]

    line_4 = [
        "carrot",
        "tomatoes",
        "cucumber"
    ]

    sides = [
        "tater",
        "assorted",
        "bean",
        "fries",
        "corn",
        "steamed",
        "salad",
        "slushies",
        "mashed"
    ]

    snacks = [
        "cookie",
        "ice cream",
        "popcorn",
        "chips"
        "soda",
        "diet"
    ]

    if any(word in food for word in academy_eats):
        return "Academy Eats"

    if any(word in food for word in hot_spot):
        return "The Hot Spot"

    if any(word in food for word in line_3):
        return "line_3"

    if any(word in food for word in line_4):
        return "line_4"

    if any(word in food for word in sides):
            return "Sides"

    if any(word in food for word in snacks):
            return "Snacks"

    return "Other"

class MenuHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        menu = get_current_week_menu()

        html = """
<!DOCTYPE html>
<html>
<head>
<title>Fulton Menu</title>

<style>
body{
    font-family:Arial,sans-serif;
    background:#eef2f7;
    padding:20px;
}

h1{
    text-align:center;
}

.container{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(260px,1fr));
    gap:15px;
}

.card{
    background:white;
    border-radius:12px;
    padding:15px;
    box-shadow:0 2px 5px rgba(0,0,0,.15);
}

.badge{
    display:inline-block;
    padding:3px 8px;
    margin-left:4px;
    border-radius:999px;
    color:white;
    font-size:11px;
    font-weight:bold;
}

.vegan{
    background:#2e7d32;
}

.vegetarian{
    background:#ef6c00;
}

.gf{
    background:#1565c0;
}
</style>

</head>
<body>

<h1>Innovation Lunch Menu</h1>

<div class="container">
"""

        for day, foods in menu.items():
            html += f"""
<div class="card">
<h2>{day}</h2>
"""

            seen = set()

            lines = {}

            for food in foods:

                if food not in seen:
                    seen.add(food)

                    line_name = get_line(food)

                    if line_name not in lines:
                        lines[line_name] = []

                    lines[line_name].append(food)

            display_order = [
                "Academy Eats",
                "The Hot Spot",
                "line_3",
                "line_4",
                "Sides",
                "Snacks",
                "Other"
            ]

            for line_name in display_order:

                if line_name not in lines:
                    continue

                html += f"<h3>{line_name}</h3><ul>"

                foods_in_line = lines[line_name]

                for food in foods_in_line:
                    html += f"<li>{food} {get_diet_badge(food)}</li>"

                html += "</ul>"

            html += """
</div>
"""

        html += """
</div>

<div class="card" style="max-width:600px;margin:20px auto;">
<h2>Legend</h2>

<p><span class="badge vegan">Vegan</span> Vegan</p>

<p><span class="badge vegetarian">Veggie</span> Vegetarian</p>

<p><span class="badge gf">GF</span> Gluten Friendly</p>

<small>
Dietary labels are estimated and may not match
official allergen information.
</small>
</div>

</body>
</html>
"""

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/html"
        )
        self.end_headers()
        self.wfile.write(html.encode())

print("Server running at http://localhost:8000")

import os

port = int(os.environ.get("PORT", 8000))

HTTPServer(
    ("0.0.0.0", port),
    MenuHandler
).serve_forever()