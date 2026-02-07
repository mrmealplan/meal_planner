import streamlit as st
from modules.db import get_connection
from modules.constants import DAYS

#arranges priority order for selecting meals - vegan+quick is first as there are less meals for this,etc.
def filter_priority(filters): 
    if "Vegan" in filters and "Quick" in filters:
        return 1
    if "Vegan" in filters:
        return 2
    if "Veggie" in filters and "Quick" in filters:
        return 3
    if "Veggie" in filters:
        return 4
    if "Quick" in filters:
        return 5
    return 6

#gets a random meal from the database based on the filters selected
def get_random_meal(filters): 
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT 
            m.id, 
            m.name, 
            c.name AS category, 
            m.is_veggie, 
            m.is_vegan
        FROM meals m
        JOIN categories c ON m.category_id = c.id
    """

    conditions = []
    params = []

    if "Veggie" in filters:
        conditions.append("m.is_veggie = TRUE")
    if "Vegan" in filters:
        conditions.append("m.is_vegan = TRUE")
    if "Quick" in filters:
        conditions.append("m.is_quick = TRUE")

    if st.session_state["used_meals"]:
        placeholders = ",".join(["%s"] * len(st.session_state["used_meals"]))
        conditions.append(f"m.id NOT IN ({placeholders})")
        params.extend(list(st.session_state["used_meals"]))

    if st.session_state["used_categories"]:
        placeholders = ",".join(["%s"] * len(st.session_state["used_categories"]))
        conditions.append(f"c.name NOT IN ({placeholders})")
        params.extend(list(st.session_state["used_categories"]))

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY RANDOM() LIMIT 1"

    cur.execute(query, params)
    meal = cur.fetchone()
    conn.close()

    return meal

#picks a random meal for each day
def generate_week(): 
    ordered_days = sorted(
        DAYS,
        key=lambda d: filter_priority(st.session_state["filters"][d])
    )

    for day in ordered_days:
        filters = st.session_state["filters"][day]

        if "Skip" in filters:
            st.session_state["week_plan"][day] = None
            continue

        meal = get_random_meal(filters)

        if meal is None:
            st.warning(f"No meals match the criteria for {day}.")
            st.session_state["week_plan"][day] = None
            continue

        meal_id, meal_name, category, is_veggie, is_vegan = meal

        st.session_state["week_plan"][day] = meal_name
        st.session_state["used_meals"].add(meal_id)
        st.session_state["used_categories"].add(category)
        st.session_state["meal_is_veggie"][day] = is_veggie
        st.session_state["meal_is_vegan"][day] = is_vegan

#re-rolls a single day
def reroll_day(day):
    old_meal_name = st.session_state["week_plan"][day]

    if old_meal_name:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT m.id, c.name
            FROM meals m
            JOIN categories c ON m.category_id = c.id
            WHERE m.name = %s
        """, (old_meal_name,))
        result = cur.fetchone()
        conn.close()

        if result:
            old_meal_id, old_category = result
            st.session_state["used_meals"].discard(old_meal_id)
            st.session_state["used_categories"].discard(old_category)

    filters = st.session_state["filters"][day]

    # 🔹 NEW: honour "Skip" on reroll too
    if "Skip" in filters:
        st.session_state["week_plan"][day] = None
        return

    meal = get_random_meal(filters)

    if meal is None:
        st.warning(f"No meals match the criteria for {day}.")
        return

    meal_id, meal_name, category, is_veggie, is_vegan = meal

    st.session_state["week_plan"][day] = meal_name
    st.session_state["used_meals"].add(meal_id)
    st.session_state["used_categories"].add(category)
    st.session_state["meal_is_veggie"][day] = is_veggie
    st.session_state["meal_is_vegan"][day] = is_vegan
