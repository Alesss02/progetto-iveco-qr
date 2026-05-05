import streamlit as st
import qrcode
import pandas as pd
import datetime
import time
import random
import os
import ast
import base64
from io import BytesIO
from PIL import Image

# ==============================================================================
# 1. CONFIGURAZIONI E DATI DI BASE
# ==============================================================================
DB_FILE = "database_bolle.csv"
CATEGORIE = ['Motore', 'Elettronica', 'Freni', 'Cambio']
TECNICI = ['Marco', 'Luca', 'Antonio', 'Davide', 'Roberto']
RICAMBI_CATALOGO = ["Olio 5W30", "Filtro Aria", "Pasticche Freni", "Cinghia", "Sensore NOx"]

CHECKLIST_DATA = {
    'Motore': [
        {"task": "Serraggio Testata", "risk": "ALTO", "eco": False},
        {"task": "Test Efficienza Termica", "risk": "BASSO", "eco": True}
    ],
    'Cambio': [
        {"task": "Allineamento Ingranaggi", "risk": "ALTO", "eco": False},
        {"task": "Recupero Olio Esausto", "risk": "MEDIO", "eco": True}
    ],
    'Freni': [
        {"task": "Verifica Spessore Dischi", "risk": "ALTO", "eco": False},
        {"task": "Smaltimento Polveri", "risk": "MEDIO", "eco": True}
    ],
    'Elettronica': [
        {"task": "Diagnosi Errori DTC", "risk": "MEDIO", "eco": False},
        {"task": "Ottimizzazione Centralina", "risk": "BASSO", "eco": True}
    ]
}

# ==============================================================================
# 2. MOTORE DI GESTIONE DATI (DATABASE)
# ==============================================================================
def safe_eval(val, default):
    """Converte stringhe in oggetti Python (liste/dict) senza crashare."""
    if not isinstance(val, str) or val == "" or pd.isna(val):
        return default
    try:
        return ast.literal_eval(val)
    except:
        return default

def carica_db():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        df = pd.read_csv(DB_FILE, index_col=0)
        # Pulizia preventiva NaN
        df = df.fillna({
            'tempo_sec': 0.0, 'stato_lavoro': 'In Attesa', 
            'foto_b64': '', 'checklist_state': '{}', 'ricambi_usati': '[]'
        })
        db_dict = df.to_dict('index')
        for k, v in db_dict.items():
            v['checklist_state'] = safe_eval(v['checklist_state'], {})
            v['ricambi_usati'] = safe_eval(v['ricambi_usati'], [])
        return db_dict
    except:
        return {}

def salva_db(db):
    if db:
        df = pd.DataFrame.from_dict(db, orient='index')
        df.to_csv(DB_FILE)

# Inizializzazione Session State
if 'db' not in st.session_state:
    st.session_state.db = carica_db()

# ==============================================================================
# 3. FUNZIONI UTILITY
# ==============================================================================
def encode_img(upload):
    img = Image.open(upload)
    img.thumbnail((500, 500)) # Compressione per CSV leggero
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode()

def get_qr(url):
    qr = qrcode.make(url)
    buf = BytesIO()
    qr.save(buf, format="PNG")
    return buf.getvalue()

# ==============================================================================
# 4. INTERFACCIA UTENTE (UI)
# ==============================================================================
st.set_page_config(page_title="IVECO Smart Hub 5.0", layout="wide")

# Routing: Operatore (se presente ID in URL) o Manager
params = st.query_params
b_id = params.get("bolla_id")

