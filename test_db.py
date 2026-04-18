# test_db.py
# Creates core tables on PostgreSQL (Railway compatible)

import psycopg2
import os
from urllib.parse import urlparse

def get_db():
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        parsed = urlparse(db_url)
        return psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port,
            database=parsed.path[1:],
            user=parsed.username,
            password=parsed.password,
            sslmode="require"
        )
    else:
        return psycopg2.connect(
            host="localhost", port=5432,
            database="airavat", user="airavat",
            password="airavat123"
        )

print("=" * 50)
print("AIRAVAT 3.0 — Database Setup")
print("=" * 50)

try:
    conn = get_db()
    cursor = conn.cursor()
    print("\n✅ Connected to PostgreSQL")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS zone_observations (
            id          SERIAL PRIMARY KEY,
            time        TIMESTAMPTZ NOT NULL,
            zone_id     TEXT        NOT NULL,
            sst         FLOAT,
            chl_a       FLOAT,
            salinity    FLOAT,
            wind_speed  FLOAT,
            source      TEXT
        );
    """)
    print("✅ zone_observations table created")

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_zone_obs_time
        ON zone_observations (zone_id, time DESC);
    """)
    print("✅ Index created")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS zone_baselines (
            zone_id         TEXT PRIMARY KEY,
            mean_sst        FLOAT,
            std_sst         FLOAT,
            mean_chl_a      FLOAT,
            std_chl_a       FLOAT,
            last_updated    TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    print("✅ zone_baselines table created")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS zone_alerts (
            id                SERIAL PRIMARY KEY,
            time              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            zone_id           TEXT NOT NULL,
            alert_level       TEXT,
            priority_score    FLOAT,
            chain_position    INT,
            event_type        TEXT,
            operator_feedback TEXT
        );
    """)
    print("✅ zone_alerts table created")

    cursor.execute("""
        INSERT INTO zone_observations
            (time, zone_id, sst, chl_a, source)
        VALUES
            (NOW(), 'Z1', 28.5, 0.42, 'test');
    """)
    print("✅ Test row inserted")

    cursor.execute("""
        SELECT time, zone_id, sst, chl_a
        FROM zone_observations LIMIT 1;
    """)
    row = cursor.fetchone()
    print(f"✅ Test row verified: zone={row[1]}, sst={row[2]}°C, chl_a={row[3]}")

    conn.commit()
    cursor.close()
    conn.close()

    print("\n" + "=" * 50)
    print("Database setup complete.")
    print("3 tables ready: zone_observations, zone_baselines, zone_alerts")
    print("=" * 50)

except Exception as e:
    print(f"\n❌ Error: {e}")