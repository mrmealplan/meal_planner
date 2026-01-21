import streamlit as st
import psycopg2
from st_copy import copy_button

# ---------------------------------------------------------
# DB CONNECTION
# ---------------------------------------------------------
@st.cache_resource
def get_connection_factory():
    db = st.secrets["database"]

    def connect():
        return psycopg2.connect(
            host=db["host"],
            port=db["port"],
            dbname=db["dbname"],
            user=db["user"],
            password=db["password"],
            sslmode="require"
        )

    return connect


def get_connection():
    connect = get_connection_factory()
    conn = connect()

    # Test connection
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1;")
    except Exception:
        conn = connect()

    return conn



# ---------------------------------------------------------
# CONSTANTS & SESSION STATE
# ---------------------------------------------------------
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

SESSION_DEFAULTS = {
    "week_plan": {day: None for day in DAYS},
    "used_meals": set(),
    "used_categories": set(),
    "filters": {day: [] for day in DAYS},
    "meal_is_veggie": {day: False for day in DAYS},
    "meal_is_vegan": {day: False for day in DAYS},
    "people": {day: 2 for day in DAYS},
}

for key, default in SESSION_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
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


def reroll_day(day):
    filters = st.session_state["filters"][day]
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


def clear_all():
    # Core state
    st.session_state["week_plan"] = {day: None for day in DAYS}
    st.session_state["used_meals"] = set()
    st.session_state["used_categories"] = set()
    st.session_state["filters"] = {day: [] for day in DAYS}
    st.session_state["meal_is_veggie"] = {day: False for day in DAYS}
    st.session_state["meal_is_vegan"] = {day: False for day in DAYS}
    st.session_state["people"] = {day: 2 for day in DAYS}

    # WIDGET STATE: delete keys so Streamlit fully resets them
    for day in DAYS:
        filter_key = f"{day}_filters"
        override_key = f"{day}_override"

        if filter_key in st.session_state:
            del st.session_state[filter_key]

        if override_key in st.session_state:
            del st.session_state[override_key]



@st.cache_data
def get_all_meal_names():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT name FROM meals ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    # ensure uniqueness at Python level too
    return sorted({r[0] for r in rows})



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


def format_quantity(qty):
    if qty is None:
        return None
    if float(qty).is_integer():
        return int(qty)
    return round(qty, 2)

# ---------------------------------------------------------
# UI
# ---------------------------------------------------------
st.title("Weekly meal planner")

st.markdown("---")

#Clear_all button
if st.button("Clear All"):
    clear_all()

st.markdown("---")

# Filters + people per day
for day in DAYS:
    col1, col2, col3 = st.columns([1, 4, 1])

    with col1:
        st.markdown(
            f"""
            <div style="
            display:flex; 
            align-items:center; 
            height:38px;
            font-weight:bold;
            ">
                {day}
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        selected = st.multiselect(
            "",
            ["Veggie", "Vegan", "Quick", "Skip"],
            key=f"{day}_filters",
            label_visibility="collapsed"
        )   

        st.session_state["filters"][day] = selected


    with col3:
        st.session_state["people"][day] = st.number_input(
            f"People eating on {day}",
            min_value=1,
            max_value=10,
            value=st.session_state["people"][day],
            key=f"{day}_people"
        )

st.markdown("---")

# Generate week
if st.button("Generate full week"):
    clear_all()
    generate_week()

st.markdown("---")

# Day-by-day reroll + override
all_meals = get_all_meal_names()

for day in DAYS:
    col1, col2 = st.columns([2, 4])

    with col1:
        if st.button(f"Re-roll {day}", key=f"{day}_reroll"):
            reroll_day(day)

    with col2:
        current_meal = st.session_state["week_plan"][day]

        override = st.selectbox(
            f"{day} meal",
            options=["(keep suggestion)"] + all_meals,
            key=f"{day}_override"
        )

        if override != "(keep suggestion)":
            st.session_state["week_plan"][day] = override

            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT is_veggie, is_vegan
                FROM meals
                WHERE name = %s
            """, (override,))
            flags = cur.fetchone()
            conn.close()

            if flags:
                st.session_state["meal_is_veggie"][day] = flags[0]
                st.session_state["meal_is_vegan"][day] = flags[1]

        final_meal = st.session_state["week_plan"][day]
        if final_meal:
            suffix = " (ve)" if st.session_state["meal_is_vegan"][day] else \
                     " (v)" if st.session_state["meal_is_veggie"][day] else ""
            st.success(f"{day}: {final_meal}{suffix}")
        else:
            st.info("No meal selected.")

st.markdown("---")

# Shopping list
if st.button("Create shopping list"):
    shopping_list = generate_shopping_list()

    if shopping_list:
        st.header("Shopping List")

        # Build copyable text first
        checklist_lines = []
        for area, ingredient, qty, unit in shopping_list:
            if qty is None:
                checklist_lines.append(f"{ingredient}")
            else:
                display_qty = format_quantity(qty)
                checklist_lines.append(f"{ingredient}: {display_qty} {unit or ''}")

        full_text = "\n".join(checklist_lines)

        # --- COPY BUTTON ABOVE THE LIST ---
        label_col, button_col = st.columns([4, 1])
        with label_col:
            st.markdown("### Copy your shopping list")
        with button_col:
            copy_button(
                full_text,
                tooltip="Copy shopping list",
                copied_label="Copied!",
                icon="st"
            )

        # --- NOW DISPLAY THE LIST ---
        current_area = None
        for area, ingredient, qty, unit in shopping_list:
            if area != current_area:
                st.subheader(f"**{area}**")
                current_area = area

            if qty is None:
                st.write(f"- {ingredient}")
            else:
                display_qty = format_quantity(qty)
                st.write(f"- {ingredient}: {display_qty} {unit or ''}")


st.markdown("---")
