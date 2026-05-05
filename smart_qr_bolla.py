import streamlit as st
import qrcode
from io import BytesIO
import pandas as pd
import datetime
import random
import os

# ==============================================================================
# 1. GESTIONE DATABASE (FILE CSV)
# ==============================================================================
DB_FILE = "database_bolle.csv"

def carica_db():
    """Carica i dati dal file CSV se esiste, altrimenti restituisce un dizionario vuoto"""
    if os.path.exists(DB_FILE):
        try:
            return pd.read_csv(DB_FILE, index_col=0).to_dict('index')
        except Exception:
            return {}
    return {}

def salva_db(db):
    """Salva il dizionario corrente nel file CSV"""
    if db:
        df = pd.DataFrame.from_dict(db, orient='index')
        df.to_csv(DB_FILE)

# Inizializzazione del database nella sessione corrente
if 'db_bolle' not in st.session_state:
    st.session_state['db_bolle'] = carica_db()

# ==============================================================================
# 2. CONFIGURAZIONI E LOGICA DI BUSINESS
# ==============================================================================
CATEGORIE = ['Motore', 'Elettronica', 'Freni', 'Cambio']
TECNICI = ['Marco', 'Luca', 'Antonio', 'Davide', 'Roberto']

# Checklist basate su dati storici per prevenire rework (Industria 5.0)
CHECKLIST_PREDITTIVE = {
    'Motore': [
        {"task": "Serraggio testata a coppia specifica", "risk": "ALTO", "info": "Rework storico: 30% per perdite olio"},
        {"task": "Controllo pressione circuito raffreddamento", "risk": "MEDIO", "info": "Previene surriscaldamento post-consegna"},
        {"task": "Verifica efficienza termica (Exergia)", "risk": "BASSO", "info": "Ottimizzazione consumi energetici"}
    ],
    'Cambio': [
        {"task": "Verifica tolleranze ingranaggi", "risk": "ALTO", "info": "Critico per evitare rumorosità"},
        {"task": "Sostituzione guarnizioni carter", "risk": "MEDIO", "info": "Prevenzione inquinamento ambientale"}
    ],
    'Freni': [
        {"task": "Spurgo aria impianto frenante", "risk": "ALTO", "info": "Sicurezza: previene frenata lunga"},
        {"task": "Misurazione spessore dischi", "risk": "ALTO", "info": "Standard sicurezza IVECO"}
    ],
    'Elettronica': [
        {"task": "Scansione errori centralina (DTC)", "risk": "MEDIO", "info": "Evita ritorno cliente per spie accese"},
        {"task": "Test isolamento cablaggi", "risk": "ALTO", "info": "Sicurezza operatore e veicolo"}
    ]
}

# ==============================================================================
# 3. FUNZIONI TECNICHE (QR & URL)
# ==============================================================================
def genera_qr_bytes(link):
    """Genera i byte dell'immagine QR per visualizzazione e download"""
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def get_base_url():
    """Identifica l'URL corretto per il QR Code"""
    host = st.context.headers.get("Host", "localhost:8501")
    protocol = "https" if "streamlit.app" in host else "http"
    return f"{protocol}://{host}"

# ==============================================================================
# 4. INTERFACCIA UTENTE (UI)
# ==============================================================================
st.set_page_config(page_title="IVECO Smart Hub 5.0", page_icon="🚚", layout="wide")

# Gestione della navigazione tramite Query Parameters (QR Code scan)
query_params = st.query_params

