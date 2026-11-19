import io
import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

import backend
from app import render_menu


class ChefSelectionReplacementTests(unittest.TestCase):
    def test_mealviewer_category_matching_ignores_case(self):
        monday = datetime.now() - timedelta(days=datetime.now().weekday())
        response_data = {
            "menuSchedules": [
                {
                    "dateInformation": {
                        "dateFull": monday.strftime("%Y-%m-%dT00:00:00")
                    },
                    "menuBlocks": [
                        {
                            "blockName": "Lunch",
                            "cafeteriaLineList": {
                                "data": [
                                    {
                                        "foodItemList": {
                                            "data": [
                                                {
                                                    "item_Order_Id": 1,
                                                    "item_Name": "Bacon Cheeseburger",
                                                    "item_Type": "Chef selection Hot sandwich",
                                                    "mvS_Visible": True,
                                                }
                                            ]
                                        }
                                    }
                                ]
                            },
                        }
                    ],
                }
            ]
        }

        with patch(
            "backend.urlopen",
            return_value=io.BytesIO(json.dumps(response_data).encode()),
        ):
            menu = backend.get_mealviewer_week_menu()

        day = f"{monday.strftime('%A')} {monday.day}"
        self.assertEqual(
            menu[day]["chef_selections"]["Chef Selection Hot Sandwich"],
            ["Bacon Cheeseburger"],
        )

    def test_fulton_chef_selection_labels_are_replaced_by_mealviewer_foods(self):
        merged = backend.merge_week_menus(
            {
                "Thursday 19": [
                    "Chef Selection Southern Breaded Thigh w/ Whole Grain Breadstick",
                    "Chef Selection Hot Sandwich",
                ]
            },
            {
                "Thursday 19": {
                    "foods": [
                        "Lemon Pepper Breaded Chicken Thigh w/ Whole Grain Breadstick",
                        "Bacon Cheeseburger",
                    ],
                    "snacks": [],
                    "chef_selections": {},
                }
            },
        )

        self.assertEqual(
            merged["Thursday 19"]["foods"],
            [
                "Lemon Pepper Breaded Chicken Thigh w/ Whole Grain Breadstick",
                "Bacon Cheeseburger",
            ],
        )

    def test_unmatched_fulton_chef_selection_is_kept_as_fallback(self):
        merged = backend.merge_week_menus(
            {"Thursday 19": ["Chef Selection Southern Breaded Thigh"]},
            {
                "Thursday 19": {
                    "foods": ["Meat Lovers Pizza"],
                    "snacks": [],
                    "chef_selections": {},
                }
            },
        )

        self.assertIn(
            "Chef Selection Southern Breaded Thigh",
            merged["Thursday 19"]["foods"],
        )


class MeatTagTests(unittest.TestCase):
    def test_bacon_cheeseburger_gets_beef_and_pork_tags(self):
        self.assertEqual(
            backend.get_item_meat_tags(
                {
                    "item_Name": "Bacon Cheeseburger",
                    "item_Type": "Entree",
                    "vegetarian": False,
                }
            ),
            ["Beef", "Pork"],
        )

    def test_website_marked_vegetarian_burger_does_not_get_meat_tags(self):
        self.assertEqual(
            backend.get_item_meat_tags(
                {
                    "item_Name": "Black Bean Burger",
                    "item_Type": "Entree",
                    "vegetarian": True,
                }
            ),
            [],
        )
        self.assertEqual(
            backend.get_item_meat_tags(
                {"item_Name": "Veggie Burger (V)", "item_Type": "Entree"}
            ),
            [],
        )


class SaladBarInfoTests(unittest.TestCase):
    def test_salad_bar_info_popup_explains_customization(self):
        rendered = render_menu(
            {"Thursday 19": {"foods": ["Rice", "Corn"]}}
        )

        self.assertIn(
            'aria-label="Show information about Salad Bar"',
            rendered,
        )
        self.assertIn(
            "Salad bar nutrition and allergen values vary depending on each "
            "student&#x27;s selections and customizations.",
            rendered,
        )


if __name__ == "__main__":
    unittest.main()
