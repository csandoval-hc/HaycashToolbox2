# --- bootstrap so local imports (main.py) work on Streamlit Cloud ---
import sys
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))
# -------------------------------------------------------------------

import os
import tempfile
import streamlit as st

# Import WITHOUT modifying existing logic/functions
import main


st.set_page_config(page_title="Reporte Consejo", layout="wide")

st.title("Reporte Consejo")
st.caption("Genera el Excel exactamente con la lógica existente en main.py.")

with st.sidebar:
    st.header("Parámetros")
    fecha_ev = st.text_input("Fecha de evaluación (YYYY-MM o YYYY-MM-DD)", value="2025-12")
    nombre_archivo = st.text_input("Nombre del archivo (xlsx)", value="reporte_concejo.xlsx")

    generar = st.button("Generar Excel", type="primary")

if generar:
    try:
        # Create a temporary output path; main.py still writes to the path you pass in.
        # We keep the same function/logic; only the UI + file handling is new.
        tmp_dir = tempfile.mkdtemp(prefix="reporte_consejo_")
        out_path = os.path.join(tmp_dir, nombre_archivo)

        main.generar_excel_financieros(fecha_ev, out_path)

        with open(out_path, "rb") as f:
            data = f.read()

        st.success("Archivo generado.")
        st.download_button(
            label="Descargar Excel",
            data=data,
            file_name=nombre_archivo,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except Exception as e:
        st.error(f"Error al generar el archivo: {e}")

st.divider()
st.subheader("Opcional: Vista previa de tablas")
show_preview = st.checkbox("Mostrar vista previa", value=False)

if show_preview:
    try:
        # These calls reuse the existing functions as-is.
        filas_fin, valores_capital, valores_vp = main.calcular_metricas_financieras(fecha_ev)
        df_fin = main.pd.DataFrame({
            "Concepto": filas_fin,
            "Valor capital": valores_capital,
            "Valor pagare": valores_vp,
        })
        st.markdown("### Financieros")
        st.dataframe(df_fin, use_container_width=True)

        filas_ind, col_ytd, col_ltm, col_hist = main.calcular_indicadores_relevantes(fecha_ev)
        df_ind = main.pd.DataFrame({
            "Indicador": filas_ind,
            "Year to date": col_ytd,
            "LTM last twelve months": col_ltm,
            "Historico desde el inicio": col_hist,
        })
        st.markdown("### Indicadores relevantes")
        st.dataframe(df_ind, use_container_width=True)

        st.markdown("### Colocación mensual")
        st.dataframe(main.calcular_colocacion_mensual(fecha_ev), use_container_width=True)

        st.markdown("### Amortización mensual")
        st.dataframe(main.calcular_amortizacion_mensual(fecha_ev), use_container_width=True)

        st.markdown("### Distribución cartera")
        df_giro, df_prov = main.calcular_distribucion_cartera(fecha_ev)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Por giro")
            st.dataframe(df_giro, use_container_width=True)
        with c2:
            st.markdown("#### Por provincia")
            st.dataframe(df_prov, use_container_width=True)

    except Exception as e:
        st.warning(f"No se pudo mostrar la vista previa: {e}")
