######################################################################
#The imports
#######################################################################
import streamlit as st
from st_copy import copy_button
from modules.db import get_connection
from modules.meal_logic import generate_week, reroll_day
from modules.shopping import generate_shopping_list, format_quantity
from modules.utils import clear_all
from modules.constants import DAYS


######################################################################
#The cache
#######################################################################
@st.cache_data
def get_all_meal_names():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT name FROM meals ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    # ensure uniqueness at Python level too
    return sorted({r[0] for r in rows})



######################################################################
#The UI
#######################################################################

st.title("Weekly meal planner") #title

st.markdown("---") #page divider line

#Clear_all button
if st.button("Clear All"):
    clear_all()

st.markdown("---")

# Ensure filters dict always exists
if "filters" not in st.session_state:
    st.session_state["filters"] = {day: [] for day in DAYS}

# Ensure people dict always exists
if "people" not in st.session_state:
    st.session_state["people"] = {day: 2 for day in DAYS}

# Ensure week_plan always exists
if "week_plan" not in st.session_state:
    st.session_state["week_plan"] = {day: None for day in DAYS}

# Ensure veggie flags always exist
if "meal_is_veggie" not in st.session_state:
    st.session_state["meal_is_veggie"] = {day: False for day in DAYS}

# Ensure vegan flags always exist
if "meal_is_vegan" not in st.session_state:
    st.session_state["meal_is_vegan"] = {day: False for day in DAYS}



# Filters + people per day
for day in DAYS:
    col1, col2, col3 = st.columns([1, 2, 2]) #this defines 3 columns with width 1,2,2

    with col1: #in column 1
        st.markdown( #this is HTML code to format the day text
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
        selected = st.multiselect( #a multiselect filter to allow user to pick veggie, etc.
            "",
            ["Veggie", "Vegan", "Quick", "Skip"],
            key=f"{day}_filters",
            label_visibility="collapsed"
        )   

        st.session_state["filters"][day] = selected


    with col3:
        st.session_state["people"][day] = st.number_input( #a number input to show allow the user to pick how many people are eating from 1-10
            f"People eating on {day}",
            min_value=1,
            max_value=10,
            value=st.session_state["people"][day],
            key=f"{day}_people"
        )

st.markdown("---")

# Generate week - button to generate a full week plan
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
