import streamlit as st
import requests

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_ANON_KEY"]

def _auth_request(endpoint, payload):
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
