#!/bin/bash
gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 90
