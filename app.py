import base64
from pathlib import Path
import streamlit as st
import yaml
from simple_auth import require_shared_password

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="HayCash ToolBox",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

require_shared_password()

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"

# --- UTILS ---
def b64(path: Path) -> str:
    if not path.exists(): return ""
    return base64.b64encode(path.read_bytes()).decode("utf-8")

def load_registry():
    cfg_path = ROOT / "apps.yaml"
    if not cfg_path.exists(): return []
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    return cfg.get("apps", [])

# --- NAVIGATION MAP ---
PAGE_BY_ID = {
    "cdf_isaac": "pages/01_Lector_CSF.py",
    "diegobbva": "pages/02_CSV_a_TXT_BBVA.py",
    "analisis_leads": "pages/03_Reporte_Interactivo_de_Leads.py",
    "factoraje": "pages/04_Factoraje.py",
    "lector_edocat": "pages/05_Lector_edocat.py",
    "reporte_consejo": "pages/06_reporte_consejo.py",
    "lector_contrato": "pages/07_lector_contrato.py",
}

apps = load_registry()
logo_b64 = b64(ASSETS / "haycash_logo.jpg")

# --- JAW-DROPPING CSS ---
st.markdown(f"""
    <style>
        /* GLOBAL RESET & FONTS */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
        
        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
        }}

        /* BACKGROUND - Deep Midnight Finance Theme */
        .stApp {{
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #172554 100%);
            background-attachment: fixed;
        }}

        /* LAYOUT FIXES */
        .block-container {{
            padding-top: 2rem !important;
            padding-bottom: 5rem !important;
            max-width: 1400px !important;
        }}

        /* HIDE DEFAULT STREAMLIT ELEMENTS */
        [data-testid="stSidebarNav"], 
        [data-testid="collapsedControl"],
        header[data-testid="stHeader"] {{
            display: none !important;
        }}

        /* --- SIDEBAR: FROSTED GLASS --- */
        section[data-testid="stSidebar"] {{
            background-color: rgba(15, 23, 42, 0.6) !important;
            backdrop-filter: blur(20px);
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }}
        
        section[data-testid="stSidebar"] h2 {{
            color: #fff;
            font-weight: 600;
            font-size: 1.2rem;
            margin-bottom: 0.5rem;
        }}
        
        section[data-testid="stSidebar"] p {{
            color: #94a3b8;
            font-size: 0.85rem;
        }}
        
        /* Sidebar Buttons */
        section[data-testid="stSidebar"] button {{
            background: transparent !important;
            border: 1px solid rgba(255,255,255,0.1) !important;
            color: #cbd5e1 !important;
            text-align: left !important;
            transition: all 0.2s ease;
        }}
        section[data-testid="stSidebar"] button:hover {{
            background: rgba(255,255,255,0.1) !important;
            color: #fff !important;
            border-color: #FFBA00 !important;
        }}

        /* --- HERO SECTION --- */
        .hero-container {{
            position: relative;
            background: rgba(30, 41, 59, 0.7);
            border-radius: 24px;
            padding: 4rem 3rem;
            margin-bottom: 3rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 20px 50px -12px rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(10px);
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        
        /* Subtle glow effect behind hero */
        .hero-container::before {{
            content: '';
            position: absolute;
            top: -50%;
            right: -10%;
            width: 400px;
            height: 400px;
            background: radial-gradient(circle, rgba(255, 186, 0, 0.15) 0%, rgba(0,0,0,0) 70%);
            z-index: 0;
            pointer-events: none;
        }}

        .hero-content {{
            z-index: 1;
        }}

        .hero-title {{
            font-size: 3.5rem;
            font-weight: 800;
            background: linear-gradient(to right, #ffffff, #94a3b8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1rem;
            line-height: 1.1;
        }}

        .hero-subtitle {{
            font-size: 1.25rem;
            color: #94a3b8;
            font-weight: 300;
            max-width: 600px;
        }}

        .hero-logo {{
            height: 100px;
            width: auto;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            z-index: 1;
        }}

        /* --- CARDS --- */
        .card-container {{
            background: rgba(30, 41, 59, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 20px;
            padding: 24px;
            height: 100%;
            transition: transform 0.3s ease, box-shadow 0.3s ease, border-color 0.3s ease;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            position: relative;
            overflow: hidden;
        }}
        
        .card-container:hover {{
            transform: translateY(-6px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.4);
            border-color: rgba(255, 186, 0, 0.3);
            background: rgba(30, 41, 59, 0.6);
        }}

        .card-icon {{
            font-size: 2.5rem;
            margin-bottom: 1rem;
            background: rgba(255, 255, 255, 0.05);
            width: 64px;
            height: 64px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 16px;
            color: #FFBA00;
        }}

        .card-title {{
            color: #fff;
            font-size: 1.4rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }}

        .card-desc {{
            color: #94a3b8;
            font-size: 0.95rem;
            line-height: 1.5;
            margin-bottom: 1.5rem;
            flex-grow: 1;
        }}

        /* --- BUTTON OVERRIDES --- */
        /* We target the specific button inside the columns */
        div[data-testid="stVerticalBlock"] button {{
            background: #FFBA00 !important;
            color: #0f172a !important;
            border: none !important;
            font-weight: 700 !important;
            padding: 0.6rem 1.2rem !important;
            border-radius: 10px !important;
            width: 100%;
            transition: all 0.2s ease;
            text-transform: uppercase;
            font-size: 0.85rem !important;
            letter-spacing: 0.5px;
        }}
        
        div[data-testid="stVerticalBlock"] button:hover {{
            background: #eebb00 !important;
            transform: scale(1.02);
            box-shadow: 0 0 15px rgba(255, 186, 0, 0.4);
        }}
        
        /* Section Header */
        .section-header {{
            color: #fff;
            font-size: 1.5rem;
            font-weight: 600;
            margin: 2rem 0 1.5rem 0;
            border-left: 4px solid #FFBA00;
            padding-left: 1rem;
        }}

    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR CONTENT ---
with st.sidebar:
    if logo_b64:
        st.markdown(f"""
            <div style="text-align: center; margin-bottom: 2rem;">
                <img src="data:image/jpg;base64,{logo_b64}" style="width: 80%; border-radius: 12px; opacity: 0.9;">
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("## Menú Rápido")
    st.markdown("<p>Navegación directa</p>", unsafe_allow_html=True)
    st.divider()
    
    # Sidebar Navigation Buttons
    for app_id, page in PAGE_BY_ID.items():
        # Clean up the name for the sidebar
        raw_name = next((a.get("name") for a in apps if a.get("id") == app_id), app_id)
        # Add simple icon logic for sidebar list
        icon = "🔹"
        if "CSF" in raw_name: icon = "🧾"
        elif "BBVA" in raw_name: icon = "🏦"
        elif "Leads" in raw_name: icon = "📊"
        elif "Factoraje" in raw_name: icon = "💳"
        
        if st.button(f"{icon}  {raw_name}", key=f"nav_{app_id}", use_container_width=True):
            st.switch_page(page)

# --- MAIN HERO AREA ---
st.markdown(f"""
    <div class="hero-container">
        <div class="hero-content">
            <div class="hero-title">HayCash ToolBox</div>
            <div class="hero-subtitle">Plataforma centralizada para gestión financiera, análisis de datos y automatización operativa.</div>
        </div>
        <img src="data:image/jpg;base64,{logo_b64}" class="hero-logo">
    </div>
""", unsafe_allow_html=True)


# --- DASHBOARD GRID ---
st.markdown('<div class="section-header">Módulos Operativos</div>', unsafe_allow_html=True)

# Grid Layout Strategy
cols = st.columns(3)

for i, a in enumerate(apps):
    col = cols[i % 3]
    
    # Determine Icon based on app name
    name = a.get("name", "Herramienta")
    icon = "⚡"
    if "CSF" in name: icon = "🧾"
    elif "BBVA" in name: icon = "🏦"
    elif "Leads" in name: icon = "📊"
    elif "Factoraje" in name: icon = "💳"
    elif "Edocat" in name: icon = "📄"
    elif "Consejo" in name: icon = "📈"
    elif "Contrato" in name: icon = "📝"
    
    with col:
        # Card HTML Structure
        st.markdown(f"""
            <div class="card-container">
                <div>
                    <div class="card-icon">{icon}</div>
                    <div class="card-title">{name}</div>
                    <div class="card-desc">Acceso directo al módulo de {name.lower()} para operaciones y reportes.</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # The button sits outside the HTML div but visually blends because of the column layout
        # We use a container to pull the button 'up' visually via CSS if needed, 
        # but standard stacking works best for functionality.
        if st.button("ACCEDER", key=f"btn_{a.get('id')}"):
            target = PAGE_BY_ID.get(a.get("id"))
            if target:
                st.switch_page(target)
            else:
                st.error("Módulo no disponible.")
        
        # Spacer for grid alignment
        st.markdown("<div style='margin-bottom: 25px;'></div>", unsafe_allow_html=True)