# --- VISTA OPERATORE (Attivata dal QR Code) ---
if 'bolla_id' in query_params:
    b_id = query_params['bolla_id']
    
    if b_id not in st.session_state['db_bolle']:
        st.error("⚠️ Bolla non trovata. Il lavoro potrebbe essere stato rimosso.")
        if st.button("Vai alla Home"):
            st.query_params.clear()
            st.rerun()
    else:
        bolla = st.session_state['db_bolle'][b_id]
        st.title(f"🛠️ Protocollo Lavoro: {bolla['veicolo']}")
        
        col_info1, col_info2 = st.columns(2)
        with col_info1:
            st.metric("ID Lavoro", b_id)
            st.write(f"**Categoria:** {bolla['categoria']}")
        with col_info2:
            st.metric("Tecnico Attuale", bolla['tecnico'])
            st.write(f"**Data Ingresso:** {bolla['data']}")

        st.subheader("📋 Checklist Intelligente Anti-Errore")
        tasks = CHECKLIST_PREDITTIVE.get(bolla['categoria'], [])
        
        for i, item in enumerate(tasks):
            color = "🔴" if item['risk'] == "ALTO" else "🟡"
            st.checkbox(f"{color} {item['task']} (Rischio: {item['risk']})", key=f"check_{b_id}_{i}")
            st.caption(f"💡 *Perché farlo? {item['info']}*")

        st.divider()
        st.subheader("🤝 Passaggio di Turno / Note")
        nuovo_tec = st.selectbox("Passa il lavoro a:", ["Mantieni attuale"] + TECNICI)
        note_op = st.text_area("Note per il prossimo tecnico / Report finale")

        if st.button("💾 AGGIORNA E SALVA", type="primary", use_container_width=True):
            if nuovo_tec != "Mantieni attuale":
                st.session_state['db_bolle'][b_id]['tecnico'] = nuovo_tec
            
            salva_db(st.session_state['db_bolle'])
            st.success("✅ Dati salvati nel database centrale!")
            st.balloons()

        if st.button("⬅️ Torna alla lista completa"):
            st.query_params.clear()
            st.rerun()

# --- VISTA MANAGER (Pagina Principale) ---
else:
    st.title("🚚 IVECO Gestione Accettazione 5.0")
    st.markdown("Generazione bolle smart con tracciabilità tramite QR Code.")

    tab1, tab2 = st.tabs(["🆕 Nuova Accettazione", "📊 Monitoraggio Officina"])

    with tab1:
        col_f, col_qr = st.columns([2, 1])
        
        with col_f:
            with st.form("form_ingresso"):
                targa = st.text_input("Targa o Modello (es. IVECO Daily AB123CD)")
                categoria = st.selectbox("Tipo di Intervento", CATEGORIE)
                tecnico_init = st.selectbox("Assegna a", TECNICI)
                note_acc = st.text_area("Sintomi riscontrati / Richiesta cliente")
                submit = st.form_submit_button("GENERA SMART BOLLA", type="primary")

        if submit and targa:
            id_gen = f"IVECO-{random.randint(1000, 9999)}"
            # Registrazione nel database
            st.session_state['db_bolle'][id_gen] = {
                "veicolo": targa,
                "categoria": categoria,
                "tecnico": tecnico_init,
                "descrizione": note_acc,
                "data": datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
            }
            salva_db(st.session_state['db_bolle'])
            
            # Generazione QR
            url_lavoro = f"{get_base_url()}?bolla_id={id_gen}"
            qr_bytes = genera_qr_bytes(url_lavoro)
            
            with col_qr:
                st.success(f"Bolla {id_gen} Creata!")
                st.image(qr_bytes, caption="QR CODE DA STAMPARE", width=250)
                st.download_button(
                    label="📥 Scarica QR per il Tecnico",
                    data=qr_bytes,
                    file_name=f"QR_{id_gen}.png",
                    mime="image/png",
                    use_container_width=True
                )
                st.info("Inquadra il QR per simulare l'accesso dell'operatore.")

    with tab2:
        if st.session_state['db_bolle']:
            df_view = pd.DataFrame.from_dict(st.session_state['db_bolle'], orient='index')
            st.subheader("Stato Avanzamento Lavori")
            st.dataframe(df_view[['veicolo', 'categoria', 'tecnico', 'data']], use_container_width=True)
            
            if st.button("🗑️ Reset Database (Attenzione: azione irreversibile)"):
                if os.path.exists(DB_FILE):
                    os.remove(DB_FILE)
                st.session_state['db_bolle'] = {}
                st.rerun()
        else:
            st.write("Nessun lavoro in corso. Inizia dalla scheda 'Nuova Accettazione'.")
