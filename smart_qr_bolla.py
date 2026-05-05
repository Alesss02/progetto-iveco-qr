import streamlit as st
import qrcode
from io import BytesIO
import pandas as pd
import datetime
import random

# ==============================================================================
# CONFIGURAZIONE INIZIALE E DATABASE SIMULATO
# ==============================================================================
st.set_page_config(page_title="Smart Bolla 5.0", page_icon="📱", layout="centered")

# Simulo un database in memoria (session_state) per le bolle e i passaggi di consegne
if 'db_bolle' not in st.session_state:
    st.session_state['db_bolle'] = {}

CATEGORIE = ['Motore', 'Elettronica', 'Freni', 'Cambio']
TECNICI = ['Marco', 'Luca', 'Antonio', 'Davide', 'Roberto']

# Il "Cervello" Predittivo: Checklist dinamiche basate sullo storico dei rework
CHECKLIST_PREDITTIVE = {
    'Motore': [
        {"task": "Serraggio testata a coppia specifica", "risk_lvl": "ALTO", "motivo": "Rework frequente (30%) - Perdita olio"},
        {"task": "Controllo guarnizioni coppa olio", "risk_lvl": "MEDIO", "motivo": "Spreco materiale"},
        {"task": "Recupero Exergia: Ottimizzazione termostato", "risk_lvl": "BASSO", "motivo": "Risparmio energetico"}
    ],
    'Cambio': [
        {"task": "Allineamento ingranaggi e verifica tolleranze", "risk_lvl": "ALTO", "motivo": "Danno critico in caso di errore"},
        {"task": "Controllo qualità e livello olio trasmissione", "risk_lvl": "MEDIO", "motivo": "Impatto ambientale"}
    ],
    'Freni': [
        {"task": "Spessore pastiglie (min. 3mm confermato)", "risk_lvl": "ALTO", "motivo": "Sicurezza veicolo"},
        {"task": "Spurgo completo liquido freni", "risk_lvl": "ALTO", "motivo": "Rework per frenata spugnosa (45% dei casi)"}
    ],
    'Elettronica': [
        {"task": "Reset memoria centralina (DTC)", "risk_lvl": "MEDIO", "motivo": "Falso allarme cliente"},
        {"task": "Test isolamento cablaggi alta tensione", "risk_lvl": "ALTO", "motivo": "Rischio sicurezza operatore"}
    ]
}

# ==============================================================================
# FUNZIONI DI SUPPORTO
# ==============================================================================
def genera_qr(link):
    """Genera l'immagine del QR code dal link fornito"""
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf

def baseUrl():
    """Recupera l'URL base dell'app Streamlit per creare il link del QR"""
    # Funziona sia in locale che deployato su Streamlit Cloud
    host = st.context.headers.get("Host", "localhost:8501")
    return f"http://{host}"

