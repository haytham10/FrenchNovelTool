#!/usr/bin/env python3
"""
Safe script to fix the job_chunks migration error by dropping conflicting indexes.
Run this inside Railway SSH or any environment where DATABASE_URL is set.
Usage: python backend/scripts/fix_migration.py
"""
import os
import sys
from sqlalchemy import create_engine, text


def main():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)

    print(f"🔗 Connecting to database...")
    engine = create_engine(database_url)

    try:
        with engine.begin() as conn:
            # Check current alembic version
            result = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
            current_version = result[0] if result else "None"
            print(f"📌 Current alembic version: {current_version}")

            # Check if job_chunks table exists
            table_check = conn.execute(
                text(
                    "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='job_chunks')"
                )
            ).scalar()

            if table_check:
                print("✅ Table 'job_chunks' exists")

                # List current indexes
                indexes = conn.execute(
                    text("SELECT indexname FROM pg_indexes WHERE tablename='job_chunks'")
                ).fetchall()
                print(f"📋 Current indexes: {[idx[0] for idx in indexes]}")

                # Drop conflicting indexes if they exist
                indexes_to_drop = [
                    "ix_job_chunks_job_id",
                    "ix_job_chunks_status",
                    "idx_job_chunk_unique",
                ]
                for index_name in indexes_to_drop:
                    index_exists = conn.execute(
                        text(
                            "SELECT EXISTS(SELECT 1 FROM pg_indexes WHERE tablename='job_chunks' AND indexname=:iname)"
                        ),
                        {"iname": index_name},
                    ).scalar()

                    if index_exists:
                        print(f"🗑️  Dropping index: {index_name}")
                        conn.execute(text(f"DROP INDEX IF EXISTS {index_name}"))
                    else:
                        print(f"⏭️  Index {index_name} doesn't exist, skipping")

                # Show indexes after cleanup
                indexes_after = conn.execute(
                    text("SELECT indexname FROM pg_indexes WHERE tablename='job_chunks'")
                ).fetchall()
                print(f"📋 Indexes after cleanup: {[idx[0] for idx in indexes_after]}")
            else:
                print("ℹ️  Table 'job_chunks' doesn't exist yet (will be created by migration)")

        print("\n✅ Cleanup complete! Now run: flask db upgrade")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
