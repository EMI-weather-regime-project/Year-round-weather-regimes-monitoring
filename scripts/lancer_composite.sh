#!/bin/bash

chemin_absolu = "/Year-round-weather-regimes-monitoring"      # chemin absolu jusqu'au dossier Year-round-weather-regimes-monitoring

source chemin_absolu/.venv/bin/activate
sleep 10
cd chemin_absolue/scripts
python3 plotting_composites.py
