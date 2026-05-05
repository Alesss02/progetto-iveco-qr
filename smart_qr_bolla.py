import streamlit as st
import qrcode
from io import BytesIO
import pandas as pd
import datetime
import time
import random
import os
import ast
import base64
from PIL import Image

# ==============================================================================
# 1. GESTIONE DATABASE E IMMAGINI
# ==============================================================================
DB_FILE = "database_bolle.csv"

def carica_db():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE, index_col=0)
            db_dict = df.to_dict('index')
            # Riconversione stringhe in oggetti complessi (liste, dizionari)
            for k, v in db_dict.items():
                if isinstance(v.get('checklist_state'), str):
                    try: v['checklist_state'] = ast.literal_eval(v['checklist_state'])
                    except: v['checklist_state'] = {}
                if isinstance(v.get('ricambi_usati'), str):
                    try: v['ricambi_usati'] = ast.literal_eval(v['ricambi_usati'])
                    except: v['ricambi_usati'] = []
            return db_dict
        except Exception as e:
            st.error(f"Errore caricamento DB: {e}")
            return {}
    return {}

def salva_db(db):
    if db:
        df = pd.DataFrame.from_dict(db, orient='index')
        df.to_csv(DB_FILE)

if 'db_bolle' not in st.session_state:
    st.session_state['db_bolle'] = carica_db()

def comprimi_e_codifica_immagine(upload):
    """Comprime la foto scattata e la converte in testo per salvarla nel CSV"""
    img = Image.open(upload)
    img.thumbnail((600, 600)) # Ridimensionamento per evitare CSV troppo pesanti
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")

# ==============================================================================
# 2. CONFIGURAZIONI & LOGICA BUSINESS
# ==============================================================================
CATEGORIE = ['Motore', 'Elettronica', 'Freni', 'Cambio']
TECNICI = ['Marco', 'Luca', 'Antonio', 'Davide', 'Roberto']
CATALOGO_RICAMBI = [
    "Olio Motore 5W30 (Litri)", "Filtro Olio", "Guarnizione Testata", 
    "Pasticche Freni Ant.", "Pasticche Freni Post.", "Sensore NOx", 
    "Cinghia Distribuzione", "Liquido Radiatore", "Cablaggio Alta Tensione"
]

# Aggiunto il parametro 'is_eco' per calcolare le statistiche di Exergia/Sostenibilità
CHECKLIST_PREDITTIVE = {
    'Motore': [
        {"task": "Serraggio testata a coppia specifica", "risk": "ALTO", "info": "Rework: 30%", "is_eco": False},
        {"task": "Verifica efficienza termica (Exergia)", "risk": "BASSO", "info": "Ottimizzazione consumi", "is_eco": True}
    ],
    'Cambio': [
        {"task": "Verifica tolleranze ingranaggi", "risk": "ALTO", "info": "Critico", "is_eco": False},
        {"task": "Recupero fluido trasmissione esausto", "risk": "MEDIO", "info": "LCA / Ambiente", "is_eco": True}
    ],
    'Freni': [
        {"task": "Misurazione spessore dischi", "risk": "ALTO", "info": "Sicurezza", "is_eco": False},
        {"task": "Smaltimento corretto polveri frenanti", "risk": "MEDIO", "info": "Salute e Sicurezza", "is_eco": True}
    ],
    'Elettronica': [
        {"task": "Scansione errori centralina (DTC)", "risk": "MEDIO", "info": "Evita ritorno", "is_eco": False},
        {"task": "Calibrazione sensori per risparmio carburante", "risk": "BASSO", "info": "Risparmio energetico", "is_eco": True}
    ]
}

# ==============================================================================
# 3. INTERFACCIA UTENTE E ROUTING
# ==============================================================================
st.set_page_config(page_title="IVECO Smart Hub 5.0", page_icon="🏭", layout="wide")

query_params = st.query_params

