import os
import streamlit as st


def _get_expected_password() -> str | None:
    # Streamlit Cloud Secrets TOML:
    # [auth]
    # SHARED_PASSWORD = "..."
    try:
        if "auth" in st.secrets and "SHARED_PASSWORD" in st.secrets["auth"]:
            return str(st.secrets["auth"]["SHARED_PASSWORD"])
    except Exception:
        pass

    # Fallback env var
    return os.getenv("TOOLBOX_SHARED_PASSWORD")


def require_shared_password() -> None:
    # One login per browser session
    if st.session_state.get("auth_ok") is True:
        return

    expected = _get_expected_password()
    if not expected:
        st.error(
            "Authentication is not configured.\n\n"
            "Set one of:\n"
            "- Streamlit Secrets: [auth].SHARED_PASSWORD\n"
            "- Environment variable: TOOLBOX_SHARED_PASSWORD"
        )
        st.stop()

    st.title("HayCash ToolBox")
    st.write("Enter the shared password to continue.")

    pw = st.text_input("Password", type="password")

    if st.button("Login"):
        if pw == expected:
            st.session_state["auth_ok"] = True
            st.rerun()
        st.error("Incorrect password.")
        st.stop()

    st.stop()
