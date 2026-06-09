@ECHO off
python -Xutf8 manage.py dumpdata --exclude contenttypes --exclude auth.Permission --format json --indent 4 -o database_backup.json
Exit