# --- VISTA OPERATORE ---
if b_id:
    if b_id not in st.session_state.db:
        st.error("Bolla non trovata.")
        if st.button("Torna Home"): st.query_params.clear(); st.rerun()
    else:
        bolla = st.session_state.db[b_id]
        st.title(f"🛠️ {bolla['veicolo']} ({b_id})")
        
        # 1. Timer e Stato
        c1, c2 = st.columns(2)
        c1.metric("Stato", bolla['stato_lavoro'])
        c2.metric("Minuti Lavorati", int(bolla.get('tempo_sec', 0) // 60))
        
        if bolla['stato_lavoro'] != "Completato":
            if bolla['stato_lavoro'] == "In Corso":
                if st.button("⏸️ SOSPENDI / FINE LAVORO", type="primary"):
                    delta = time.time() - bolla.get('last_start', time.time())
                    bolla['tempo_sec'] = bolla.get('tempo_sec', 0) + delta
                    bolla['stato_lavoro'] = "Completato"
                    salva_db(st.session_state.db); st.rerun()
            else:
                if st.button("▶️ INIZIA INTERVENTO", type="primary"):
                    bolla['last_start'] = time.time()
                    bolla['stato_lavoro'] = "In Corso"
                    salva_db(st.session_state.db); st.rerun()

        st.divider()

        # 2. Foto Guasto
        st.subheader("📸 Evidenza Digitale")
        foto_data = bolla.get('foto_b64', "")
        if foto_data and isinstance(foto_data, str) and len(foto_data) > 10:
            st.image(base64.b64decode(foto_data), width=300)
            if st.button("Elimina Foto"):
                bolla['foto_b64'] = ""; salva_db(st.session_state.db); st.rerun()
        else:
            up = st.file_uploader("Carica/Scatta Foto", type=['jpg', 'png'])
            if up:
                bolla['foto_b64'] = encode_img(up)
                salva_db(st.session_state.db); st.rerun()

        # 3. Checklist e Ricambi
        st.divider()
        st.subheader("📋 Task e Magazzino")
        tasks = CHECKLIST_DATA.get(bolla['categoria'], [])
        for i, t in enumerate(tasks):
            key = f"chk_{i}"
            val = bolla['checklist_state'].get(key, False)
            bolla['checklist_state'][key] = st.checkbox(f"{t['task']} ({t['risk']})", value=val)
        
        bolla['ricambi_usati'] = st.multiselect("Ricambi Utilizzati", RICAMBI_CATALOGO, default=bolla.get('ricambi_usati', []))

        if st.button("💾 SALVA AVANZAMENTO", use_container_width=True):
            salva_db(st.session_state.db)
            st.success("Dati sincronizzati col server!")

# --- VISTA MANAGER ---
else:
    st.title("🏭 IVECO Managerial Hub 5.0")
    t1, t2, t3 = st.tabs(["🆕 Accettazione", "📊 Monitor Officina", "📈 Analisi KPI"])

    with t1:
        with st.form("nuova_bolla"):
            v = st.text_input("Targa / Modello")
            c = st.selectbox("Categoria", CATEGORIE)
            t = st.selectbox("Assegna Tecnico", TECNICI)
            if st.form_submit_button("GENERA QR CODE"):
                new_id = f"IV-{random.randint(1000,9999)}"
                st.session_state.db[new_id] = {
                    "veicolo": v, "categoria": c, "tecnico": t, "stato_lavoro": "In Attesa",
                    "tempo_sec": 0.0, "checklist_state": {}, "ricambi_usati": [], "foto_b64": ""
                }
                salva_db(st.session_state.db)
                
                host = st.context.headers.get("Host", "localhost")
                url = f"https://{host}?bolla_id={new_id}"
                st.image(get_qr(url), caption=f"QR Bolla {new_id}", width=200)
                st.info(f"Link Operatore: {url}")

    with t2:
        if st.session_state.db:

st.download_button(
    label="📥 Scarica Database CSV",
    data=df.to_csv().encode('utf-8'),
    file_name='estrazione_bolle.csv',
    mime='text/csv',
)
            
            df = pd.DataFrame.from_dict(st.session_state.db, orient='index')
            df['Minuti'] = (df['tempo_sec'] // 60).astype(int)
            st.dataframe(df[['veicolo', 'tecnico', 'stato_lavoro', 'Minuti']], use_container_width=True)
            if st.button("🗑️ RESET DATABASE"):
                if os.path.exists(DB_FILE): os.remove(DB_FILE)
                st.session_state.db = {}; st.rerun()
        else:
            st.info("Nessun lavoro attivo.")

    with t3:
        if st.session_state.db:
            df_kpi = pd.DataFrame.from_dict(st.session_state.db, orient='index')
            c1, c2 = st.columns(2)
            c1.markdown("### Stato Lavori")
            c1.bar_chart(df_kpi['stato_lavoro'].value_counts())
            
            # Calcolo Exergia/Sostenibilità
            eco_count = 0
            for b in st.session_state.db.values():
                cat_tasks = CHECKLIST_DATA.get(b['categoria'], [])
                for i, t in enumerate(cat_tasks):
                    if t['eco'] and b['checklist_state'].get(f"chk_{i}"):
                        eco_count += 1
            
            c2.metric("🌱 Azioni Green Effettuate", eco_count)
            c2.markdown("### Tempi Medi (Sec)")
            c2.line_chart(df_kpi.groupby('categoria')['tempo_sec'].mean())
