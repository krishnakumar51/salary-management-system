"""Start (or reuse) a throw-away local PostgreSQL without Docker, using the `pgserver` dev dependency.

    python scripts/dev_postgres.py          # prints a DATABASE_URL and leaves the server running

Data lives in backend/.pgdata (git-ignored). Stop it with:  python scripts/dev_postgres.py --stop
"""

import sys
from pathlib import Path

import pgserver

DATA_DIR = Path(__file__).resolve().parent.parent / ".pgdata"

if __name__ == "__main__":
    server = pgserver.get_server(DATA_DIR, cleanup_mode="stop" if "--stop" in sys.argv else None)
    if "--stop" in sys.argv:
        server.cleanup()
        print("stopped")
    else:
        print(server.get_uri().replace("postgresql://", "postgresql+psycopg://", 1))
