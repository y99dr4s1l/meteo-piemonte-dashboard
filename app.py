import streamlit as st
from datetime import datetime, timedelta
import os
from animation_creator import create_forecast_evolution_animation, create_rmse_analysis
import time

# Configurazione pagina
st.set_page_config(
    page_title="Dashboard Meteo Piemonte",
    page_icon="🌦️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizzato
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.title("🌦️ Dashboard Previsioni Meteo - Piemonte")
st.markdown("Evoluzione delle previsioni GFS per un momento target")

# Inizializza session state
if 'rmse_fig' not in st.session_state:
    st.session_state.rmse_fig = None
if 'last_generation' not in st.session_state:
    st.session_state.last_generation = None

# Sidebar con controlli
st.sidebar.header("⚙️ Configurazione")

# Data e ora target
col_date, col_hour = st.sidebar.columns(2)
with col_date:
    target_date = st.date_input(
        "Data target",
        datetime.now() + timedelta(days=1),
        min_value=datetime.now().date(),
        max_value=datetime.now().date() + timedelta(days=7)
    )
with col_hour:
    target_hour = st.selectbox("Ora (UTC)", list(range(0, 24, 3)), index=2)

# Giorni di storico
days_back = st.sidebar.slider("Giorni di storico run", 1, 7, 5)

# Selezione variabile
variable_options = {
    "🌡️ Geopotenziale 500hPa": ("HGT", "500_mb"),
    "🌧️ Precipitazione": ("APCP", "surface"),
    "🌡️ Temperatura 850hPa": ("TMP", "850_mb"),
    "💨 Temperatura 500hPa": ("TMP", "500_mb")
}

selected_var = st.sidebar.selectbox("Variabile meteorologica", list(variable_options.keys()))
var_code, level = variable_options[selected_var]

st.sidebar.markdown("---")

# Pulsante di aggiornamento
update_button = st.sidebar.button("🔄 Genera Animazione", type="primary", use_container_width=True)

# Info sidebar
with st.sidebar.expander("ℹ️ Come funziona"):
    st.markdown("""
    Questa dashboard mostra come evolve la previsione meteorologica 
    per un momento specifico nel tempo.
    
    **Cosa vedi:**
    - Ogni frame = una run GFS diversa
    - Le run più vecchie sono meno accurate
    - Osserva la convergenza verso il momento target
    
    **Fonte dati:** NOAA GFS 0.25°
    """)

with st.sidebar.expander("📖 Legenda Variabili"):
    st.markdown("""
    - **Geopotenziale 500hPa**: Altezza della superficie isobarica, 
      indica zone di alta/bassa pressione in quota
    - **Precipitazione**: Accumulo previsto
    - **Temperatura 850/500hPa**: Temperatura a diverse quote
    """)

# Main content area
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    st.metric(
        "🎯 Target", 
        f"{target_date.strftime('%d/%m/%Y')}",
        f"{target_hour:02d}:00 UTC"
    )

with col2:
    st.metric(
        "📅 Storico Run", 
        f"{days_back} giorni",
        f"~{days_back * 4} previsioni"
    )

with col3:
    st.metric(
        "🌍 Area", 
        "Piemonte",
        selected_var.split()[1] if len(selected_var.split()) > 1 else ""
    )

st.markdown("---")

# Area principale per la GIF
gif_path = 'current_forecast.gif'

if update_button:
    # Combina data e ora
    target = datetime.combine(target_date, datetime.min.time())
    target = target.replace(hour=target_hour)
    
    # Progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    status_text.text("⏳ Preparazione download...")
    progress_bar.progress(10)
    
    with st.spinner("🌐 Scaricamento dati GFS in corso..."):
        try:
            # Crea l'animazione
            status_text.text("📥 Download run GFS...")
            progress_bar.progress(30)
            
            # MODIFICA: Ora la funzione restituisce sia anim che datasets
            anim, datasets = create_forecast_evolution_animation(
                target_time=target,
                days_back=days_back,
                variable=var_code,
                level=level,
                output_file=gif_path
            )
            
            progress_bar.progress(70)
            status_text.text("📊 Generazione analisi RMSE...")
            
            # Crea il plot RMSE e salvalo in session state
            st.session_state.rmse_fig = create_rmse_analysis(
                datasets=datasets,
                target_time=target,
                variable_name=var_code
            )
            
            # Salva timestamp generazione
            st.session_state.last_generation = datetime.now()
            
            progress_bar.progress(90)
            status_text.text("✅ Generazione completata!")
            time.sleep(1)
            
            progress_bar.progress(100)
            status_text.empty()
            progress_bar.empty()
            
            st.success("✅ Animazione e analisi generate con successo!")
            st.balloons()
            
        except Exception as e:
            st.error(f"❌ Errore durante la generazione: {str(e)}")
            st.exception(e)

# Visualizza la GIF
st.subheader("📊 Evoluzione della Previsione")

if os.path.exists(gif_path):
    # Mostra la GIF
    col_gif, col_info = st.columns([2, 1])
    
    with col_gif:
        st.image(gif_path, width='stretch')
    
    with col_info:
        st.info("""
        **💡 Come interpretare:**
        
        - I frame procedono cronologicamente
        - Le previsioni più recenti sono più affidabili
        - Cerca pattern ricorrenti tra le diverse run
        - La convergenza indica maggiore certezza
        """)
        
        # Info sul file
        file_size = os.path.getsize(gif_path) / 1024  # KB
        st.caption(f"Dimensione file: {file_size:.1f} KB")
        
        # Info ultima generazione
        if st.session_state.last_generation:
            st.caption(f"Ultima generazione: {st.session_state.last_generation.strftime('%H:%M:%S')}")
        
        # Download button
        with open(gif_path, 'rb') as f:
            st.download_button(
                label="⬇️ Scarica GIF",
                data=f,
                file_name=f"previsione_{target_date}_{var_code}.gif",
                mime="image/gif"
            )
    
    # SEZIONE AGGIUNTA: Visualizza analisi RMSE
    st.markdown("---")
    st.subheader("📈 Analisi Evoluzione Previsioni")
    
    # MODIFICA: Usa session state invece di variabile locale
    if st.session_state.rmse_fig is not None:
        st.pyplot(st.session_state.rmse_fig)
        
        col_rmse1, col_rmse2 = st.columns(2)
        
        with col_rmse1:
            st.markdown("""
            **📊 Interpretazione RMSE:**
            - **Valori alti**: Maggiore discrepanza con l'ultima previsione
            - **Valori bassi**: Maggiore accordo con l'ultima previsione
            - **Trend decrescente**: Previsioni che convergono nel tempo
            """)
        
        with col_rmse2:
            st.markdown("""
            **🎯 Cosa osservare:**
            - La linea rossa indica l'ultimo run (riferimento)
            - Run più vecchi dovrebbero avere RMSE più alti
            - Convergenza verso RMSE basso indica stabilità
            """)
    else:
        st.warning("Analisi RMSE non disponibile. Rigenera l'animazione.")
        
else:
    st.info("👆 Clicca su 'Genera Animazione' per creare la visualizzazione")
    
    # Esempio placeholder
    st.image("https://via.placeholder.com/800x600.png?text=In+attesa+di+generare+animazione", 
             use_container_width=True)

# Footer
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #666;'>
        <small>
        Dashboard Meteo Piemonte | Dati: NOAA GFS | 
        Aggiornato: {}
        </small>
    </div>
""".format(datetime.now().strftime("%Y-%m-%d %H:%M UTC")), unsafe_allow_html=True)
