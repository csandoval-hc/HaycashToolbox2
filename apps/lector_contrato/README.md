# Lector Contrato (Streamlit)

Port en Python/Streamlit del app original en R/Shiny.

## 1) Requisitos (Windows)

1. Python 3.10+ (recomendado 3.11)
2. (Opcional pero recomendado) Tesseract OCR para PDFs escaneados:
   - Instala Tesseract (UB Mannheim) con `winget` o instalador.
   - Si `tesseract --version` no funciona, configura la ruta con `TESSERACT_CMD`.

## 2) Instalación

En PowerShell, dentro de la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 3) Ejecutar

```powershell
streamlit run app.py
```

## 4) Tesseract (solo si OCR es necesario)

### Opción A: variable de entorno (PowerShell)

```powershell
$env:TESSERACT_CMD="C:\Program Files\Tesseract-OCR\tesseract.exe"
streamlit run app.py
```

### Opción B: desde la interfaz

En el sidebar pega la ruta completa de `tesseract.exe`.

## 5) Salida

- Vista previa: columnas numéricas (capital, valor_pagare, cpa, min_payment)
- Excel: incluye también columnas `*_raw` para depurar capturas.
