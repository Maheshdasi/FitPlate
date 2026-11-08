"""Wait until PostgreSQL accepts connections (it can take a few seconds to start)."""
import os
import sys
import time

import psycopg2

url = os.environ.get("DATABASE_URL", "").replace("postgresql+psycopg2://", "postgresql://")
for attempt in range(60):
    try:
        psycopg2.connect(url).close()
        print("Database is ready.")
        sys.exit(0)
    except psycopg2.OperationalError:
        time.sleep(2)
print("Database did not start in time.")
sys.exit(1)
