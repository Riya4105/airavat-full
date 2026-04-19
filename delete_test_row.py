import psycopg2, os
from urllib.parse import urlparse

db_url = os.environ['DATABASE_URL']
parsed = urlparse(db_url)
conn = psycopg2.connect(
    host=parsed.hostname, port=parsed.port,
    database=parsed.path[1:], user=parsed.username,
    password=parsed.password, sslmode='require'
)
cur = conn.cursor()
cur.execute("DELETE FROM zone_observations WHERE source = 'test'")
print(f'Deleted {cur.rowcount} test rows')
conn.commit()
conn.close()