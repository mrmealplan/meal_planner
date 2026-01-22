import streamlit as st
from modules.constants import DAYS


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




def clear_all():
    # Reset logical state
    st.session_state["week_plan"] = {day: None for day in DAYS}
    st.session_state["used_meals"] = set()
    st.session_state["used_categories"] = set()
    st.session_state["filters"] = {day: [] for day in DAYS}
    st.session_state["meal_is_veggie"] = {day: False for day in DAYS}
    st.session_state["meal_is_vegan"] = {day: False for day in DAYS}
    st.session_state["people"] = {day: 2 for day in DAYS}

    # Remove widget keys so Streamlit recreates them with defaults
    for day in DAYS:
        st.session_state[f"{day}_filters"] = []
        st.session_state[f"{day}_override"] = False
        st.session_state[f"{day}_people"] = 2


def reset_for_generation():
    # Reset only the state needed for generating a new week
    st.session_state["week_plan"] = {day: None for day in DAYS}
    st.session_state["used_meals"] = set()
    st.session_state["used_categories"] = set()
    st.session_state["meal_is_veggie"] = {day: False for day in DAYS}
    st.session_state["meal_is_vegan"] = {day: False for day in DAYS}

    # Do NOT touch filters
    # Do NOT touch people
    # Do NOT delete filter widget keys
    # Do NOT delete override widget keys


