import os
import shutil
import subprocess
from pathlib import Path
from datetime import date

import pandas as pd
import streamlit as st

from leads_logic import (
    ReviewStore,
    SnapshotSource,
    load_blocked_rfcs,
    build_snapshot_view,
    enrich,
    apply_filters,
    kpis,
    DEFAULT_REVIEWED_CSV,
    DEFAULT_SNAPSHOT_CSV,
    ALLOWED_STATUSES,
)

APP_TITLE = "Análisis Leads"
APP_ICON = "📊"


# -----------------------------
# Auth (keeps shinymanager sqlite behavior when R is available)
# -----------------------------
def _rscript_path() -> str | None:
    return shutil.which("Rscript")


def _verify_with_r(user: str, password: str) -> bool:
    """
    Uses the original shinymanager sqlite auth if Rscript is available.

    Env:
      - SM_PASSPHRASE: passphrase (defaults to Shiny's fallback)
    Uses: data/auth.sqlite (relative to app root)
    """
    r = _rscript_path()
    if not r:
        return False

    script = Path(__file__).with_name("verify_credentials.R")
    # run in app root so relative paths match
    proc = subprocess.run(
        [r, str(script), user, password],
        cwd=str(Path(__file__).parent),
        capture_output=True,
        text=True,
        timeout=12,
    )
    return proc.returncode == 0


def require_login():
    # If R is missing, allow bypass (otherwise you'd be locked out).
    # Set REQUIRE_R_AUTH=1 to force R auth and fail hard if not available.
    require_r = os.getenv("REQUIRE_R_AUTH", "0") == "1"
    r_ok = _rscript_path() is not None

    if require_r and not r_ok:
        st.error("Rscript no está disponible en PATH. Instala R o agrega Rscript al PATH.")
        st.stop()

    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False
        st.session_state.auth_user = None

    if st.session_state.auth_ok:
        return

    with st.container(border=True):
        st.subheader("Login")
        user = st.text_input("Usuario", key="login_user")
        pwd = st.text_input("Password", type="password", key="login_pwd")

        cols = st.columns([1, 1, 3])
        if cols[0].button("Entrar", use_container_width=True):
            if not user or not pwd:
                st.warning("Ingresa usuario y password.")
            else:
                if r_ok:
                    ok = _verify_with_r(user, pwd)
                else:
                    ok = True  # fallback bypass
                if ok:
                    st.session_state.auth_ok = True
                    st.session_state.auth_user = user
                    st.rerun()
                else:
                    st.error("Credenciales inválidas.")

        if cols[1].button("Salir", use_container_width=True):
            st.stop()

    st.stop()


def logout_button():
    if st.sidebar.button("Cerrar sesión", use_container_width=True):
        st.session_state.auth_ok = False
        st.session_state.auth_user = None
        st.rerun()


# -----------------------------
# App
# -----------------------------
st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")
require_login()

st.title(APP_TITLE)
st.caption(f"Usuario: {st.session_state.get('auth_user') or '-'}")

logout_button()

# logo (if present)
logo_path = Path("www") / "logo.png"
if logo_path.exists():
    st.sidebar.image(str(logo_path), use_container_width=True)

# data sources
snapshot_path = Path(os.getenv("SNAPSHOT_CSV", str(DEFAULT_SNAPSHOT_CSV)))
reviewed_path = Path(os.getenv("REVIEWED_CSV", str(DEFAULT_REVIEWED_CSV)))

snapshot_src = SnapshotSource(snapshot_path)
review_store = ReviewStore(reviewed_path)

blocked_rfcs = load_blocked_rfcs(Path("www"))

# Load / normalize
raw_snapshot = snapshot_src.read_or_empty()
snapshot = build_snapshot_view(raw_snapshot)

# apply RFC blocklist (same intent as Shiny)
if not snapshot.empty and "rfc" in snapshot.columns and blocked_rfcs:
    snapshot = snapshot[~snapshot["rfc"].astype(str).map(lambda x: "".join(ch for ch in str(x).upper() if ch.isalnum())).isin(blocked_rfcs)].copy()

reviewed_tbl = review_store.read_or_empty()
enriched_df = enrich(snapshot, reviewed_tbl)

# Sidebar filters
st.sidebar.header("Filtros")

# date range default: last 7 days (for pending tab) but bounded by available data
today = date.today()
default_start = today.replace(day=today.day)  # placeholder
default_start = today  # will adjust below

# compute suggested default range from data if possible
created_dates = []
if not enriched_df.empty:
    tmp = pd.to_datetime(enriched_df["created_mx"], errors="coerce")
    tmp = tmp.dropna()
    if not tmp.empty:
        created_dates = tmp.dt.date.tolist()

if created_dates:
    max_d = max(created_dates)
    min_d = max(max_d.replace(day=max_d.day), max_d)  # noop
    default_end = max_d
    default_start = max_d - pd.Timedelta(days=7)
    default_start = default_start.date()
else:
    default_end = today
    default_start = today

created_range = st.sidebar.date_input(
    "Rango creación (solo Pendientes)",
    value=(default_start, default_end),
)

if isinstance(created_range, tuple) and len(created_range) == 2:
    created_range_tuple = (created_range[0], created_range[1])
else:
    created_range_tuple = None

