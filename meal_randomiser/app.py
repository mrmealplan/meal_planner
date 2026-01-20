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

#GET RANDOM MEAL
def get_random_meal(filters):
    conn = get_connection()
    cur = conn.cursor

    query = "Select id, name, category FROM meals"
    conditions = []
    params = []

    #multi-filter logic
    if "Veggie" in filters:
        conditions.append("is_veggie = TRUE")
    if "Vegan" in filters:
        conditions.append("is_vegan = TRUE")
    if "Quick" in filters:
        conditions.append("is_quick = TRUE")

    #Avoid duplucate meals
    if st.session_state["used_meals"]:
        placeholders = ",".join(["%s"]*len(st.session_state["used_meals"]))
        conditions.append(f"id NOT IN ({placeholders})")
        params.extend(list(st.session_state["used_meals"]))

    #Avoid duplicate categories (meal types)
    if st.session_state["used_categories"]:
        placeholders = ",".join(["%s"]*len(st.session_state["used_categories"]))
        conditions.append(f"category NOT IN ({placeholders})")
        params.extend(list(st.session_state["used_categories"]))

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY RANDOM () LIMIT 1"

    st.write("QUERY": query)
    st.write("PARAMS:", params)

    cur.execute(query, params)
    meal = cur.fetchone()
    conn.close()

    return meal # may be NONE

#GENERATE WEEK
def generate_week():
    ordered_days=sorted(
        DAYS,
        key=lambda d: filter_priority(st.session_state["filters"][d])
    )

    for day in ordered_days:
        filters = st.session_state["filters"][day]
        meal = get_random_meal(filters)

        if meal is None:
            st.warning(f"No meals match the criteria for {day}.")
            st.session_state["week_plan"][day] = None
            continue

        meal_id, meal_name, category = meal

        st.session_state["week_plan"][day] = meal_name
        st.session_state["used_meals"].add(meal_id)
        st.session_state["used_categories"].add(category)
    

#RE ROLL DAY
def reroll_day(day):
    filters = st.session_state["filters"][day]
    meal = get_random_meal(filters)

    if meal is None:
        st.warning(f"No meals match the criteria for {day}.")
        return
    
    meal_id, mea_name, category = meal
    
    st.session_state["week_plan"][day] = meal_name
    st.session_state["used_meals"].add(meal_id)
    st.session_state["used_categories"].add(category)

#CLEAR WEEK
def clear_week():
    st.session_state["week_plan"] = {day: None for day in DAYS}
    st.session_state["used_meals"] = set()
    st.session_state["used_categories"] = set()


#UI code (streamlit layout)
st.title("Weekly meal planner")

for day in DAYS:
    st.subheader(day)

    st.session_state["filters"][day] = st.multiselect(
        "Filters",
        ["Veggie", "Vegan", "Quick"],
        default  = st.session_state["filters"][day],
        key=f"{day}_filters"
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Suggest", key=f"{day}_suggest"):
            reroll_day(day)

    with col2:
        if st.button("Re-roll", key=f"{day}_reroll"):
            reroll_day(day)

    meal = st.session_state["week_plan"][day]
    if meal:
        st.success(meal)
    else:
        st.info("No meal selected yet.")

st.markdown("---")

if st.button("Generate full week"):
    clear_week()
    generate_week()

if st.button("Clear Week"):
    clear_week()