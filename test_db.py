# test_db.py
# Verifies TimescaleDB connection and creates the core hypertable

import psycopg2

# Connection details matching our docker run command
CONN = {
    "host": "localhost",
    "port": 5432,
    "database": "airavat",
    "user": "airavat",
    "password": "airavat123"
}

print("=" * 50)
print("AIRAVAT 3.0 — Database Setup")
print("=" * 50)

try:
    # Connect
    conn = psycopg2.connect(**CONN)
    cursor = conn.cursor()
    print("\n✅ Connected to TimescaleDB")

    # Enable TimescaleDB extension
    cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")
    print("✅ TimescaleDB extension enabled")

    # Create the main observations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS zone_observations (
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

    # Convert to hypertable (TimescaleDB magic)
    cursor.execute("""
        SELECT create_hypertable(
            'zone_observations', 'time',
            if_not_exists => TRUE
        );
    """)
    print("✅ Hypertable created — time-series optimised")

    # Create zone baselines table
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

    # Create alerts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS zone_alerts (
            time            TIMESTAMPTZ NOT NULL,
            zone_id         TEXT NOT NULL,
            alert_level     TEXT,
            priority_score  FLOAT,
            chain_position  INT,
            event_type      TEXT,
            operator_feedback TEXT
        );
    """)
    print("✅ zone_alerts table created")

    # Insert a test row to verify everything works
    cursor.execute("""
        INSERT INTO zone_observations
            (time, zone_id, sst, chl_a, source)
        VALUES
            (NOW(), 'Z1', 28.5, 0.42, 'test');
    """)
    print("✅ Test row inserted")

    # Read it back
    cursor.execute("""
        SELECT time, zone_id, sst, chl_a
        FROM zone_observations
        LIMIT 1;
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