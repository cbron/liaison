#!/bin/bash

cd /opt/liaison
source venv/bin/activate
python -V
python manage.py db upgrade
