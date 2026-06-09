#!/bin/bash
OUT_FILE="database_backup.json"
python manage.py dumpdata --exclude contenttypes --exclude auth.Permission --indent 4 -o "$OUT_FILE"
