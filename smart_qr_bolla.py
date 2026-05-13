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
# 1. CONFIGURAZIONI E LOGICA BUSINESS
# ==============================================================================
DB_FILE = "database_bolle.csv"
CATEGORIE = ['Motore', 'Elettronica', 'Freni', 'Cambio']
TECNICI = ['Marco', 'Luca', 'Antonio', 'Davide', 'Roberto']
RICAMBI_CATALOGO = ["Olio 5W30", "Filtro Aria", "Pasticche Freni", "Cinghia", "Sensore NOx"]

CHECKLIST_DATA = {
    'Motore': [
        {"task": "Serraggio Testata coppia specifica", "risk": "ALTO", "eco": False},
        {"task": "Verifica Efficienza Termica", "risk": "BASSO", "eco": True}
    ],
    'Cambio': [
        {"task": "Tolleranze Ingranaggi", "risk": "ALTO", "eco": False},
        {"task": "Recupero Olio Trasmissione", "risk": "MEDIO", "eco": True}
    ],
    'Freni': [
        {"task": "Misurazione Spessore Dischi", "risk": "ALTO", "eco": False},
        {"task": "Spurgo Impianto", "risk": "ALTO", "eco": False}
    ],
    'Elettronica': [
        {"task": "Scansione Errori DTC", "risk": "MEDIO", "eco": False},
        {"task": "Reset Parametri Adattativi", "risk": "BASSO", "eco": True}
    ]
}

# ==============================================================================
# 2. GESTIONE DATI E DATABASE (SISTEMA ANTI-CRASH)
# ==============================================================================
def safe_eval(val, default):
    """Converte stringhe in oggetti Python senza mandare l'app in crash."""
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
        # Riempiamo i vuoti per evitare errori di tipo (NaN)
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

if 'db' not in st.session_state:
    st.session_state.db = carica_db()

# ==============================================================================
# 3. UTILITY FUNZIONALI
# ==============================================================================
def encode_img(upload):
    img = Image.open(upload)
    img.thumbnail((600, 600)) # Compressione per non appesantire il DB
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
st.set_page_config(page_title="IVECO Smart Hub 5.0", layout="wide", page_icon="🚚")

# Routing: Verifica se siamo Operatore (da QR) o Manager
params = st.query_params
b_id = params.get("bolla_id")

