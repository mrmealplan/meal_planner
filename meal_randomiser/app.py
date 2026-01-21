import streamlit as st
import psycopg2

#GET CONNECTION
def get_connection():
    db = st.secrets["database"]
    try:
        return psycopg2.connect(
            host=db["host"],
            port=db["port"],
            dbname=db["dbname"],
            user=db["user"],
            password=db["password"],
            sslmode="require"
        )
    except Exception as e:
        st.error(f"RAW CONNECTION ERROR: {e}")
        raise

####################################################################
#SESSION STATE SETUP
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

if "week_plan" not in st.session_state:
    st.session_state["week_plan"] = {day: None for day in DAYS}

if "used_meals" not in st.session_state:
    st.session_state["used_meals"] = set()

if "used_categories" not in st.session_state:
    st.session_state["used_categories"] = set()

if "filters" not in st.session_state:
    st.session_state["filters"] = {day: [] for day in DAYS}

if "meal_categories" not in st.session_state:
    st.session_state["meal_categories"] = {day: "" for day in DAYS}

if "meal_is_veggie" not in st.session_state:
    st.session_state["meal_is_veggie"] = {day: False for day in DAYS} 
    
if "meal_is_vegan" not in st.session_state:
    st.session_state["meal_is_vegan"] = {day: False for day in DAYS}

if "people" not in st.session_state:
    st.session_state["people"] = {day: 2 for day in DAYS}  # default 2 people


#########################################################################
#FILTER PRIORITY
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

    # Multi-filter logic
    if "Veggie" in filters:
        conditions.append("m.is_veggie = TRUE")
    if "Vegan" in filters:
        conditions.append("m.is_vegan = TRUE")
    if "Quick" in filters:
        conditions.append("m.is_quick = TRUE")

    # Avoid duplicate meals
    if st.session_state["used_meals"]:
        placeholders = ",".join(["%s"] * len(st.session_state["used_meals"]))
        conditions.append(f"m.id NOT IN ({placeholders})")
        params.extend(list(st.session_state["used_meals"]))

    # Avoid duplicate categories
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


#GENERATE WEEK
def generate_week():
          
    ordered_days=sorted(
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
    

#RE ROLL DAY
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

#CLEAR WEEK
def clear_week():
    st.session_state["week_plan"] = {day: None for day in DAYS}
    st.session_state["used_meals"] = set()
    st.session_state["used_categories"] = set()

def generate_shopping_list():
    # Collect selected meals + people counts
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

    # Get meal IDs + default servings
    cur.execute("""
        SELECT id, name, default_servings
        FROM meals
        WHERE name = ANY(%s)
    """, (meal_names,))
    meal_rows = cur.fetchall()

    meal_info = {name: (mid, servings) for mid, name, servings in meal_rows}

    # Build list of (meal_id, people_eating)
    meal_people_pairs = [
        (meal_info[name][0], people_counts[i], meal_info[name][1])
        for i, name in enumerate(meal_names)
    ]

    # Build dynamic SQL for scaling
    ingredient_rows = []
    for meal_id, people, default_servings in meal_people_pairs:
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

    # Aggregate identical ingredients + units
    shopping = {}
    for ingredient, area, qty, unit in ingredient_rows:
        key = (area or "Other", ingredient, unit)
        shopping[key] = shopping.get(key, 0) + (qty or 0)

    # Convert dict to sorted list
    result = sorted(
        [(area, ingredient, qty, unit) for (area, ingredient, unit), qty in shopping.items()],
        key=lambda x: (x[0], x[1])
    )

    return result

    






######################################################################################

#UI code (streamlit layout)
st.title("Weekly meal planner")

for day in DAYS:
    col1, col2, col3 = st.columns([1,4,1])
    
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
        st.session_state["filters"][day] = st.multiselect(
            "",
            ["Veggie", "Vegan", "Quick", "Skip"],
            default  = st.session_state["filters"][day],
            key=f"{day}_filters",
            label_visibility="collapsed"
        )    

    with col3:
        st.session_state["people"][day] = st.number_input(
        f"People eating on {day}",
        min_value=1,
        max_value=10,
        value=st.session_state["people"][day],
        key=f"{day}_people"
    )

st.markdown("---")

if st.button("Generate full week"):
    clear_week()
    generate_week()

st.markdown("---")

col1, col2 = st.columns([1,1])

with col1:
    if st.button("Clear Week"):
        clear_week()

with col2:
    if st.button("Re-roll full week"):
        clear_week()
        generate_week()

st.markdown("---")


suffix_map = { "Veggie": " (v)", "Vegan": " (ve)" }

for day in DAYS:
    col1, col2 = st.columns([2,4])
    
    with col1:
        if st.button(f"Re-roll {day}", key=f"{day}_reroll"):
            reroll_day(day)

    with col2:
        meal = st.session_state["week_plan"][day]
        is_veggie = st.session_state["meal_is_veggie"].get(day, False)
        is_vegan = st.session_state["meal_is_vegan"].get(day, False)
        suffix = " (ve)" if is_vegan else " (v)" if is_veggie else ""

        if meal:
            st.success(f"{day}: {meal}{suffix}")
        else:
            st.info("No meal selected.")

st.markdown("---")

if st.button("Create shopping list"):
    shopping_list = generate_shopping_list()

    if shopping_list:
        st.header("Shopping List")

        current_area = None
        for area, ingredient, qty, unit in shopping_list:
            if area != current_area:
                st.subheader(f"**{area}**")
                current_area = area

            if qty is None:
                st.write(f"- {ingredient}")
            else:
                st.write(f"- {ingredient}: {qty} {unit or ''}")

st.markdown("---")
