from datetime import datetime, timedelta
import xarray as xr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import geopandas as gpd
import numpy as np
from gfs_downloader import download_gfs_for_target
import sys
import pandas as pd

def create_forecast_evolution_animation(target_time, days_back=5, variable='HGT', 
                                       level='500_mb', output_file='current_forecast.gif'):
    """Crea animazione evoluzione previsione per un'ora target fissata"""
    
    print("="*60)
    print("INIZIO CREAZIONE ANIMAZIONE")
    print(f"Target: {target_time}")
    print(f"Variable: {variable}, Level: {level}")
    print(f"Days back: {days_back}")
    print("="*60)
    sys.stdout.flush()
    
    try:
        # Scarica confini Piemonte
        print("\n[1/5] 📥 Caricamento confini Piemonte...")
        sys.stdout.flush()
        url = "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_ITA_1.json"
        italy_regions = gpd.read_file(url)
        piemonte = italy_regions[italy_regions['NAME_1'] == 'Piemonte']
        print(f"✓ Confini caricati: {len(piemonte)} geometrie")
        sys.stdout.flush()
    except Exception as e:
        print(f"✗ ERRORE caricamento confini: {e}")
        sys.stdout.flush()
        raise
    
    try:
        # Genera lista run SOLO quelli che possono forecast il target
        print("\n[2/5] 📅 Generazione lista run validi...")
        sys.stdout.flush()
        run_times = []
        current = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        current = current.replace(hour=(current.hour // 6) * 6)
        
        max_forecast_hours = 384  # 16 giorni max GFS
        
        for i in range(days_back * 4):
            run_time = current - timedelta(hours=i * 6)
            
            # Calcola se questo run può avere il forecast per il target
            forecast_hours_needed = int((target_time - run_time).total_seconds() / 3600)
            
            if 0 <= forecast_hours_needed <= max_forecast_hours:
                run_times.append(run_time)
                print(f"  ✓ Run {run_time.strftime('%d/%m %H:00')} può forecast {forecast_hours_needed}h")
            else:
                print(f"  ✗ Run {run_time.strftime('%d/%m %H:00')} fuori range ({forecast_hours_needed}h)")
        
        run_times.reverse()
        print(f"✓ Generati {len(run_times)} run validi da scaricare")
        sys.stdout.flush()
        
        if len(run_times) < 2:
            error_msg = f"ERRORE: Solo {len(run_times)} run validi! Prova con target più vicino o meno giorni di storico."
            print(f"\n{error_msg}")
            sys.stdout.flush()
            raise Exception(error_msg)
            
    except Exception as e:
        print(f"✗ ERRORE generazione run: {e}")
        sys.stdout.flush()
        raise
    
    # Scarica file
    print(f"\n[3/5] 📥 Download {len(run_times)} file GRIB...")
    sys.stdout.flush()
    files = []
    
    for idx, run_time in enumerate(run_times):
        print(f"\n  [{idx+1}/{len(run_times)}] Run: {run_time.strftime('%Y-%m-%d %H:00 UTC')}")
        sys.stdout.flush()
        
        try:
            file = download_gfs_for_target(target_time, run_time, variable=variable, level=level)
            if file:
                files.append((run_time, file))
                print(f"    ✓ Successo")
            else:
                print(f"    ✗ Download fallito")
            sys.stdout.flush()
        except Exception as e:
            print(f"    ✗ Eccezione: {e}")
            sys.stdout.flush()
    
    if not files:
        error_msg = "ERRORE: Nessun file scaricato con successo!"
        print(f"\n{error_msg}")
        sys.stdout.flush()
        raise Exception(error_msg)
    
    print(f"\n✓ Scaricati {len(files)}/{len(run_times)} file")
    sys.stdout.flush()
    
    # Configurazione variabili con range fissi
    var_configs = {
        'HGT': {'name': 'gh', 'cmap': 'RdYlBu_r', 'label': 'Geopotenziale (m)', 
                'title': 'Geopotenziale 500 hPa', 'contour': True, 'contour_levels': 20,
                'vmin_fixed': 5400, 'vmax_fixed': 5880},
        'APCP': {'name': 'tp', 'cmap': 'Blues', 'label': 'Precipitazione (mm)', 
                 'title': 'Precipitazione', 'contour': False,
                 'vmin_fixed': 0, 'vmax_fixed': 50},
        'TMP': {'name': 't', 'cmap': 'RdYlBu_r', 'label': 'Temperatura (°C)', 
                'title': 'Temperatura', 'contour': True, 'contour_levels': 15,
                'convert_to_celsius': True,
                'vmin_fixed': -10, 'vmax_fixed': 35}
    }
    
    config = var_configs.get(variable, var_configs['HGT'])
    
    # Carica datasets
    print("\n[4/5] 📖 Caricamento datasets GRIB...")
    sys.stdout.flush()
    all_values = []
    datasets = []
    
    for idx, (run_time, file) in enumerate(files):
        try:
            print(f"  [{idx+1}/{len(files)}] Lettura {file}...")
            sys.stdout.flush()
            
            ds = xr.open_dataset(file, engine='cfgrib')
            
            var_name = config['name']
            if var_name not in ds:
                available = list(ds.data_vars.keys())
                print(f"    ⚠️ Variabile '{var_name}' non trovata. Disponibili: {available}")
                if available:
                    var_name = available[0]
                    print(f"    Uso: {var_name}")
                sys.stdout.flush()
            
            # CONVERSIONE IN CELSIUS per temperatura
            if variable == 'TMP' and config.get('convert_to_celsius', False):
                ds[var_name] = ds[var_name] - 273.15
                print(f"    ✓ Temperatura convertita in Celsius")
            
            datasets.append((run_time, ds))
            all_values.append(ds[var_name].values)
            print(f"    ✓ OK - Tempo: {ds.time.values}")
            sys.stdout.flush()
        except Exception as e:
            print(f"    ✗ Errore lettura: {e}")
            sys.stdout.flush()
    
    if not datasets:
        error_msg = "ERRORE: Nessun dataset caricato con successo!"
        print(f"\n{error_msg}")
        sys.stdout.flush()
        raise Exception(error_msg)
    
    print(f"✓ Caricati {len(datasets)} datasets")
    sys.stdout.flush()
    
    # Verifica che tutti i dataset abbiano il tempo target
    print("\n🎯 Verifica tempi target...")
    valid_datasets = []
    
    for run_time, ds in datasets:
        try:
            available_times = ds.time.values
            target_np = np.datetime64(target_time)
            
            # Gestisci sia array che valori scalari
            if available_times.ndim == 0:
                available_times = np.array([available_times])
            
            # Verifica che il tempo nel dataset sia quello target (entro 1 minuto)
            time_match = np.abs(available_times - target_np) < np.timedelta64(1, 'm')
            
            if np.any(time_match):
                valid_datasets.append((run_time, ds))
                actual_time = available_times[np.argmax(time_match)] if available_times.size > 1 else available_times[0]
                print(f"  ✓ {run_time.strftime('%d/%m %H:00')} → {pd.Timestamp(actual_time).strftime('%d/%m %H:00')}")
            else:
                actual_time = available_times[0] if available_times.size > 0 else "N/A"
                time_diff = np.abs(actual_time - target_np).astype('timedelta64[h]').astype(int)
                print(f"  ⚠️ {run_time.strftime('%d/%m %H:00')} tempo diverso: {pd.Timestamp(actual_time).strftime('%d/%m %H:00')} (diff: {time_diff}h)")
                # Accettiamo comunque il dataset
                valid_datasets.append((run_time, ds))
                
        except Exception as e:
            print(f"  ✗ Errore verifica {run_time.strftime('%d/%m %H:00')}: {e}")
            continue
    
    datasets = valid_datasets
    
    if len(datasets) < 2:
        error_msg = f"ERRORE: Solo {len(datasets)} dataset validi!"
        print(f"\n{error_msg}")
        sys.stdout.flush()
        raise Exception(error_msg)
    
    print(f"✓ Dataset finali: {len(datasets)}")
    
    # CALCOLO RANGE VALORI CON SCALA FISSA
    print("\n🎯 Configurazione scala fissa...")
    
    if 'vmin_fixed' in config and 'vmax_fixed' in config:
        vmin = config['vmin_fixed']
        vmax = config['vmax_fixed']
        print(f"✓ Scala fissa: {vmin} - {vmax}")
    else:
        data_min = np.nanmin([np.nanmin(v) for v in all_values])
        data_max = np.nanmax([np.nanmax(v) for v in all_values])
        
        if variable == 'HGT':
            vmin = np.floor(data_min / 10) * 10
            vmax = np.ceil(data_max / 10) * 10
        elif variable == 'TMP':
            vmin = np.floor(data_min)
            vmax = np.ceil(data_max)
        else:
            margin = (data_max - data_min) * 0.1
            vmin = data_min - margin
            vmax = data_max + margin
        
        print(f"✓ Scala calcolata dai dati: {vmin:.1f} - {vmax:.1f}")
    
    sys.stdout.flush()
    
    # Crea animazione
    print("\n[5/5] 🎬 Creazione animazione GIF...")
    sys.stdout.flush()
    
    fig, ax = plt.subplots(figsize=(12, 10))
    
    def animate(i):
        print(f"  Frame {i+1}/{len(datasets)}", end='\r')
        sys.stdout.flush()
        
        ax.clear()
        run_time, ds = datasets[i]
        
        var_name = config['name']
        if var_name not in ds:
            var_name = list(ds.data_vars.keys())[0]
        
        # PLOT CON SCALA FISSA
        im = ds[var_name].plot(ax=ax, cmap=config['cmap'], vmin=vmin, vmax=vmax, 
                               add_colorbar=False)
        
        if config.get('contour', False):
            levels = np.linspace(vmin, vmax, config.get('contour_levels', 20))
            cs = ax.contour(ds.longitude, ds.latitude, ds[var_name], 
                           levels=levels, colors='black', linewidths=0.5, alpha=0.5)
            ax.clabel(cs, inline=True, fontsize=8, fmt='%.1f' if variable == 'TMP' else '%d')
        
        piemonte.boundary.plot(ax=ax, color='red', linewidth=2)
        
        ax.set_xlim([6.5, 9.3])
        ax.set_ylim([44.0, 46.6])
        
        hours_ahead = int((target_time - run_time).total_seconds() / 3600)
        
        # Ottieni il tempo effettivo del dataset
        actual_time = ds.time.values
        if actual_time.ndim == 0:
            actual_time = pd.Timestamp(actual_time)
        else:
            actual_time = pd.Timestamp(actual_time[0])
        
        time_info = ""
        if actual_time != target_time:
            time_diff = int((actual_time - pd.Timestamp(target_time)).total_seconds() / 3600)
            time_info = f" (dati: {actual_time.strftime('%H:00')} UTC, diff: {time_diff:+d}h)"
        
        ax.set_title(f'{config["title"]} - Previsione per {target_time.strftime("%d/%m/%Y %H:00 UTC")}{time_info}\n' +
                    f'Run: {run_time.strftime("%d/%m/%Y %H:00 UTC")} ({hours_ahead}h prima)',
                    fontsize=14, fontweight='bold')
        
        ax.set_xlabel('Longitudine')
        ax.set_ylabel('Latitudine')
        ax.grid(True, alpha=0.3)
        
        return [im]
    
    # CREAZIONE COLORBAR CON SCALA FISSA
    cbar = plt.colorbar(plt.cm.ScalarMappable(cmap=config['cmap'], 
                        norm=plt.Normalize(vmin=vmin, vmax=vmax)),
                       ax=ax, label=config['label'])
    
    print("\n  Rendering frames...")
    sys.stdout.flush()
    
    anim = animation.FuncAnimation(fig, animate, frames=len(datasets),
                                  interval=800, blit=False, repeat=True)
    
    print(f"\n  💾 Salvataggio in {output_file}...")
    sys.stdout.flush()
    
    try:
        Writer = animation.writers['pillow']
        writer = Writer(fps=1.5, metadata=dict(artist='GFS Forecast'), bitrate=1800)
        anim.save(output_file, writer=writer)
        print(f"  ✓ Salvato!")
        sys.stdout.flush()
    except Exception as e:
        print(f"  ✗ ERRORE salvataggio: {e}")
        sys.stdout.flush()
        raise
    
    plt.close()
    
    print("\n" + "="*60)
    print(f"✅ ANIMAZIONE COMPLETATA: {output_file}")
    print(f"📊 Scala fissa: {vmin} - {vmax} {config['label'].split('(')[-1].split(')')[0]}")
    print(f"📈 Dataset utilizzati: {len(datasets)}")
    print("="*60)
    sys.stdout.flush()
    
    return anim, datasets
    
def create_rmse_analysis(datasets, target_time, variable_name):
    """Crea analisi RMSE per l'evoluzione delle previsioni"""
    
    print("📊 Calcolo RMSE spaziale...")
    
    # Mappa nomi variabili GRIB
    var_name_map = {
        'HGT': 'gh',
        'APCP': 'tp', 
        'TMP': 't'
    }
    
    grib_var_name = var_name_map.get(variable_name, variable_name.lower())
    
    forecasts = []
    run_dates = []
    
    # Estrai previsioni da ogni dataset
    for run_time, dataset in datasets:
        if grib_var_name in dataset:
            try:
                # VERIFICA: Controlla le dimensioni della variabile
                data_var = dataset[grib_var_name]
                print(f"  Analisi {run_time.strftime('%d/%m %H:00')}: dims={data_var.dims}, shape={data_var.shape}")
                
                # Se non ha dimensione time, usa direttamente la variabile
                if 'time' not in data_var.dims:
                    forecast = data_var
                    print(f"    ✓ Variabile senza dimensione time")
                else:
                    # Se ha dimensione time, prendi il primo elemento
                    if data_var.dims:
                        forecast = data_var.isel(time=0)
                    else:
                        forecast = data_var
                    print(f"    ✓ Variabile con dimensione time")
                    
                forecasts.append(forecast)
                run_dates.append(run_time)
                print(f"✓ Run {run_time.strftime('%d/%m %H:00')} utilizzato")
                
            except Exception as e:
                print(f"✗ Errore run {run_time.strftime('%d/%m %H:00')}: {e}")
                continue
    
    print(f"📈 Run validi per RMSE: {len(forecasts)}/{len(datasets)}")
    
    if len(forecasts) < 2:
        print("❌ Non abbastanza dati per calcolo RMSE")
        return None
    
    # Ultimo run come riferimento
    last_run_forecast = forecasts[-1]
    
    # Calcola RMSE spaziale
    rmses = []
    for i, forecast in enumerate(forecasts):
        try:
            rmse = np.sqrt(((forecast - last_run_forecast)**2).mean())
            rmses.append(float(rmse))
            print(f"  RMSE run {run_dates[i].strftime('%d/%m %H:00')}: {float(rmse):.2f}")
        except Exception as e:
            print(f"  ✗ Errore calcolo RMSE per {run_dates[i].strftime('%d/%m %H:00')}: {e}")
            continue
    
    if len(rmses) < 2:
        print("❌ Non abbastanza RMSE calcolati")
        return None
    
    # Crea plot
    fig, ax = plt.subplots(figsize=(10, 4))
    
    ax.plot(run_dates, rmses, 'o-', linewidth=2, markersize=6, 
            color='#2E86AB', markerfacecolor='#A23B72')
    
    # Evidenzia l'ultimo run
    ax.axvline(x=run_dates[-1], color='red', linestyle='--', alpha=0.7, 
               label='Ultimo run (riferimento)')
    
    # Aggiungi unità di misura
    units = {'HGT': 'm', 'APCP': 'mm', 'TMP': '°C'}
    unit = units.get(variable_name, '')
    
    ax.set_xlabel('Data del Run')
    ax.set_ylabel(f'RMSE Spaziale ({unit})')
    ax.set_title(f'Evoluzione Accuratezza Previsioni {variable_name}\n'
                f'RMSE spaziale rispetto all\'ultimo run ({run_dates[-1].strftime("%d/%m %H:00")})')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    print(f"✅ RMSE calcolato per {len(rmses)} run")
    return fig