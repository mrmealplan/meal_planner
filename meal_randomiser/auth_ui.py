import streamlit as st
from auth import signup, login

def auth_ui():
    st.title("Login / Sign Up")

    mode = st.radio("Choose", ["Login", "Sign Up"], horizontal=True)

    ####################
    # SIGN UP MODE - learn what this actually does
    ####################
    if mode == "Sign Up":
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_password")

        if st.button("Create Account", key="signup_button"):
            res = signup(email, password)

            if "user" in res or res.get("id"):
                st.success("Account created!")
            else:
                st.error(
                    res.get("error_description")
                    or res.get("message")
                    or res.get("error")
                    or "Sign-up failed"
                )

    ####################
    # LOGIN MODE - learn what this actually does
    ####################
    if mode == "Login":
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")

        debug = st.checkbox("Show Supabase debug info", key="login_debug")

        if st.button("Login", key="login_button"):
            res = login(email, password)

            if "access_token" in res:
                st.session_state.session = res
                st.rerun()
            else:
                st.error("Invalid login")

                if debug:
                    st.write("Supabase response:", res)
