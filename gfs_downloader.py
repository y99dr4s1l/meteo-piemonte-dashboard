import requests
from datetime import datetime, timedelta
import os

def download_gfs_for_target(target_time, run_time, variable='APCP', level='surface', output_dir='gfs_data'):
    """
    Scarica dati GFS per una specifica run
    """
    os.makedirs(output_dir, exist_ok=True)
    
    forecast_hours = int((target_time - run_time).total_seconds() / 3600)
    
    if forecast_hours < 0 or forecast_hours > 384:
        return None
    
    if forecast_hours <= 120:
        forecast_hours = (forecast_hours // 3) * 3
    else:
        forecast_hours = (forecast_hours // 6) * 6
    
    cycle = run_time.hour
    date_str = run_time.strftime("%Y%m%d")
    
    output_file = os.path.join(output_dir, f'gfs_{variable}_{date_str}_{cycle:02d}z_f{forecast_hours:03d}.grib2')
    
    if os.path.exists(output_file):
        return output_file
    
    base_url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"
    
    params = {
        'dir': f'/gfs.{date_str}/{cycle:02d}/atmos',
        'file': f'gfs.t{cycle:02d}z.pgrb2.0p25.f{forecast_hours:03d}',
        f'var_{variable}': 'on',
        'leftlon': '6',
        'rightlon': '19',
        'toplat': '47',
        'bottomlat': '36',
        f'lev_{level}': 'on',
        'subregion': '',
    }
    
    try:
        response = requests.get(base_url, params=params, stream=True, timeout=30)
        
        if response.status_code == 200:
            with open(output_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    f.write(chunk)
            return output_file
        else:
            return None
    except Exception as e:
        print(f"Errore download: {e}")
        return None