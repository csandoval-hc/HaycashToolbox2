import os
import sys
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

try:
    os.chdir(str(_APP_DIR))
except Exception:
    pass

import shutil
import subprocess
from datetime import date, timedelta

import pandas as pd
import streamlit as st
import sqlalchemy

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

EMBEDDED = os.getenv("HC_EMBEDDED", "0") == "1"
SKIP_PAGE_CONFIG = os.getenv("HC_SKIP_PAGE_CONFIG", "0") == "1"
SKIP_INTERNAL_AUTH = os.getenv("HC_SKIP_INTERNAL_AUTH", "0") == "1"


def _rscript_path() -> str | None:
    return shutil.which("Rscript")


def _verify_with_r(user: str, password: str) -> bool:
    r = _rscript_path()
    if not r:
        return False

    script = Path(__file__).with_name("verify_credentials.R")
    proc = subprocess.run(
        [r, str(script), user, password],
        cwd=str(Path(__file__).parent),
        capture_output=True,
        text=True,
        timeout=12,
    )
    return proc.returncode == 0


def require_login():
    if SKIP_INTERNAL_AUTH:
        # wrapper auth is source of truth; just ensure fields exist
        if "auth_ok" not in st.session_state:
            st.session_state.auth_ok = True
        if "auth_user" not in st.session_state:
            st.session_state.auth_user = st.session_state.get("auth_user") or "Carlos"
        return

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
                ok = _verify_with_r(user, pwd) if r_ok else True
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


if not SKIP_PAGE_CONFIG:
    st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")

require_login()

# IMPORTANT: In embedded mode, do NOT add extra titles/captions/logos/logout
if not EMBEDDED:
    st.title(APP_TITLE)
    st.caption(f"Usuario: {st.session_state.get('auth_user') or '-'}")
    logout_button()

    logo_path = Path("www") / "logo.png"
    if logo_path.exists():
        st.sidebar.image(str(logo_path), use_container_width=True)

# =========================================================================
# === DB CONFIGURATION (FILL THESE IN WITH YOUR MYSQL CREDENTIALS) ===
# =========================================================================
DB_HOST = "haycash-prod.cluster-cymmiznbjsjw.us-east-1.rds.amazonaws.com"
DB_USER = "csandoval"
DB_PASS = "4Jz~QT,Epa%d@K#(yRSp*=V265+q0vdC"
DB_NAME = "calculados"

@st.cache_resource
def get_db_engine():
    return sqlalchemy.create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}")

engine = get_db_engine()

class ReviewStoreDB:
    """Replaces the CSV ReviewStore to read/write directly to MySQL"""
    def __init__(self, db_engine, table_name="reviewed_leads_app"):
        self.engine = db_engine
        self.table_name = table_name

    def read_or_empty(self):
        try:
            return pd.read_sql(self.table_name, self.engine)
        except Exception:
            return pd.DataFrame()

    def mark(self, lead_ids, user):
        import datetime
        df = self.read_or_empty()
        
        if 'Lead_id' not in df.columns:
            df['Lead_id'] = []

        # Remove old marks for these IDs so we don't duplicate
        if not df.empty:
            df = df[~df['Lead_id'].astype(str).isin(map(str, lead_ids))]

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_rows = pd.DataFrame({
            "Lead_id": lead_ids,
            "revisado": 1,
            "revisado_por": user,
            "fecha_revision": now
        })
        
        df = pd.concat([df, new_rows], ignore_index=True)
        df.to_sql(self.table_name, self.engine, if_exists='replace', index=False)

    def reset(self):
        df = pd.DataFrame(columns=["Lead_id", "revisado", "revisado_por", "fecha_revision"])
        df.to_sql(self.table_name, self.engine, if_exists='replace', index=False)

# Read Data from MySQL
try:
    raw_snapshot = pd.read_sql("leads_dashboard_snapshot", engine)
except Exception:
    raw_snapshot = pd.DataFrame()

review_store = ReviewStoreDB(engine, "reviewed_leads_app")
reviewed_tbl = review_store.read_or_empty()
# =========================================================================

blocked_rfcs = load_blocked_rfcs(Path("www"))
snapshot = build_snapshot_view(raw_snapshot)

if not snapshot.empty and "rfc" in snapshot.columns and blocked_rfcs:
    snapshot = snapshot[
        ~snapshot["rfc"]
        .astype(str)
        .map(lambda x: "".join(ch for ch in str(x).upper() if ch.isalnum()))
        .isin(blocked_rfcs)
    ].copy()

enriched_df = enrich(snapshot, reviewed_tbl)

# Filters (these go into the wrapper card because sidebar is monkeypatched)
st.sidebar.header("Filtros")

today = date.today()
default_start = today - timedelta(days=90)
default_end = today

