import streamlit as st
import psycopg2

def get_connection():
    return psycopg2.connect(
        host="db.chshyaiulzcyfdhpuqax.supabase.co",
        port=5432,
        dbname="postgres",
        user="postgres",
        password="S7aamiDx8Wz5AjrD",
        sslmode="require"
    )

def get_all_meals():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, category FROM meals;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

st.title("Meal Planner POC")

st.write("Meals in the database:")

meals = get_all_meals()
for name, category in meals:
    st.write(f"- {name} ({category})")
