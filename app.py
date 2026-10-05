from datetime import datetime
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

from backend import (
    MEAL_PRICES,
    get_current_week_menu,
    get_diet_badge,
    get_line,
    school_is_out,
)


def render_diet_badges(food):
    badge_classes = {
        "Vegan": "vegan",
        "Veggie": "vegetarian",
        "GF": "gf",
    }
    return " ".join(
        f'<span class="badge {badge_classes[badge]}">{badge}</span>'
        for badge in get_diet_badge(food)
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
            
        menu = get_current_week_menu()

        html = """
<!DOCTYPE html>
<html>
<head>
<title>Fulton Menu</title>

<link rel="icon"
      type="image/svg+xml"
      href="Phoenix_Vector.svg">

<style>
body{
    font-family:Arial,sans-serif;
    background:#eef2f7;
    margin: 0;
}

.page-content{
    padding:20px;
}

h1{
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
    margin-top:20px;
}

.week-view{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(350px,1fr));
    gap:15px;
}

.today-view{
    display:flex;
    justify-content:center;
}

.card{
    background:white;
    border-radius:12px;
    padding:15px;
    box-shadow:0 2px 5px rgba(0,0,0,.15);
    min-width:0;
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
    width:auto;
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

.tv-toggle{
    margin-left:auto;
    padding:10px 16px;
    border:1px solid rgba(255,255,255,.7);
    border-radius:6px;
    background:#ffffff;
    color:#234b64;
    font-size:1rem;
    font-weight:bold;
    cursor:pointer;
    flex-shrink:0;
}

.tv-toggle:hover,
.tv-toggle:focus-visible{
    background:#e7f0f5;
}

@media (max-width: 768px){

    .top-cards{
        flex-direction:column;
        align-items:center;
    }

    .today-card{
        width:100%;
    }
}

.top-card{
        background:#ffffff;
        border:1px solid #3d79b3;
        border-radius:6px;
        overflow:hidden;
}

.banner{
    display:flex;
    align-items:center;
    justify-content:flex-start;

    gap:20px;

    background:linear-gradient(
        135deg,
        #5F87A0 0%,
        #5F87A0 80%,
        #7AA0B8 100%
    );

    color:white;
    padding:20px 30px;
    margin-bottom:20px;
}

.school-logo{
    height:120px;
    width:auto;
}

.banner-text{
    text-align:left;
}

.banner h1{
    margin:0;
}

.banner p{
    margin:5px 0 0 0;
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

.card-header{
    background:#3d79b3;
    color:white;
    padding:12px 16px;
    font-size:1.2rem;
    font-weight:normal;
}

.card-content{
    padding:15px;
}

.line-card:nth-child(odd){
    background:#f4f8fb;
    border:1px solid #5F87A0;
}

.line-card:nth-child(even){
    background:#eef4f8;
    border:1px solid #3d79b3;
}

.line-card:nth-child(odd) h3{
    background:#5F87A0;
    color:white;
}

.line-card:nth-child(even) h3{
    background:#3d79b3;
    color:white;
}

body.tv-mode{
    height:100vh;
    overflow:hidden;
    display:flex;
    flex-direction:column;
}

.tv-mode .banner{
    box-sizing:border-box;
    flex:0 0 96px;
    min-height:96px;
    padding:8px 24px;
    margin:0;
}

.tv-mode .school-logo{
    height:76px;
}

.tv-mode .banner h1{
    font-size:2rem;
}

.tv-mode .banner p{
    margin-top:2px;
}

.tv-mode .menu-layout{
    box-sizing:border-box;
    display:grid;
    grid-template-columns:minmax(260px, 300px) minmax(0, 1fr);
    gap:14px;
    flex:1;
    min-height:0;
    padding:14px 18px 18px;
}

.tv-mode .top-cards{
    flex-direction:column;
    flex-wrap:nowrap;
    justify-content:flex-start;
    gap:12px;
    margin:0;
}

.tv-mode .top-card{
    box-sizing:border-box;
    width:100%;
    flex:0 0 auto;
}

.tv-mode .card-content{
    padding:12px 14px;
    font-size:1.45rem;
    line-height:1.35;
}

.tv-mode .card-content p{
    margin:8px 0;
}

.tv-mode .card-header{
    padding:12px 14px;
    font-size:1.55rem;
}

.tv-mode .menu-content{
    display:flex;
    flex-direction:column;
    min-width:0;
    min-height:0;
}

.tv-mode #weekButton{
    display:none;
}

.tv-mode .container{
    flex:1;
    min-height:0;
    margin:0;
}

.tv-mode .container.today-view{
    display:flex;
    align-items:stretch;
    justify-content:stretch;
}

.tv-mode .today-card{
    box-sizing:border-box;
    display:flex;
    flex:1;
    flex-direction:column;
    width:100%;
    max-width:none;
    padding:16px;
    overflow:hidden;
}

.tv-mode .today-card h2{
    margin:0 0 10px;
    font-size:2.2rem;
}

.tv-mode .line-container{
    flex:1;
    grid-template-columns:repeat(auto-fit, minmax(280px, 1fr));
    align-content:stretch;
    gap:8px;
    min-height:0;
}

.tv-mode .line-card{
    display:flex;
    flex-direction:column;
    min-width:0;
    margin:0;
}

.tv-mode .line-card h3{
    padding:10px;
    font-size:1.6rem;
}

.tv-mode .line-card ul{
    display:flex;
    flex:1;
    flex-direction:column;
    justify-content:space-evenly;
    gap:8px;
    padding:10px 10px 10px 30px;
}

.tv-mode li{
    font-size:1.75rem;
    font-weight:700;
    line-height:1.35;
}

.tv-mode .badge{
    padding:4px 9px;
    margin-left:5px;
    font-size:1rem;
}

@media (max-width: 900px){
    .tv-mode{
        height:auto;
        min-height:100vh;
        overflow:auto;
    }

    .tv-mode .menu-layout{
        display:flex;
        flex-direction:column;
        min-height:calc(100vh - 96px);
    }

    .tv-mode .top-cards{
        display:grid;
        grid-template-columns:repeat(2, minmax(0, 1fr));
    }

    .tv-mode .container{
        flex:auto;
    }

    .tv-mode .today-card{
        min-height:70vh;
    }
}

@media (max-height: 680px) and (min-width: 901px){
    .tv-mode .banner{
        flex-basis:76px;
        min-height:76px;
    }

    .tv-mode .school-logo{
        height:60px;
    }

    .tv-mode .menu-layout{
        padding-top:8px;
        padding-bottom:8px;
    }

    .tv-mode .today-card{
        padding:8px;
    }

    .tv-mode .card-content{
        padding:8px 10px;
        font-size:1.2rem;
    }

    .tv-mode .card-header{
        padding:8px 10px;
        font-size:1.3rem;
    }

    .tv-mode .today-card h2{
        margin-bottom:6px;
        font-size:1.8rem;
    }

    .tv-mode .line-card h3,
    .tv-mode .line-card ul{
        padding-top:5px;
        padding-bottom:5px;
    }

    .tv-mode .line-card h3{
        font-size:1.35rem;
    }

    .tv-mode li{
        font-size:1.45rem;
    }

    .tv-mode .badge{
        font-size:.85rem;
    }
}

</style>

</head>
<body>

<div class="banner">

<img
    src="Phoenix_Vector.svg"
    class="school-logo"
    alt="Innovation Academy Logo">

<div class="banner-text">

<h1 id="menuTitle">
Today's Lunch Menu
</h1>

<p>
Innovation Academy High School
</p>

</div>

<button
    id="tvButton"
    class="tv-toggle"
    type="button"
    aria-pressed="false"
    onclick="toggleTV()">
    TV View
</button>

</div>

<div id="menuLayout" class="menu-layout">
<div class="top-cards">

<div class="top-card">

<div class="card-header">
Legend
</div>

<div class="card-content">

<p><span class="badge vegan">Vegan</span> Vegan</p>
<p><span class="badge vegetarian">Veggie</span> Vegetarian</p>
<p><span class="badge gf">GF</span> Gluten Friendly</p>

</div>

</div>

<div class="top-card">

<div class="card-header">
Meal Prices
</div>

<div class="card-content">
"""

        for meal, price in MEAL_PRICES.items():
            html += f"<p>{meal}: {price}</p>"

        html += """
</div>

</div>

</div>

<div class="menu-content">
<button
    id="weekButton"
    class="menu-toggle"
    onclick="toggleWeek()">
    Show Full Week
</button>

<script>
function toggleWeek() {

    const container =
        document.querySelector('.container');    

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

        container.classList.remove('today-view');
        container.classList.add('week-view');
    } else {
        btn.innerText = 'Show Full Week';
        title.innerText = "Today's Lunch Menu";

        container.classList.remove('week-view');
        container.classList.add('today-view');
    }
}

function toggleTV() {
    const enabled =
        document.body.classList.toggle('tv-mode');

    const tvButton =
        document.getElementById('tvButton');

    tvButton.innerText = enabled ? 'Exit TV View' : 'TV View';
    tvButton.setAttribute('aria-pressed', String(enabled));

    if (enabled) {
        const container =
            document.querySelector('.container');

        document.querySelectorAll('.future-day').forEach(card => {
            card.style.display = 'none';
        });

        document.getElementById('weekButton').innerText = 'Show Full Week';
        document.getElementById('menuTitle').innerText = "Today's Lunch Menu";
        container.classList.remove('week-view');
        container.classList.add('today-view');
    }
}
</script>

<div class="container today-view">
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

            parts = day.split()

            day_name = parts[0]
            day_number = int(parts[1])

            current_month = datetime.now().strftime("%b")

            pretty_day = (
                f"{day_name} ({current_month} {day_number})"
            )

            if school_is_out(foods):
                html += f"""
            <div {card_class}>
            <h2>{pretty_day}</h2>

            <div class="line-card">
            <h3>School Closed</h3>
            <ul>
            <li><p> No lunch menu available. Have a nice break!</p></li>
            </ul>
            </div>

            </div>
            """
                continue

            html += f"""
            <div {card_class}>
            <h2>{pretty_day}</h2>
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

            html += '<div class="line-container">'

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
                    html += f"<li>{food} {render_diet_badges(food)}</li>"

                html += """
            </ul>
            </div>
            """
            
            html += '</div>'

            html += """
</div>
"""

        html += """
</div>

 </div>
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Server running at http://localhost:{port}")
    HTTPServer(("0.0.0.0", port), MenuHandler).serve_forever()