# ==============================================================================
# VISTA 2: INTERFACCIA OPERATORE (Si attiva solo se c'è ?bolla_id= nell'URL)
# ==============================================================================
if 'bolla_id' in st.query_params:
    b_id = st.query_params['bolla_id']
    
    if b_id not in st.session_state['db_bolle']:
        st.error("Bolla non trovata o scaduta.")
        if st.button("Torna alla Home"):
            st.query_params.clear()
            st.rerun()
    else:
        bolla = st.session_state['db_bolle'][b_id]
        
        # UI Mobile-Friendly per l'operatore
        st.markdown(f"## 🛠️ Lavoro: {bolla['veicolo']}")
        st.info(f"**Categoria:** {bolla['categoria']} | **Creato il:** {bolla['data']} \n\n **Operatore Attuale:** {bolla['tecnico']}")
        
        st.divider()
        st.markdown("### 📋 Smart Checklist (Prevenzione Rework)")
        st.caption("I controlli seguenti sono generati dall'AI in base agli errori storici più frequenti per questa categoria.")
        
        checklist = CHECKLIST_PREDITTIVE[bolla['categoria']]
        tutti_spuntati = True
        
        for i, item in enumerate(checklist):
            # Colori in base al rischio
            color = "🔴" if item['risk_lvl'] == "ALTO" else "🟡" if item['risk_lvl'] == "MEDIO" else "🟢"
            
            # Checkbox per ogni task
            checked = st.checkbox(f"{color} **{item['task']}**\n\n*{item['motivo']}*", key=f"chk_{b_id}_{i}")
            if not checked:
                tutti_spuntati = False

        st.divider()
        
        # Gestione Passaggio di Consegne (Handover)
        st.markdown("### 🤝 Passaggio di Consegne")
        nuovo_tecnico = st.selectbox("Se il turno finisce, a chi passi il lavoro?", ["Nessuno (Continuo io)"] + TECNICI, index=0)
        note_passaggio = st.text_area("Note per il collega (Cosa manca da fare?)")
        
        if st.button("💾 Salva Stato Lavoro", use_container_width=True, type="primary"):
            if not tutti_spuntati:
                st.warning("⚠️ Non hai spuntato tutti i controlli critici. Rischio di Rework elevato. Stato salvato comunque nel log.")
            else:
                st.success("✅ Ottimo lavoro! Protocollo qualità rispettato.")
            
            # Se c'è un passaggio di consegne, aggiorniamo il database
            if nuovo_tecnico != "Nessuno (Continuo io)":
                st.session_state['db_bolle'][b_id]['tecnico'] = nuovo_tecnico
                st.info(f"Lavoro passato a {nuovo_tecnico}. Note registrate.")
            
        if st.button("⬅️ Chiudi Scheda Lavoro", use_container_width=True):
            st.query_params.clear()
            st.rerun()

# ==============================================================================
# VISTA 1: VISTA MANAGER / ACCETTAZIONE (Default)
# ==============================================================================
else:
    st.title("🖨️ Accettazione & Generatore Bolle Smart")
    st.markdown("Inserisci i dati del veicolo per generare il protocollo di lavoro e il QR Code anticaduta-informazioni.")
    
    with st.form("form_bolla"):
        col1, col2 = st.columns(2)
        with col1:
            targa = st.text_input("Targa / Modello Veicolo (es. IVECO S-Way AB123CD)")
            categoria = st.selectbox("Categoria Lavoro", CATEGORIE)
        with col2:
            tecnico = st.selectbox("Assegna a (Tecnico Iniziale)", TECNICI)
            descrizione = st.text_area("Difetto lamentato dal cliente")
            
        submit = st.form_submit_button("Genera Smart Bolla & QR Code", type="primary")
        
    if submit and targa:
        # Creazione ID univoco
        bolla_id = f"ID-{datetime.datetime.now().strftime('%H%M%S')}-{random.randint(10,99)}"
        
        # Salvataggio nel "Database"
        st.session_state['db_bolle'][bolla_id] = {
            "veicolo": targa,
            "categoria": categoria,
            "tecnico": tecnico,
            "descrizione": descrizione,
            "data": datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
        }
        
        # Generazione Link e QR
        link_bolla = f"{baseUrl()}?bolla_id={bolla_id}"
        qr_img = genera_qr(link_bolla)
        
        st.success(f"Bolla {bolla_id} generata con successo!")
        
        st.markdown("### Stampa questo QR Code da attaccare al veicolo:")
        col_qr, col_info = st.columns([1, 2])
        
        with col_qr:
            st.image(qr_img, width=200)
        with col_info:
            st.markdown(f"**Veicolo:** {targa}")
            st.markdown(f"**Assegnato a:** {tecnico}")
            st.markdown(f"**Reparto:** {categoria}")
            st.caption("Inquadra il QR Code con il telefono per aprire la Smart Checklist.")
            
            # Bottone di simulazione per testare dal PC
            st.markdown("---")
            st.markdown(f"[Simula scansione QR Code cliccando qui]({link_bolla})")
            
    # Mostra i lavori attivi in officina
    if st.session_state['db_bolle']:
        st.divider()
        st.subheader("📋 Lavori Attivi in Officina")
        df_attivi = pd.DataFrame.from_dict(st.session_state['db_bolle'], orient='index')
        st.dataframe(df_attivi, use_container_width=True)