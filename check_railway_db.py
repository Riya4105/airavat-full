import psycopg2
import os

conn = psycopg2.connect(os.environ['DATABASE_URL'], sslmode='require')
cur = conn.cursor()
cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
tables = cur.fetchall()
print('Tables in Railway database:')
for t in tables:
    print(f'  {t[0]}')
conn.close()