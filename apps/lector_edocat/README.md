# Lector edocat (Streamlit)

Port a Streamlit/Python del archivo `lectura_edocta.R` (Shiny).

## 1) Crear carpeta del proyecto
Crea una carpeta (por ejemplo `Lector_edocat_streamlit`) y coloca dentro el archivo:

- `app.py`

## 2) Crear y activar entorno virtual (PowerShell)
```powershell
cd "C:\ruta\a\Lector_edocat_streamlit"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 3) Instalar dependencias
```powershell
pip install streamlit pytesseract pypdfium2 pillow pandas
```

## 4) Instalar Tesseract (OBLIGATORIO para OCR)
Este proyecto usa **Tesseract OCR** (binario externo). En Windows:

1. Instala Tesseract (por ejemplo el instalador de UB Mannheim).
2. Durante instalación, habilita el idioma **Spanish** (spa) si aparece en opciones.
3. Verifica en PowerShell:
```powershell
tesseract --version
```

### Si `tesseract` no se reconoce
Opción A: agrega Tesseract al PATH (recomendado).

Opción B: define la ruta del ejecutable (solo para la sesión):
```powershell
$env:TESSERACT_CMD="C:\Program Files\Tesseract-OCR\tesseract.exe"
```

### Si falla el idioma "spa"
Asegúrate de que existe `spa.traineddata` dentro de tu `tessdata` y define:
```powershell
$env:TESSDATA_PREFIX="C:\Program Files\Tesseract-OCR\tessdata"
```

## 5) Ejecutar
```powershell
streamlit run app.py
```

Se abrirá el navegador con la app.

## Notas
- Esta versión renderiza el PDF con `pypdfium2`, por lo que NO necesitas Poppler.
- El resumen usa los mismos patrones regex del script R original.
