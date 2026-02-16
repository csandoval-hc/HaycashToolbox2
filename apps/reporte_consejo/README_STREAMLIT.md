# Reporte Consejo - Streamlit

Este proyecto mantiene **intacto** `main.py` (lógica y funciones).  
Se agregó únicamente `streamlit_app.py` para exponer la misma funcionalidad en una interfaz web con Streamlit.

## Ejecutar

Desde la carpeta del proyecto:

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Notas
- La generación del Excel usa exactamente `main.generar_excel_financieros(...)`.
- La vista previa (opcional) llama a las mismas funciones de `main.py` y solo muestra los DataFrames.
