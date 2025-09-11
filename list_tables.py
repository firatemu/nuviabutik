import sqlite3

conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

cursor.execute('SELECT name FROM sqlite_master WHERE type=" table\')
all_tables = cursor.fetchall()

print('All tables in SQLite:')
for table in all_tables:
 table_name = table[0]
 if not table_name.startswith('django_') and not table_name.startswith('auth_') and table_name != 'sqlite_sequence':
 try:
 cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
 count = cursor.fetchone()[0]
 print(f' {table_name}: {count} records')
 except:
 print(f' {table_name}: error reading')

conn.close()
