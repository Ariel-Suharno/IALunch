# Official Websites Used

- **Overall Fulton County menu:** https://nutrition.fultonschools.org/MenuCalendar
- **MealViewer menu (Source of allergen, dietary, and snack data):** https://schools.mealviewer.com/school/InnovationAcademyHigh
- **Special diet requests:** https://nutrition.fultonschools.org/SpecialDiets

# IALunch

IALunch displays the Innovation Academy High School lunch menu and related meal information.

Website: https://innovation-menu.onrender.com/

## Features

- Shows today's menu by default, with an option to view the full week.
- Combines the Fulton County menu with MealViewer data, including available allergen and dietary information.
- Groups food items by cafeteria line and organizes snacks into snacks, drinks, and ice cream.
- Shows allergen and dietary labels on menu items, plus a legend of the tags available for the week.
- Lets users filter menu items by hiding foods that contain selected allergens.
- Shows student, reduced, adult, and extra-milk prices.
- Identifies school-closure days. When Fulton provides a closure note, it appears beneath the closed-school message.
- Displays an allergen-data notice when that information is unavailable for a menu day.
- Provides a link to Fulton County's special diet form. Medical allergy accommodations require an official doctor's form; the form is not for religious or personal dietary preferences.

## Running Locally

Python 3 is required. Install the web server dependency and start the app:

```bash
pip install -r requirements.txt
python app.py
```

By default, the app listens on port `8000`. Set the `PORT` environment variable to use another port.
