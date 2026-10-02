import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

def extract_data_from_pdf(pdf_file):
    # Extraer todo el texto del PDF
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    
    # Unificar el texto para facilitar la búsqueda
    text = text.replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text)
    
    data = {}
    
    # 1. Calicata
    match = re.search(r"Calicata\s+([A-Za-z0-9\-]+)", text)
    data["Calicata"] = match.group(1) if match else ""
    
    # 2. Muestra
    match = re.search(r"Muestra\s+([A-Za-z0-9\-]+)", text)
    data["Muestra"] = match.group(1) if match else ""
    
    # 3, 4 y 5. Grava, Arena y Fino
    match = re.search(r"N[°º]?\s*4\s+4\.750\s+([\d\.]+)\s+[\d\.]+\s+100\.0", text)
    grava = match.group(1) if match else None
    
    match = re.search(r"N[°º]?\s*200\s+0\.075\s+[\d\.]+\s+([\d\.]+)\s+([\d\.]+)", text)
    if match:
        arena = match.group(1)
        fino = match.group(2)
        if not grava:
            try:
                grava = round(100.0 - float(arena) - float(fino), 1)
            except:
                grava = ""
    else:
        arena = None
        fino = None
        
    data["Grava (Ret. Nº4)"] = f"{grava}%" if grava is not None else ""
    data["Arena"] = f"{arena}%" if arena is not None else ""
    data["Fino (Pas. Nº200)"] = f"{fino}%" if fino is not None else ""
    
    # 6. Límite Líquido (L.L)
    match = re.search(r"LÍMITE LÍQUIDO\s*\(?\s*%\s*\)?\s*([\d\.]+)", text)
    ll = float(match.group(1)) if match else 0.0
    data["Límite Líquido (L.L)"] = f"{ll}%"
    
    # 7. Índice Plástico (I.P)
    match = re.search(r"ÍNDICE DE PLASTICIDAD\s*\(?\s*%\s*\)?\s*([\d\.]+)", text)
    ip = float(match.group(1)) if match else 0.0
    data["Índice Plástico (I.P)"] = f"{ip}%"
    
    # 8. Límite Plástico (L.P)
    match = re.search(r"LÍMITE PL[AÁ]STICO\s*\(?\s*%\s*\)?\s*([\d\.]+)", text)
    lp = float(match.group(1)) if match else (ll - ip)
    data["Límite Plástico (L.P)"] = f"{lp:.1f}%"
    
    # 9. Clasificación AASHTO
    match = re.search(r"(A-\d+-?\d*\s*\(\s*\d+\s*\))", text)
    data["ASTM D 3282, \"Clasificación para el uso en vías transporte\" (AASHTO)"] = match.group(1) if match else ""
    
    # 10. Clasificación SUCS (Código de 2 letras)
    match = re.search(r"SUCS\)\s*.*?\b([A-Z]{2})\b", text)
    if not match:
        match = re.search(r"Clasif\.?\s*SUCS\s*[:.]?\s*([A-Z]{2})\b", text)
    data["ASTM D 2487_Codigo"] = match.group(1) if match else ""
    
    # 11. Descripción SUCS
    match = re.search(r"\b(Arcilla|Limo|Arena|Grava|Suelo)\s+([a-záéíóú\s,]+?)\s+(?:N[°º]?\s*\d+|\d+\.\d+|Mallas|Pasa|Retenido|Serie|ABERTURA)", text, re.IGNORECASE)
    if match:
        descripcion = f"{match.group(1)} {match.group(2)}".strip()
        descripcion = re.sub(r'[\d°º]+.*$', '', descripcion).strip()
        descripcion = re.sub(r'\s+(Mallas|Pasa|Retenido|Serie|Abertura)$', '', descripcion, flags=re.IGNORECASE).strip()
        data["ASTM D 2487_Descripcion"] = descripcion
    else:
        data["ASTM D 2487_Descripcion"] = ""
    
    # 12. Cont. de humedad
    match = re.search(r"Cont\. de humedad\s*:?\s*([\d\.]+)\s*%?", text)
    data["Cont. de humedad"] = f"{match.group(1)}%" if match else ""
    
    # 13 y 14. Tamaños menores a 5μm y 2μm
    match_5um = re.search(r"Tama[ñn]os menores a 5[µμ]m", text)
    if match_5um:
        start_pos = match_5um.end()
        percentages = re.findall(r"([\d\.]+)\s*%", text[start_pos:])
        valid_percentages = [p for p in percentages if p != '.']
        if len(valid_percentages) > 0:
            data["Tamaños menores a 5μm (0.005mm)"] = f"{valid_percentages[0]}%"
        if len(valid_percentages) > 1:
            data["Tamaños menores a 2μm (0.002mm)"] = f"{valid_percentages[1]}%"
    
    # 15. Material Pasante del Tamiz N° 200 por Lavado
    match = re.search(r"Pasante Tamiz N[°º]?\s*200\s*\(?\s*%\s*\)?\s*([\d\.]+)", text)
    if not match:
        match = re.search(r"N[°º]?\s*200\s+0\.075\s+[\d\.]+\s+[\d\.]+\s+([\d\.]+)", text)
    if not match:
        match = re.search(r"([\d\.]+)\s*Material Pasante del Tamiz N[°º]?\s*200 por Lavado", text)
    data["Material Pasante del Tamiz N° 200 por Lavado"] = match.group(1) if match else ""
    
    # 16. Contenido de Humedad (RESULTADO)
    match = re.search(r"Contenido de Humedad\s*\(RESULTADO\)\s*\(?\s*%\s*\)?\s*([\d\.]+)", text)
    data["Contenido de Humedad (RESULTADO)"] = match.group(1) if match else ""
    
    # 17. RESULTADO (ASTM C 40)
    match = re.search(r"RESULTADO\s+(ACEPTABLE|NO ACEPTABLE)", text, re.IGNORECASE)
    data["RESULTADO"] = match.group(1).upper() if match else ""
    
    # 18, 19 y 20. SALES SOLUBLES, CLORUROS y SULFATOS (Lógica a prueba de comas y espacios)
    def get_chem_val(full_text, title):
        idx = full_text.rfind(title)
        if idx != -1:
            # Acotar el bloque a 500 caracteres para no leer el siguiente ensayo
            sub_text = full_text[idx:idx+500]
            # Encontrar la línea de "Profundidad (m): X.XX - Y.YY"
            match_depth = re.search(r"Profundidad\s*\(m\):\s*\d+(?:\.\d+)?\s*-\s*\d+(?:\.\d+)?", sub_text)
            if match_depth:
                search_area = sub_text[match_depth.end():]
                # Buscar el primer número disponible, saltando comas, espacios, etc.
                num_match = re.search(r"\d[\d\s\.]*\d|\d", search_area)
                if num_match:
                    val = num_match.group(0).replace(" ", "")
                    val = val.rstrip('.')
                    # Validar que sea un número bien formado antes de retornarlo
                    if re.match(r"^\d+(?:\.\d+)?$", val):
                        return val
        return ""

    data["SALES SOLUBLES TOTALES(%)"] = get_chem_val(text, "SALES SOLUBLES")
    data["CLORUROS EXPRESADOS COMO IÓN Cl -"] = get_chem_val(text, "CLORUROS EXPRESADOS")
    data["SULFATOS EXPRESADOS COMO IÓN SO4("] = get_chem_val(text, "SULFATOS EXPRESADOS")
    
    # 21. MDS
    match = re.search(r"MDS\s+([\d\.]+)\s*gr/cm³", text)
    data["MDS"] = f"{match.group(1)} gr/cm³" if match else ""
    
    # 22. OCH
    match = re.search(r"OCH\s+([\d\.]+)\s*%", text)
    data["OCH"] = f"{match.group(1)}%" if match else ""
    
    return data

