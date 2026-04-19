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
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'zone_alerts'
    ORDER BY ordinal_position
""")
print("zone_alerts columns:")
for r in cur.fetchall():
    print(f"  {r[0]} — {r[1]}")
conn.close()