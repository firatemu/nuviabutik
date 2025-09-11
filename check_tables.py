import sqlite3

conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# Tablo listesini al
cursor.execute(" SELECT name FROM sqlite_master WHERE type=table AND name NOT LIKE django_% AND name NOT LIKE auth_% AND name != sqlite_sequence \)
tables = cursor.fetchall()

print('Available tables in SQLite:')
for table in tables:
 table_name = table[0]
 cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
 count = cursor.fetchone()[0]
 print(f'{table_name}: {count} records')

conn.close()