status_sel = st.sidebar.multiselect(
    "Estatus (optools)",
    options=ALLOWED_STATUSES,
    default=ALLOWED_STATUSES,
)

# KPIs (same filter logic as Shiny module)
kpi = kpis(enriched_df, created_range_tuple, status_sel)
k1, k2, k3 = st.columns(3)
k1.metric("Pendientes", kpi["pending"])
k2.metric("Revisados", kpi["reviewed"])
k3.metric("% Revisados", kpi["conv"])

tab_pending, tab_reviewed, tab_downloads, tab_admin = st.tabs(["Pendientes", "Revisados", "Descargas", "Admin"])

# Helper: render selectable table
def selectable_table(df: pd.DataFrame, key: str) -> tuple[pd.DataFrame, list[str]]:
    if df.empty:
        st.info("Sin resultados.")
        return df, []

    work = df.copy()
    # add selection checkbox (Streamlit doesn't have DT row selection like Shiny)
    sel_col = "Seleccionar"
    if sel_col not in work.columns:
        work.insert(0, sel_col, False)

    edited = st.data_editor(
        work,
        key=key,
        hide_index=True,
        use_container_width=True,
        column_config={sel_col: st.column_config.CheckboxColumn(required=False)},
        disabled=[c for c in work.columns if c != sel_col],
    )
    selected = edited[edited[sel_col] == True]
    selected_ids = selected["Lead_id"].astype(str).tolist() if "Lead_id" in selected.columns else []
    # return view without selector for downstream
    return edited.drop(columns=[sel_col]), selected_ids


with tab_pending:
    pending = enriched_df[enriched_df["revisado"] == 0].copy()
    pending = apply_filters(pending, reviewed=False, created_range=created_range_tuple, statuses=status_sel)

    st.subheader("Pendientes")
    view_df, selected_ids = selectable_table(pending, key="pending_tbl")

    btn_cols = st.columns(4)
    if btn_cols[0].button("Marcar revisado (MAU)", use_container_width=True):
        if selected_ids:
            review_store.mark(selected_ids, "MAU")
            st.success(f"Marcados {len(selected_ids)}")
            st.rerun()
        else:
            st.warning("Selecciona filas.")
    if btn_cols[1].button("Marcar revisado (BRANDON)", use_container_width=True):
        if selected_ids:
            review_store.mark(selected_ids, "BRANDON")
            st.success(f"Marcados {len(selected_ids)}")
            st.rerun()
        else:
            st.warning("Selecciona filas.")
    if btn_cols[2].button("Marcar revisado (TANIA)", use_container_width=True):
        if selected_ids:
            review_store.mark(selected_ids, "TANIA")
            st.success(f"Marcados {len(selected_ids)}")
            st.rerun()
        else:
            st.warning("Selecciona filas.")
    if btn_cols[3].button("Recargar snapshot", use_container_width=True):
        st.rerun()

with tab_reviewed:
    reviewed = enriched_df[enriched_df["revisado"] == 1].copy()
    reviewed = apply_filters(reviewed, reviewed=True, created_range=None, statuses=status_sel)

    st.subheader("Revisados")
    _view_df, _sel = selectable_table(reviewed, key="reviewed_tbl")

with tab_downloads:
    st.subheader("Descargas")

    # Mirror Shiny: download visible data from pending module + reviewed file
    pending = enriched_df[enriched_df["revisado"] == 0].copy()
    pending = apply_filters(pending, reviewed=False, created_range=created_range_tuple, statuses=status_sel)

    reviewed = enriched_df[enriched_df["revisado"] == 1].copy()
    reviewed = apply_filters(reviewed, reviewed=True, created_range=None, statuses=status_sel)

    st.write("Pendientes (filtrado actual):")
    st.download_button(
        "Descargar CSV (pendientes)",
        data=pending.to_csv(index=False).encode("utf-8-sig"),
        file_name="pendientes.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.write("Revisados (filtrado actual):")
    st.download_button(
        "Descargar CSV (revisados)",
        data=reviewed.to_csv(index=False).encode("utf-8-sig"),
        file_name="revisados.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.write("Reviewed store (raw):")
    st.download_button(
        "Descargar CSV (reviewed_leads_app.csv)",
        data=reviewed_tbl.to_csv(index=False).encode("utf-8-sig"),
        file_name=reviewed_path.name,
        mime="text/csv",
        use_container_width=True,
    )

with tab_admin:
    st.subheader("Admin")

    st.write("Rutas actuales:")
    st.code(f"snapshot: {snapshot_path}\nreviewed: {reviewed_path}")

    # reset reviewed
    admin_user = str(st.session_state.get("auth_user") or "").lower()
    is_admin = admin_user in {"doc", "enrique"} or (os.getenv("ADMIN_USERS", "") != "" and admin_user in {u.strip().lower() for u in os.getenv("ADMIN_USERS","").split(",")})

    if not is_admin:
        st.info("Modo admin restringido.")
    else:
        if st.button("Reset reviewed (borrar marcas)", type="primary"):
            review_store.reset()
            st.success("Reviewed reset.")
            st.rerun()

    st.write("Preview snapshot (primeras 50 filas):")
    st.dataframe(snapshot.head(50), use_container_width=True)

    st.write("Preview reviewed store:")
    st.dataframe(reviewed_tbl.head(50), use_container_width=True)