if not enriched_df.empty and "created_mx" in enriched_df.columns:
    tmp = pd.to_datetime(enriched_df["created_mx"], errors="coerce").dropna()
    if not tmp.empty:
        max_d = tmp.dt.date.max()
        min_d = tmp.dt.date.min()
        default_end = max_d
        default_start = max_d - timedelta(days=90)
        if default_start < min_d:
            default_start = min_d

created_range = st.sidebar.date_input(
    "Rango creación (solo Pendientes)",
    value=(default_start, default_end),
)

created_range_tuple = None
if isinstance(created_range, tuple) and len(created_range) == 2:
    start_d, end_d = created_range
    if start_d and end_d:
        if start_d > end_d:
            start_d, end_d = end_d, start_d
        created_range_tuple = (start_d, end_d)

status_sel = st.sidebar.multiselect(
    "Estatus (optools)",
    options=ALLOWED_STATUSES,
    default=ALLOWED_STATUSES,
)

kpi = kpis(enriched_df, created_range_tuple, status_sel)
k1, k2, k3 = st.columns(3)
k1.metric("Pendientes", kpi["pending"])
k2.metric("Revisados", kpi["reviewed"])
k3.metric("% Revisados", kpi["conv"])

tab_pending, tab_reviewed, tab_downloads, tab_admin = st.tabs(
    ["Pendientes", "Revisados", "Descargas", "Admin"]
)


def selectable_table(df: pd.DataFrame, key: str) -> tuple[pd.DataFrame, list[str]]:
    if df.empty:
        st.info("Sin resultados.")
        return df, []

    work = df.copy()
    sel_col = "Seleccionar"
    if sel_col not in work.columns:
        work.insert(0, sel_col, False)

    # Freeze 'nombre' column by setting it as the index
    # In Streamlit, the index is automatically pinned/frozen to the left side when scrolling
    if "nombre" in work.columns:
        work = work.set_index("nombre")
        hide_idx = False
    else:
        hide_idx = True

    edited = st.data_editor(
        work,
        key=key,
        hide_index=hide_idx,
        use_container_width=True,
        column_config={sel_col: st.column_config.CheckboxColumn(required=False)},
        disabled=[c for c in work.columns if c != sel_col],
    )
    
    selected = edited[edited[sel_col] == True]
    selected_ids = (
        selected["Lead_id"].astype(str).tolist() if "Lead_id" in selected.columns else []
    )
    return edited.drop(columns=[sel_col]), selected_ids


with tab_pending:
    pending = enriched_df[enriched_df.get("revisado", 0) == 0].copy()
    pending = apply_filters(
        pending, reviewed=False, created_range=created_range_tuple, statuses=status_sel
    )

    btn_container = st.container()

    st.subheader("Pendientes")
    _view_df, selected_ids = selectable_table(pending, key="pending_tbl")

    with btn_container:
        btn_cols = st.columns(3)

        # MAU removed
        if btn_cols[0].button("Revisado (BRANDON)", use_container_width=True, type="primary"):
            if selected_ids:
                review_store.mark(selected_ids, "BRANDON")
                st.success(f"Marcados {len(selected_ids)}")
                st.rerun()
            else:
                st.warning("Selecciona filas.")

        if btn_cols[1].button("Revisado (TANIA)", use_container_width=True, type="primary"):
            if selected_ids:
                review_store.mark(selected_ids, "TANIA")
                st.success(f"Marcados {len(selected_ids)}")
                st.rerun()
            else:
                st.warning("Selecciona filas.")

        if btn_cols[2].button("Recargar snapshot", use_container_width=True, type="primary"):
            st.rerun()

with tab_reviewed:
    reviewed = enriched_df[enriched_df.get("revisado", 0) == 1].copy()
    reviewed = apply_filters(reviewed, reviewed=True, created_range=None, statuses=status_sel)

    st.subheader("Revisados")
    selectable_table(reviewed, key="reviewed_tbl")

with tab_downloads:
    st.subheader("Descargas")

    pending = enriched_df[enriched_df.get("revisado", 0) == 0].copy()
    pending = apply_filters(
        pending, reviewed=False, created_range=created_range_tuple, statuses=status_sel
    )

    reviewed = enriched_df[enriched_df.get("revisado", 0) == 1].copy()
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
        file_name="reviewed_leads_app.csv",
        mime="text/csv",
        use_container_width=True,
    )

with tab_admin:
    st.subheader("Admin")

    st.write("Conexión de Base de Datos:")
    st.code(f"Host: {DB_HOST}\nBase de datos: {DB_NAME}")

    admin_user = str(st.session_state.get("auth_user") or "").lower()
    is_admin = admin_user in {"doc", "enrique"} or (
        os.getenv("ADMIN_USERS", "") != ""
        and admin_user in {u.strip().lower() for u in os.getenv("ADMIN_USERS", "").split(",")}
    )

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
