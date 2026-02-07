import psycopg2
import streamlit as st

#######################################################################
# DB CONNECTION to connect to Neon - need to understand more about this
#######################################################################

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

@st.cache_data
def get_meal_lookup():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, is_veggie, is_vegan
        FROM meals
    """)
    rows = cur.fetchall()
    conn.close()

    return {mid: (name, veg, vegan) for mid, name, veg, vegan in rows}

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


