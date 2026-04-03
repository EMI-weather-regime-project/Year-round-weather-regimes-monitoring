#!/bin/bash

chemin_absolu = "/Year-round-weather-regimes-monitoring"      # chemin absolu jusqu'au dossier Year-round-weather-regimes-monitoring

source chemin_absolu/.venv/bin/activate
sleep 10
cd chemin_absolu/scripts
python3 recuperer_nouvelles_donnees.py
python3 daily-tasks.py --datatype ERA5
python3 daily-tasks.py --datatype AnaCEP
