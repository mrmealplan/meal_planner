import streamlit as st
import requests

def get_supabase_config():
    return (
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_ANON_KEY"]
    )

def _auth_request(endpoint, payload):
    SUPABASE_URL, SUPABASE_KEY = get_supabase_config()

    url = f"{SUPABASE_URL}/auth/v1/{endpoint}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json",
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

def signup(email, password):
    return _auth_request("signup", {"email": email, "password": password})

def login(email, password):
    return _auth_request("token?grant_type=password", {
        "email": email,
        "password": password
    })
