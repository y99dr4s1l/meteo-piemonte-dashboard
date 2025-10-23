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

def create_forecast_evolution_animation(target_time, days_back=5, variable='HGT', 
                                       level='500_mb', output_file='current_forecast.gif'):
    """Crea animazione evoluzione previsione"""
    
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
        # Genera lista run
        print("\n[2/5] 📅 Generazione lista run...")
        sys.stdout.flush()
        run_times = []
        current = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        current = current.replace(hour=(current.hour // 6) * 6)
        
        for i in range(days_back * 4):
            run_time = current - timedelta(hours=i * 6)
            if target_time > run_time:
                run_times.append(run_time)
        
        run_times.reverse()
        print(f"✓ Generate {len(run_times)} run da scaricare")
        sys.stdout.flush()
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
    
    # Configurazione variabili
    var_configs = {
        'HGT': {'name': 'gh', 'cmap': 'RdYlBu_r', 'label': 'Geopotenziale (m)', 
                'title': 'Geopotenziale 500 hPa', 'contour': True, 'contour_levels': 20},
        'APCP': {'name': 'tp', 'cmap': 'Blues', 'label': 'Precipitazione (mm)', 
                 'title': 'Precipitazione', 'contour': False},
        'TMP': {'name': 't', 'cmap': 'RdYlBu_r', 'label': 'Temperatura (K)', 
                'title': 'Temperatura', 'contour': True, 'contour_levels': 15}
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
            
            datasets.append((run_time, ds))
            all_values.append(ds[var_name].values)
            print(f"    ✓ OK")
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
    
    # Calcola range valori
    vmin = np.nanmin([np.nanmin(v) for v in all_values])
    vmax = np.nanmax([np.nanmax(v) for v in all_values])
    
    if variable == 'HGT':
        vmin = np.floor(vmin / 10) * 10
        vmax = np.ceil(vmax / 10) * 10
    
    print(f"Range valori: {vmin} - {vmax}")
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
        
        im = ds[var_name].plot(ax=ax, cmap=config['cmap'], vmin=vmin, vmax=vmax, 
                               add_colorbar=False)
        
        if config.get('contour', False):
            levels = np.linspace(vmin, vmax, config.get('contour_levels', 20))
            cs = ax.contour(ds.longitude, ds.latitude, ds[var_name], 
                           levels=levels, colors='black', linewidths=0.5, alpha=0.5)
            ax.clabel(cs, inline=True, fontsize=8, fmt='%d')
        
        piemonte.boundary.plot(ax=ax, color='red', linewidth=2)
        
        ax.set_xlim([6.5, 9.3])
        ax.set_ylim([44.0, 46.6])
        
        hours_ahead = int((target_time - run_time).total_seconds() / 3600)
        ax.set_title(f'{config["title"]} - Previsione per {target_time.strftime("%d/%m/%Y %H:00 UTC")}\n' +
                    f'Run: {run_time.strftime("%d/%m/%Y %H:00 UTC")} ({hours_ahead}h prima)',
                    fontsize=14, fontweight='bold')
        
        ax.set_xlabel('Longitudine')
        ax.set_ylabel('Latitudine')
        ax.grid(True, alpha=0.3)
        
        return [im]
    
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
    print("="*60)
    sys.stdout.flush()
    
    return anim
