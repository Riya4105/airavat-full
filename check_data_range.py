import psycopg2, os
from urllib.parse import urlparse

db_url = os.environ['DATABASE_URL']
parsed = urlparse(db_url)
conn = psycopg2.connect(
    host=parsed.hostname, port=parsed.port,
    database=parsed.path[1:], user=parsed.username,
    password=os.environ.get('DB_PASSWORD', parsed.password),
    sslmode='require'
)
cur = conn.cursor()

cur.execute("""
    SELECT zone_id,
           COUNT(*) as obs,
           MIN(time::date) as earliest,
           MAX(time::date) as latest
    FROM zone_observations
    GROUP BY zone_id
    ORDER BY zone_id
""")

print(f"{'Zone':<6} {'Obs':<6} {'From':<12} {'To':<12}")
print("-" * 38)
for r in cur.fetchall():
    print(f"{r[0]:<6} {r[1]:<6} {str(r[2]):<12} {str(r[3]):<12}")

cur.execute("SELECT COUNT(*) FROM zone_observations")
print(f"\nTotal rows: {cur.fetchone()[0]}")

conn.close()