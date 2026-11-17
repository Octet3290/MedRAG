import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

db_url = os.environ.get("DATABASE_URL")
if not db_url:
    print("ERROR: DATABASE_URL not set in environment.")
    exit(1)

# Remove driver prefix for raw psycopg test if present
raw_url = db_url.replace("postgresql+psycopg://", "postgresql://")

print(f"Connecting to Neon database...")
try:
    with psycopg.connect(raw_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
            print(f"Connected successfully!")
            print(f"PostgreSQL Version: {version}")

            # Verify and enable pgvector extension
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            conn.commit()

            cur.execute("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';")
            ext = cur.fetchone()
            print(f"pgvector extension status: {ext}")
            print("Ready for Milestone 2 migrations!")
except Exception as e:
    print(f"Failed to connect: {e}")
    exit(1)
