@ECHO off
waitress-serve --port=8000 core.wsgi:application
Exit
