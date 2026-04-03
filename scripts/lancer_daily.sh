#!/bin/bash

source /opt/metwork-mfext-2.3/share/profile
sleep 10
cd /home/mcbd/voisinl/WWW/scripts
python3 recuperer_nouvelles_donnees.py
python3 daily-tasks.py --datatype ERA5
python3 daily-tasks.py --datatype AnaCEP