# ------------------------------------------------------------------------------
# VISTA 1: INTERFACCIA OPERATORE (QR CODE)
# ------------------------------------------------------------------------------
if 'bolla_id' in query_params:
    b_id = query_params['bolla_id']
    
    if b_id not in st.session_state['db_bolle']:
        st.error("⚠️ Bolla non trovata.")
        if st.button("Torna alla Home"): st.query_params.clear(); st.rerun()
    else:
        bolla = st.session_state['db_bolle'][b_id]
        
        # Gestione sicurezza campi vecchi
        for field in ['checklist_state', 'ricambi_usati']:
            if field not in bolla: bolla[field] = {} if field == 'checklist_state' else []
        for field in ['storico_note', 'foto_b64']:
            if field not in bolla: bolla[field] = ""
        for field in ['tempo_sec', 'inizio_timestamp']:
            if field not in bolla: bolla[field] = 0.0
        if 'stato_lavoro' not in bolla: bolla['stato_lavoro'] = "In Attesa"

        st.title(f"🛠️ Intervento: {bolla['veicolo']}")
        
        # TIMBRATURA E STATO LAVORO (Miglioria 1)
        st.subheader("⏱️ Log Attività")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.metric("Stato Attuale", bolla['stato_lavoro'])
        with col_t2:
            minuti_lavorati = int(bolla['tempo_sec'] // 60)
            st.metric("Tempo Registrato (Minuti)", minuti_lavorati)

        if bolla['stato_lavoro'] in ["In Attesa", "Sospeso"]:
            if st.button("▶️ INIZIA / RIPRENDI LAVORO", type="primary", use_container_width=True):
                bolla['inizio_timestamp'] = time.time()
                bolla['stato_lavoro'] = "In Corso"
                salva_db(st.session_state['db_bolle'])
                st.rerun()
        elif bolla['stato_lavoro'] == "In Corso":
            st.warning("🔄 Lavoro attualmente in esecuzione...")
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("⏸️ SOSPENDI (Pausa/Fine Turno)", use_container_width=True):
                    delta = time.time() - bolla['inizio_timestamp']
                    bolla['tempo_sec'] += delta
                    bolla['stato_lavoro'] = "Sospeso"
                    salva_db(st.session_state['db_bolle'])
                    st.rerun()
            with col_b2:
                if st.button("✅ COMPLETA INTERVENTO", type="primary", use_container_width=True):
                    delta = time.time() - bolla['inizio_timestamp']
                    bolla['tempo_sec'] += delta
                    bolla['stato_lavoro'] = "Completato"
                    salva_db(st.session_state['db_bolle'])
                    st.rerun()

        st.divider()

        # NOTE PRECEDENTI
        if bolla['storico_note']:
            st.warning(f"📝 **NOTE DAI COLLEGHI:**\n{bolla['storico_note']}")

        # EVIDENZA DIGITALE / FOTO (Miglioria 2)
        st.subheader("📸 Evidenza Digitale Guasto")
        if bolla['foto_b64']:
            img_bytes = base64.b64decode(bolla['foto_b64'])
            st.image(img_bytes, caption="Foto allegata all'intervento", width=300)
            if st.button("🗑️ Rimuovi Foto"):
                bolla['foto_b64'] = ""
                salva_db(st.session_state['db_bolle'])
                st.rerun()
        else:
            foto_upload = st.file_uploader("Scatta o carica una foto del componente", type=['jpg', 'jpeg', 'png'])
            if foto_upload:
                bolla['foto_b64'] = comprimi_e_codifica_immagine(foto_upload)
                salva_db(st.session_state['db_bolle'])
                st.rerun()

        st.divider()

        # RICAMBI MAGAZZINO (Miglioria 3)
        st.subheader("📦 Magazzino e Ricambi")
        ricambi_selezionati = st.multiselect(
            "Seleziona i ricambi utilizzati in questo intervento:", 
            options=CATALOGO_RICAMBI, 
            default=bolla['ricambi_usati']
        )
        bolla['ricambi_usati'] = ricambi_selezionati

        st.divider()

        # CHECKLIST PREDITTIVA
        st.subheader("📋 Checklist Qualità")
        tasks = CHECKLIST_PREDITTIVE.get(bolla['categoria'], [])
        for i, item in enumerate(tasks):
            is_checked = bolla['checklist_state'].get(str(i), False)
            chk = st.checkbox(f"{item['task']} (Rischio: {item['risk']})", value=is_checked, key=f"c_{b_id}_{i}")
            bolla['checklist_state'][str(i)] = chk
            st.caption(f"_{item['info']}_")

        st.divider()

        # HANDOVER E SALVATAGGIO
        nuovo_tec = st.selectbox("Passa lavoro a (Handover):", ["Mantieni attuale"] + TECNICI)
        note_op = st.text_area("Aggiungi note per il prossimo turno:", value=bolla['storico_note'])

        if st.button("💾 AGGIORNA DATI E SALVA", type="primary", use_container_width=True):
            if nuovo_tec != "Mantieni attuale": bolla['tecnico'] = nuovo_tec
            bolla['storico_note'] = note_op
            salva_db(st.session_state['db_bolle'])
            st.success("Dati aggiornati con successo!")
            st.rerun()

        if st.button("⬅️ Chiudi Scheda"):
            st.query_params.clear(); st.rerun()


# ------------------------------------------------------------------------------
# VISTA 2: CRUSCOTTO MANAGER (PC)
# ------------------------------------------------------------------------------
else:
    st.title("🚚 IVECO Managerial Hub 5.0")
    
    tab1, tab2, tab3 = st.tabs(["🆕 Accettazione", "📊 Lavori Attivi", "📈 Cruscotto KPI 5.0"])

    # --- TAB 1: CREAZIONE BOLLA ---
    with tab1:
        col_f, col_qr = st.columns([2, 1])
        with col_f:
            with st.form("form_ingresso"):
                targa = st.text_input("Targa / Modello")
                categoria = st.selectbox("Categoria", CATEGORIE)
                tecnico_init = st.selectbox("Tecnico", TECNICI)
                note_acc = st.text_area("Note Iniziali")
                submit = st.form_submit_button("Genera Bolla e QR", type="primary")

        if submit and targa:
            id_gen = f"ID-{random.randint(1000, 9999)}"
            st.session_state['db_bolle'][id_gen] = {
                "veicolo": targa, "categoria": categoria, "tecnico": tecnico_init,
                "descrizione": note_acc, "data": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                "checklist_state": {}, "ricambi_usati": [], "storico_note": note_acc,
                "foto_b64": "", "stato_lavoro": "In Attesa", "tempo_sec": 0.0, "inizio_timestamp": 0.0
            }
            salva_db(st.session_state['db_bolle'])
            
            host = st.context.headers.get("Host", "localhost:8501")
            prot = "https" if "streamlit.app" in host else "http"
            url_lavoro = f"{prot}://{host}?bolla_id={id_gen}"
            
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(url_lavoro); qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = BytesIO(); img.save(buf, format="PNG")
            
            with col_qr:
                st.success("Bolla Creata!")
                st.image(buf.getvalue(), width=200)
                st.download_button("📥 Scarica QR", data=buf.getvalue(), file_name=f"QR_{id_gen}.png", mime="image/png")

    # --- TAB 2: MONITORAGGIO ---
    with tab2:
        if st.session_state['db_bolle']:
            df_view = pd.DataFrame.from_dict(st.session_state['db_bolle'], orient='index')
            df_view['Minuti Lavorati'] = (df_view['tempo_sec'] // 60).astype(int)
            colonne_visibili = ['veicolo', 'categoria', 'tecnico', 'stato_lavoro', 'Minuti Lavorati']
            st.dataframe(df_view[colonne_visibili], use_container_width=True)
            
            if st.button("🗑️ Svuota Database"):
                if os.path.exists(DB_FILE): os.remove(DB_FILE)
                st.session_state['db_bolle'] = {}
                st.rerun()
        else:
            st.info("Nessun lavoro nel database.")

    # --- TAB 3: CRUSCOTTO ANALITICO KPI 5.0 (Miglioria 5) ---
    with tab3:
        st.markdown("### 🏭 Analisi delle Performance e Sostenibilità")
        if not st.session_state['db_bolle']:
            st.warning("Non ci sono dati sufficienti per generare le statistiche. Crea qualche bolla e simulane l'avanzamento.")
        else:
            df_kpi = pd.DataFrame.from_dict(st.session_state['db_bolle'], orient='index')
            df_kpi['Minuti'] = df_kpi['tempo_sec'] / 60.0

            col_k1, col_k2, col_k3 = st.columns(3)
            
            # Calcolo KPI
            tot_lavori = len(df_kpi)
            completati = len(df_kpi[df_kpi['stato_lavoro'] == 'Completato'])
            
            # Calcolo Azioni Sostenibili (Exergia) effettuate
            azioni_eco_totali = 0
            for b_id, data in st.session_state['db_bolle'].items():
                cat = data.get('categoria', '')
                tasks = CHECKLIST_PREDITTIVE.get(cat, [])
                for i, t in enumerate(tasks):
                    if t['is_eco'] and data.get('checklist_state', {}).get(str(i), False):
                        azioni_eco_totali += 1

            col_k1.metric("Totale Interventi", tot_lavori)
            col_k2.metric("Interventi Completati", completati)
            col_k3.metric("🌱 Azioni Exergia/Eco Applicate", azioni_eco_totali, help="Numero di controlli eseguiti mirati all'ottimizzazione energetica o ambientale.")

            st.divider()
            
            col_c1, col_c2 = st.columns(2)
            
            with col_c1:
                st.markdown("**Tempo Medio per Categoria (Minuti)**")
                if df_kpi['Minuti'].sum() > 0:
                    tempo_cat = df_kpi.groupby('categoria')['Minuti'].mean()
                    st.bar_chart(tempo_cat)
                else:
                    st.info("Nessun tempo registrato ancora. Premi 'Inizia Lavoro' e 'Sospendi' su una bolla per vedere i dati.")

            with col_c2:
                st.markdown("**Stato Avanzamento Globale**")
                stato_counts = df_kpi['stato_lavoro'].value_counts()
                st.bar_chart(stato_counts, color="#ffaa00")

            st.markdown("**Classifica Ricambi Più Utilizzati**")
            tutti_ricambi = []
            for r_list in df_kpi['ricambi_usati']:
                if isinstance(r_list, list): tutti_ricambi.extend(r_list)
            
            if tutti_ricambi:
                df_ricambi = pd.Series(tutti_ricambi).value_counts()
                st.bar_chart(df_ricambi, color="#00aa44")
            else:
                st.info("Nessun ricambio ancora utilizzato negli interventi.")
