import streamlit as st
import qrcode
from io import BytesIO
import pandas as pd
import datetime
import random
import os

# ==============================================================================
# CONFIGURAZIONE DATABASE PERSISTENTE
# ==============================================================================
DB_FILE = "database_bolle.csv"

def carica_db():
    if os.path.exists(DB_FILE):
        try:
            return pd.read_csv(DB_FILE, index_col=0).to_dict('index')
        except:
            return {}
    return {}

def salva_db(db):
    if db:
        df = pd.DataFrame.from_dict(db, orient='index')
        df.to_csv(DB_FILE)

# Inizializzazione database nello stato della sessione
if 'db_bolle' not in st.session_state:
    st.session_state['db_bolle'] = carica_db()

# ==============================================================================
# COSTANTI E LOGICA PREDITTIVA
# ==============================================================================
CATEGORIE = ['Motore', 'Elettronica', 'Freni', 'Cambio']
TECNICI = ['Marco', 'Luca', 'Antonio', 'Davide', 'Roberto']

CHECKLIST_PREDITTIVE = {
    'Motore': [
        {"task": "Serraggio testata a coppia specifica", "risk_lvl": "ALTO", "motivo": "Prevenzione perdite olio (Rework storico 30%)"},
        {"task": "Verifica integrità guarnizioni", "risk_lvl": "MEDIO", "motivo": "Riduzione scarti materiali"},
        {"task": "Ottimizzazione parametri termici", "risk_lvl": "BASSO", "motivo": "Risparmio Exergia/Energia"}
    ],
    'Cambio': [
        {"task": "Allineamento meccanico ingranaggi", "risk_lvl": "ALTO", "motivo": "Criticità rottura componenti"},
        {"task": "Controllo livello fluido trasmissione", "risk_lvl": "MEDIO", "motivo": "Impatto ambientale (LCA)"}
    ],
    'Freni': [
        {"task": "Misurazione spessore dischi/pastiglie", "risk_lvl": "ALTO", "motivo": "Sicurezza stradale"},
        {"task": "Spurgo aria impianto frenante", "risk_lvl": "ALTO", "motivo": "Prevenzione 'pedale spugnoso'"}
    ],
    'Elettronica': [
        {"task": "Diagnosi errori memoria DTC", "risk_lvl": "MEDIO", "motivo": "Evitare ritorni in officina"},
        {"task": "Controllo cablaggi e connettori", "risk_lvl": "ALTO", "motivo": "Prevenzione cortocircuiti"}
    ]
}

# ==============================================================================
# FUNZIONI UTILI
# ==============================================================================
def genera_qr(link):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf

def get_base_url():
    # Gestisce automaticamente l'URL sia in locale che su Streamlit Cloud
    host = st.context.headers.get("Host", "localhost:8501")
    protocol = "https" if "streamlit.app" in host else "http"
    return f"{protocol}://{host}"

# ==============================================================================
# INTERFACCIA UTENTE (UI)
# ==============================================================================
st.set_page_config(page_title="Smart Bolla IVECO 5.0", page_icon="🧬", layout="wide")

# CONTROLLO ROUTING: Se l'URL contiene bolla_id, mostra la vista OPERATORE
query_params = st.query_params

if 'bolla_id' in query_params:
    b_id = query_params['bolla_id']
    
    if b_id not in st.session_state['db_bolle']:
        st.error("⚠️ Errore: Bolla non trovata nel database.")
        if st.button("Torna alla Gestione"):
            st.query_params.clear()
            st.rerun()
    else:
        bolla = st.session_state['db_bolle'][b_id]
        
        st.markdown(f"# 🛠️ Scheda Lavoro: {bolla['veicolo']}")
        st.info(f"**ID:** {b_id} | **Tecnico Assegnato:** {bolla['tecnico']}")
        
        with st.expander("📝 Descrizione Guasto"):
            st.write(bolla['descrizione'])

        st.subheader("📋 Checklist Qualità Obbligatoria")
        st.caption("Eseguire i controlli per validare il lavoro e prevenire sprechi.")
        
        tasks = CHECKLIST_PREDITTIVE.get(bolla['categoria'], [])
        completato = True
        for i, item in enumerate(tasks):
            icon = "🔴" if item['risk_lvl'] == "ALTO" else "🟡"
            chk = st.checkbox(f"{icon} **{item['task']}** (Rischio: {item['risk_lvl']})", key=f"t_{b_id}_{i}")
            st.caption(f"_{item['motivo']}_")
            if not chk: completato = False

        st.divider()
        st.subheader("🤝 Passaggio di Consegne")
        nuovo_t = st.selectbox("Cambia Tecnico (Handover):", ["Nessuno"] + TECNICI)
        note = st.text_area("Note di avanzamento per il collega:")

        if st.button("💾 Salva e Aggiorna Stato", type="primary", use_container_width=True):
            if completato:
                st.success("✅ Protocollo qualità completato correttamente.")
            else:
                st.warning("⚠️ Stato salvato con controlli incompleti. Rischio Rework!")
            
            if nuovo_t != "Nessuno":
                st.session_state['db_bolle'][b_id]['tecnico'] = nuovo_t
            
            salva_db(st.session_state['db_bolle'])
            st.balloons()

        if st.button("🏠 Torna all'Accettazione"):
            st.query_params.clear()
            st.rerun()

# VISTA MANAGER (Default)
else:
    st.title("🖨️ Centro Accettazione Smart Bolla")
    st.markdown("Gestione flussi di lavoro e tracciabilità digitale per l'officina sostenibile.")

    col_form, col_lista = st.columns([1, 1])

    with col_form:
        st.subheader("🆕 Crea Nuova Bolla")
        with st.form("nuova_bolla"):
            targa = st.text_input("Targa o Modello Veicolo", placeholder="Es: IVECO S-WAY - AA123BB")
            cat = st.selectbox("Categoria Intervento", CATEGORIE)
            tec = st.selectbox("Tecnico Responsabile", TECNICI)
            desc = st.text_area("Note Accettazione / Sintomi")
            crea = st.form_submit_button("Genera Bolla e QR Code", type="primary")

        if crea and targa:
            id_lavoro = f"B{random.randint(1000, 9999)}"
            # Salvataggio
            st.session_state['db_bolle'][id_lavoro] = {
                "veicolo": targa, "categoria": cat, "tecnico": tec, 
                "descrizione": desc, "data": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            salva_db(st.session_state['db_bolle'])
            
            # Link e QR
            url_lavoro = f"{get_base_url()}?bolla_id={id_lavoro}"
            img_qr = genera_qr(url_lavoro)
            
            st.success(f"Bolla {id_lavoro} creata!")
            st.image(img_qr, caption=f"QR Code per {targa}", width=250)
            st.markdown(f"**Link diretto (da copiare se non puoi usare il cellulare):** [Clicca qui]({url_lavoro})")

    with col_lista:
        st.subheader("📋 Lavori in corso")
        if st.session_state['db_bolle']:
            df = pd.DataFrame.from_dict(st.session_state['db_bolle'], orient='index')
            st.dataframe(df[['veicolo', 'categoria', 'tecnico', 'data']], use_container_width=True)
            if st.button("🗑️ Svuota Database (Reset)"):
                if os.path.exists(DB_FILE): os.remove(DB_FILE)
                st.session_state['db_bolle'] = {}
                st.rerun()
        else:
            st.info("Nessun lavoro attivo al momento.")