import sqlite3
import json

# SQLite database'ini kontrol et
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# Tüm tabloları listele
cursor.execute( SELECT name FROM sqlite_master WHERE type=table
