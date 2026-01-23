import streamlit as st
from modules.db import get_connection

#Generate a shopping list based on the meals selected for the week
def generate_shopping_list():
    selected = [
        (day, name, st.session_state["people"][day])
        for day, name in st.session_state["week_plan"].items()
        if name is not None
    ]

    if not selected:
        st.warning("No meals selected for the week.")
        return None

    days, meal_names, people_counts = zip(*selected)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, default_servings
        FROM meals
        WHERE name = ANY(%s)
    """, (list(meal_names),))

    meal_rows = cur.fetchall()
    meal_info = {name: (mid, servings) for mid, name, servings in meal_rows}

    ingredient_rows = []
    for i, name in enumerate(meal_names):
        meal_id, default_servings = meal_info[name]
        people = people_counts[i]

        cur.execute("""
            SELECT 
                ri.name,
                sa.name AS area,
                i.quantity * %s::float / %s::float AS scaled_qty,
                i.unit
            FROM ingredients i
            JOIN raw_ingredients ri ON i.raw_ingredient_id = ri.id
            LEFT JOIN supermarket_areas sa ON ri.area_id = sa.id
            WHERE i.meal_id = %s
        """, (people, default_servings, meal_id))

        ingredient_rows.extend(cur.fetchall())

    conn.close()

    shopping = {}

    for ingredient, area, qty, unit in ingredient_rows:
        area = area or "Other"
        key = (area, ingredient, unit)

        if qty is None:
            shopping[key] = {"qty": None}
        else:
            if key not in shopping or shopping[key]["qty"] is None:
                shopping[key] = {"qty": qty}
            else:
                shopping[key]["qty"] += qty

    result = sorted(
        [(area, ingredient, data["qty"], unit) for (area, ingredient, unit), data in shopping.items()],
        key=lambda x: (x[0], x[1])
    )

    return result

# Formats the quantity so we don't get things like 2.0 tins of beans
def format_quantity(qty):
    if qty is None:
        return None
    if float(qty).is_integer():
        return int(qty)
    return round(qty, 2)
