import streamlit as st
import psycopg2

def get_connection():
    db = st.secrets["database"]
    return psycopg2.connect(
        host=db["host"], 
        port=db["port"], 
        dbname=db["dbname"], 
        ser=db["user"], 
        password=db["password"], 
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