# --- VISTA OPERATORE (MOBILE OPTIMIZED) ---
if b_id:
    if b_id not in st.session_state.db:
        st.error("⚠️ Bolla non trovata. Scansiona un QR valido.")
        if st.button("Torna alla Home"): st.query_params.clear(); st.rerun()
    else:
        bolla = st.session_state.db[b_id]
        st.title(f"🛠️ {bolla['veicolo']}")
        st.caption(f"ID Bolla: {b_id} | Categoria: {bolla['categoria']}")
        
        # ⏱️ Sezione Tempi
        c1, c2 = st.columns(2)
        c1.metric("Stato Attuale", bolla['stato_lavoro'])
        minuti = int(bolla.get('tempo_sec', 0) // 60)
        c2.metric("Minuti Lavorati", minuti)
        
        if bolla['stato_lavoro'] != "Completato":
            if bolla['stato_lavoro'] == "In Corso":
                if st.button("⏸️ SOSPENDI / COMPLETA", type="primary", use_container_width=True):
                    # Calcolo tempo trascorso dall'ultimo avvio
                    delta = time.time() - bolla.get('last_start', time.time())
                    bolla['tempo_sec'] = bolla.get('tempo_sec', 0) + delta
                    bolla['stato_lavoro'] = "Completato"
                    salva_db(st.session_state.db); st.rerun()
            else:
                if st.button("▶️ INIZIA INTERVENTO", type="primary", use_container_width=True):
                    bolla['last_start'] = time.time()
                    bolla['stato_lavoro'] = "In Corso"
                    salva_db(st.session_state.db); st.rerun()

        st.divider()

        # 📸 Sezione Foto
        st.subheader("📸 Evidenza Fotografica")
        foto_data = bolla.get('foto_b64', "")
        if isinstance(foto_data, str) and len(foto_data) > 20:
            st.image(base64.b64decode(foto_data), caption="Foto Guasto/Riparazione", use_container_width=True)
            if st.button("🗑️ Elimina e Scatta Nuova"):
                bolla['foto_b64'] = ""; salva_db(st.session_state.db); st.rerun()
        else:
            up = st.file_uploader("Carica foto dell'intervento", type=['jpg', 'png'])
            if up:
                bolla['foto_b64'] = encode_img(up)
                salva_db(st.session_state.db); st.rerun()

        st.divider()

        # 📋 Checklist e Magazzino
        st.subheader("📋 Controllo Qualità e Ricambi")
        tasks = CHECKLIST_DATA.get(bolla['categoria'], [])
        for i, t in enumerate(tasks):
            key = f"chk_{i}"
            is_done = bolla['checklist_state'].get(key, False)
            bolla['checklist_state'][key] = st.checkbox(f"{t['task']} ({t['risk']})", value=is_done)
        
        st.write("")
        bolla['ricambi_usati'] = st.multiselect("Ricambi Utilizzati", RICAMBI_CATALOGO, default=bolla.get('ricambi_usati', []))

        if st.button("💾 SALVA AVANZAMENTO", use_container_width=True):
            salva_db(st.session_state.db)
            st.success("Dati sincronizzati correttamente!")

# --- VISTA MANAGER (DESKTOP OPTIMIZED) ---
else:
    st.title("🚚 IVECO Managerial Hub 5.0")
    t1, t2, t3 = st.tabs(["🆕 Nuova Accettazione", "📊 Stato Officina", "📈 Analisi KPI"])

    with t1:
        st.subheader("Creazione Bolla di Lavoro")
        with st.form("nuova_bolla"):
            v = st.text_input("Targa Veicolo / Modello")
            c = st.selectbox("Area Intervento", CATEGORIE)
            t = st.selectbox("Tecnico Assegnato", TECNICI)
            submit = st.form_submit_button("GENERA QR CODE")
            
        if submit and v:
            new_id = f"IV-{random.randint(1000, 9999)}"
            st.session_state.db[new_id] = {
                "veicolo": v, "categoria": c, "tecnico": t, "stato_lavoro": "In Attesa",
                "tempo_sec": 0.0, "checklist_state": {}, "ricambi_usati": [], "foto_b64": ""
            }
            salva_db(st.session_state.db)
            
            # Generazione link QR
            host = st.context.headers.get("Host", "localhost")
            url = f"https://{host}?bolla_id={new_id}"
            
            c_qr1, c_qr2 = st.columns([1, 2])
            with c_qr1:
                st.image(get_qr(url), caption=f"QR per {v}")
            with c_qr2:
                st.success(f"Bolla {new_id} registrata!")
                st.code(url, language=None)
                st.info("Stampa il QR o invia il link al tecnico.")

    with t2:
        st.subheader("Monitoraggio Lavori in Tempo Reale")
        if st.session_state.db:
            df = pd.DataFrame.from_dict(st.session_state.db, orient='index')
            # Calcolo minuti al volo per la tabella
            df['Minuti'] = (df['tempo_sec'].fillna(0) // 60).astype(int)
            
            st.dataframe(df[['veicolo', 'categoria', 'tecnico', 'stato_lavoro', 'Minuti']], use_container_width=True)
            
            # Pulsantiera di gestione
            c_down, c_reset = st.columns(2)
            with c_down:
                st.download_button(
                    label="📥 Scarica Database (CSV)",
                    data=df.to_csv().encode('utf-8'),
                    file_name=f'report_iveco_{datetime.datetime.now().strftime("%Y%m%d")}.csv',
                    mime='text/csv'
                )
            with c_reset:
                if st.button("🗑️ RESET TOTALE DATABASE", help="ATTENZIONE: Azione irreversibile"):
                    if os.path.exists(DB_FILE): os.remove(DB_FILE)
                    st.session_state.db = {}
                    st.rerun()
        else:
            st.info("Nessuna bolla presente nel database.")

    with t3:
        st.subheader("Performance e Sostenibilità")
        if st.session_state.db:
            df_kpi = pd.DataFrame.from_dict(st.session_state.db, orient='index')
            
            col_k1, col_k2 = st.columns(2)
            with col_k1:
                st.write("**Carico di lavoro per Stato**")
                st.bar_chart(df_kpi['stato_lavoro'].value_counts())
            
            with col_k2:
                # Calcolo azioni "Green" (Exergia)
                eco_azioni = 0
                for b in st.session_state.db.values():
                    c_tasks = CHECKLIST_DATA.get(b['categoria'], [])
                    for i, task_info in enumerate(c_tasks):
                        if task_info['eco'] and b['checklist_state'].get(f"chk_{i}"):
                            eco_azioni += 1
                
                st.metric("🌱 Azioni Green Completate", eco_azioni)
                st.write("**Tempo medio per Categoria (sec)**")
                st.line_chart(df_kpi.groupby('categoria')['tempo_sec'].mean())
