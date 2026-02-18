import os
import hmac
import streamlit as st


def _get_user_table() -> tuple[dict, dict]:
    # Streamlit Cloud Secrets TOML:
    # [auth.users]
    # Carlos = "..."
    # Juan   = "..."
    # Daniel = "..."
    #
    # [auth.roles]
    # Carlos = "admin"
    # Juan   = "user"
    # Daniel = "user"
    try:
        auth = st.secrets.get("auth", {})
        users = auth.get("users", {}) or {}
        roles = auth.get("roles", {}) or {}
        return dict(users), dict(roles)
    except Exception:
        pass

    # Fallback env var (optional):
    # TOOLBOX_USERS = 'Carlos=pass1;Juan=pass2;Daniel=pass3'
    # TOOLBOX_ROLES = 'Carlos=admin;Juan=user;Daniel=user'
    users_env = os.getenv("TOOLBOX_USERS", "")
    roles_env = os.getenv("TOOLBOX_ROLES", "")

    users: dict[str, str] = {}
    roles: dict[str, str] = {}

    if users_env:
        for pair in users_env.split(";"):
            if not pair.strip():
                continue
            if "=" not in pair:
                continue
            k, v = pair.split("=", 1)
            users[k.strip()] = v.strip()

    if roles_env:
        for pair in roles_env.split(";"):
            if not pair.strip():
                continue
            if "=" not in pair:
                continue
            k, v = pair.split("=", 1)
            roles[k.strip()] = v.strip()

    return users, roles


def require_shared_password() -> None:
    # Backwards-compatible name: app.py doesn't need changes
    if st.session_state.get("auth_ok") is True:
        return

    users, roles = _get_user_table()

    if not users:
        st.error(
            "Authentication is not configured.\n\n"
            "Set one of:\n"
            "- Streamlit Secrets: [auth.users] (and optionally [auth.roles])\n"
            "- Environment variables: TOOLBOX_USERS (and optionally TOOLBOX_ROLES)"
        )
        st.stop()

    st.title("HayCash ToolBox")
    st.write("Enter your username and password to continue.")

    username = st.text_input("Username")
    pw = st.text_input("Password", type="password")

    if st.button("Login"):
        stored = users.get(username, "")
        ok_user = bool(stored) and bool(pw)
        ok_pass = ok_user and hmac.compare_digest(str(stored), str(pw))

        if ok_pass:
            st.session_state["auth_ok"] = True
            st.session_state["auth_user"] = username
            st.session_state["auth_role"] = roles.get(username, "user")
            st.rerun()

        st.error("Incorrect username or password.")
        st.stop()

    st.stop()