# ----------------- Configuración de la Interfaz Streamlit -----------------
st.set_page_config(page_title="Extractor de Ensayos", layout="wide")
st.title("📄 Extractor de Datos de Pavimentos a Excel")
st.write("Sube uno o varios archivos PDF con los resultados de los ensayos. El sistema extraerá los datos y los apilará en un solo archivo Excel.")

uploaded_files = st.file_uploader("Sube los archivos PDF aquí", type=["pdf"], accept_multiple_files=True)

if uploaded_files and len(uploaded_files) > 0:
    all_data = []
    progress_bar = st.progress(0)
    
    for i, uploaded_file in enumerate(uploaded_files):
        try:
            with st.spinner(f"Procesando {i+1} de {len(uploaded_files)}: {uploaded_file.name}..."):
                extracted_data = extract_data_from_pdf(uploaded_file)
                all_data.append(extracted_data)
        except Exception as e:
            st.error(f"Ocurrió un error al procesar el archivo {uploaded_file.name}: {e}")
        
        progress_bar.progress((i + 1) / len(uploaded_files))
    
    if all_data:
        df = pd.DataFrame(all_data)
        
        # Renombrar columnas para coincidir con el Excel
        df = df.rename(columns={
            "ASTM D 2487_Codigo": "ASTM D 2487, \"Clasificación con propósito de ingeniería\" (SUCS)_1",
            "ASTM D 2487_Descripcion": "ASTM D 2487, \"Clasificación con propósito de ingeniería\" (SUCS)_2"
        })
        
        st.success(f"¡Se procesaron correctamente {len(all_data)} archivo(s)!")
        st.write("Vista previa de los datos extraídos y apilados:")
        st.dataframe(df, use_container_width=True)
        
        # Generar el archivo Excel en memoria
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Hoja1')
        processed_data = output.getvalue()
        
        st.download_button(
            label="📥 Descargar archivo Excel consolidado",
            data=processed_data,
            file_name="Resumen_Ensayos_Pavimentos_Consolidado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
