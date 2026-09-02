from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from datetime import datetime, timedelta
import re

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

    #Categorizes what words trigger off what dietary restriction tag, add as needed according to what type the ingredient is, needs fine tuning for certain menu items

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
        badges.append(
            '<span class="badge gf">GF</span>'
        )

    return " ".join(badges)

#Theortically, automatically changes the menu to the current week
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

    #Organizes food items into which line they're in, use keywords instead of whole name, add as needed

    academy_eats = [
        "nacho",
        "teriyaki",
        "tangerine",
        "sriracha",
        "general",
        "rice",
        #Check if this is correct line, if not, remove it
        "sichuan",
        #Check if this is correct line, if not, remove it
        "chow mein"
    ]

    hot_spot = [
        "pizza",
        "wings",
        "breaded",
        "pasta",
        "tender",
        "bbq",
        #Check if this is correct line, if not, remove it
        "wild mikes",
        "parmesan",
        "boil",
        "waffle",
        "roll",
        "bake",
        "ranch",
        "breadstick"
    ]

    go_gourmet = [
        "hamburger",
        "cheeseburger",
        "basket",
        "sandwich",
        "hot dog",
        "corndog"
    ]

    chop_it = [
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
        "mashed",
        "carrot",
        "tomatoes",
        "cucumber",
        "edamame"
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
    font-size:2.5rem;
}

h2{
    font-size:1.8rem;
}

h3{
    font-size:1.3rem;
}

li{
    font-size:1.1rem;
}

.container{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(260px,1fr));
    gap:15px;
    margin-top:20px;
}

.card{
    background:white;
    border-radius:12px;
    padding:15px;
    box-shadow:0 2px 5px rgba(0,0,0,.15);
}

.top-cards{
    display:flex;
    gap:20px;
    justify-content:center;
    flex-wrap:wrap;
    margin-bottom:30px;
}

.top-card{
    width:320px;
}

.today-card{
    max-width:900px;
    margin:auto;
    text-align:center;
}

.today-card ul{
    text-align:left;
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

.menu-toggle{
    display:block;
    margin:20px auto;
    padding:15px 25px;
    font-size:18px;
    font-weight:bold;
    background:#1565c0;
    color:white;
    border:none;
    border-radius:12px;
    cursor:pointer;
}

@media (max-width: 768px){

    .top-cards{
        flex-direction:column;
        align-items:center;
    }

    .top-card{
        width:100%;
        max-width:400px;
    }

    .today-card{
        width:100%;
    }
}

.line-card{
    background:white;
    border:1px solid #e5e7eb;
    border-radius:10px;
    margin-bottom:12px;
    overflow:hidden;
}

.line-card h3{
    margin:0;
    padding:10px;
    font-size:1.5rem;
    color:#374151;
    border-bottom:1px solid #e5e7eb;
}

.line-card ul{
    margin:0;
    padding:10px 10px 10px 30px;
}

.line-card ul{
    margin:0;
    padding-left:20px;
}

.line-container{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(250px,1fr));
    gap:12px;
}
</style>

</head>
<body>

<h1 id="menuTitle">Today's Lunch Menu</h1>

<div class="top-cards">

<div class="card top-card">
<h2>Legend</h2>

<p><span class="badge vegan">Vegan</span> Vegan</p>
<p><span class="badge vegetarian">Veggie</span> Vegetarian</p>
<p><span class="badge gf">GF</span> Gluten Friendly</p>

<small>
Dietary labels are estimated and may not match
official allergen information.
</small>

</div>

<div class="card top-card">
<h2>Meal Prices</h2>
"""

        for meal, price in MEAL_PRICES.items():
            html += f"<p>{meal}: {price}</p>"

        html += """
</div>

</div>

<button
    id="weekButton"
    class="menu-toggle"
    onclick="toggleWeek()">
    Show Full Week
</button>

<script>
function toggleWeek() {

    const hiddenCards =
        document.querySelectorAll('.future-day');

    const btn =
        document.getElementById('weekButton');

    const title =
        document.getElementById('menuTitle');

    let hidden =
        hiddenCards.length > 0 &&
        hiddenCards[0].style.display === 'none';

    hiddenCards.forEach(card => {
        card.style.display =
            hidden ? 'block' : 'none';
    });

    if (hidden) {
        btn.innerText = 'Show Only Today';
        title.innerText = "This Week's Lunch Menu";
    } else {
        btn.innerText = 'Show Full Week';
        title.innerText = "Today's Lunch Menu";
    }
}
</script>

<div class="container">
"""
        today_name = datetime.now().strftime("%A")

        for day, foods in menu.items():

            if day.startswith(today_name):
                card_class = 'class="card today-card"'
            else:
                card_class = (
                    'class="card future-day" '
                    'style="display:none;"'
                )

            html += f"""
<div {card_class}>
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

            STATIC_ITEMS = {
                "Lettuce Chop It": [
                    "Salad Bar",
                ] #, (incase there are any other static items to add to the menu, add them here)
                #"Line name": [
                #    "Static item 1",
                #]
            }

            for category, items in STATIC_ITEMS.items():

                if category not in lines:
                    lines[category] = []

                lines[category].extend(items)

            display_order = [
                "Academy Eats",
                "Hot Spot",
                "Lettuce Chop It",
                "Go Go Gourmet",
                "Sides",
                "Snacks",
                "Other"
            ]

            for line_name in display_order:

                if line_name not in lines:
                    continue

                html += f"""
            <div class="line-card">
            <h3>{line_name}</h3>
            <ul>
            """

                foods_in_line = lines[line_name]

                for food in foods_in_line:
                    html += f"<li>{food} {get_diet_badge(food)}</li>"

                html += """
            </ul>
            </div>
            """

            html += """
</div>
"""

        html += """
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
