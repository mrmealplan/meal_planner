import streamlit as st
from auth import signup, login

def auth_ui():
    st.title("Login / Sign Up")

    mode = st.radio("Choose", ["Login", "Sign Up"], horizontal=True)
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if mode == "Sign Up":
        if st.button("Create Account"):
            res = signup(email, password)
            if "user" in res:
                st.success("Account created! Check your email.")
            else:
                st.error(res.get("msg", "Sign-up failed"))

    if mode == "Login":
        if st.button("Login"):
            res = login(email, password)
            if "access_token" in res:
                st.session_state.session = res
                st.rerun()
            else:
                st.error("Invalid login")
