import streamlit as st
import requests

#Find supabase config from secrets in streamlit
def get_supabase_config():
    return (
        st.secrets["supabase"]["url"],
        st.secrets["supabase"]["anon_key"]
    )

#Need to learn what this does
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

