@ECHO off
waitress-serve --port=8000 --threads=16 --connection-limit=200 core.wsgi:application
Exit
