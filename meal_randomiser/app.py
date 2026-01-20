import streamlit as st
import psycopg2
import socket

st.write("DEBUG VERSION: v8")

def get_connection():
    db = st.secrets["database"]

    # Force IPv4
    orig_getaddrinfo = socket.getaddrinfo
    def ipv4_only(*args, **kwargs):
        return [ai for ai in orig_getaddrinfo(*args, **kwargs) if ai[0] == socket.AF_INET]
    socket.getaddrinfo = ipv4_only

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
    finally:
        socket.getaddrinfo = orig_getaddrinfo



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

