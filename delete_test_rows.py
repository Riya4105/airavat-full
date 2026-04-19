import psycopg2

conn = psycopg2.connect(
    host="localhost", port=5432,
    database="airavat", user="airavat", password="airavat123"
)
cur = conn.cursor()
cur.execute("DELETE FROM zone_observations WHERE source = 'test'")
print(f"Deleted {cur.rowcount} test rows")
conn.commit()
conn.close()