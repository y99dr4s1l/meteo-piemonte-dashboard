# 🌦️ Dashboard Meteo Piemonte

Dashboard interattiva per visualizzare l'evoluzione delle previsioni meteorologiche GFS per il Piemonte.

## Features

- 📊 Animazioni dell'evoluzione delle previsioni
- 🌡️ Multiple variabili: Geopotenziale 500hPa, Precipitazione, Temperatura
- 📅 Storico fino a 7 giorni di run precedenti
- 🗺️ Focus sulla regione Piemonte

## Come Usare

1. Seleziona data e ora target
2. Scegli la variabile meteorologica
3. Clicca "Genera Animazione"
4. Scarica la GIF generata

## Fonte Dati

NOAA GFS 0.25° - Global Forecast System

## Tech Stack

- Streamlit
- xarray + cfgrib
- matplotlib
- geopandas