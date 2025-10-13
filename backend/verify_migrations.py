#!/usr/bin/env python3
"""
Database Migration Verification Script for Railway/Supabase Deployment

This script verifies that all expected database migrations have been applied
and all required columns exist in the production database.

Usage:
    python verify_migrations.py

Environment Variables Required:
    DATABASE_URL - PostgreSQL connection string
"""
import os
import sys
from sqlalchemy import create_engine, inspect, text
from datetime import datetime, timezone


def get_db_engine():
    """Create database engine from DATABASE_URL"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL environment variable not set")
        sys.exit(1)

    # Handle postgres:// -> postgresql://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    return create_engine(db_url, pool_pre_ping=True)


def check_alembic_version(engine):
    """Check current Alembic migration version"""
    print("\n📋 Checking migration version...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            version = result.scalar()
            if version:
                print(f"✅ Current migration version: {version}")
                return version
            else:
                print("⚠️  No migration version found (alembic_version table empty)")
                return None
    except Exception as e:
        print(f"❌ Failed to check migration version: {e}")
        return None


def verify_table_columns(engine, table_name, expected_columns):
    """Verify that a table has all expected columns"""
    print(f"\n🔍 Verifying '{table_name}' table columns...")

    inspector = inspect(engine)

    # Check if table exists
    if table_name not in inspector.get_table_names():
        print(f"❌ Table '{table_name}' does not exist!")
        return False

    # Get actual columns
    actual_columns = {col["name"] for col in inspector.get_columns(table_name)}

    # Check for missing columns
    missing_columns = set(expected_columns) - actual_columns
    extra_columns = actual_columns - set(expected_columns)

    if missing_columns:
        print(f"❌ Missing columns in '{table_name}':")
        for col in sorted(missing_columns):
            print(f"   - {col}")
        return False

    print(f"✅ All expected columns present in '{table_name}'")

    if extra_columns:
        print(f"ℹ️  Extra columns found (this is OK):")
        for col in sorted(extra_columns):
            print(f"   - {col}")

    return True


def main():
    """Main verification function"""
    print("🚀 Starting Database Migration Verification\n")
    print(f"⏰ Timestamp: {datetime.now(timezone.utc).isoformat()}Z\n")

    # Create database engine
    engine = get_db_engine()

    # Check connection
    print("🔌 Testing database connection...")
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database connection successful\n")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)

    # Check migration version
    version = check_alembic_version(engine)

    # Expected columns for async processing (from migration 48fd2dc76953)
    jobs_async_columns = [
        "id",
        "user_id",
        "history_id",
        "status",
        "original_filename",
        "model",
        "estimated_tokens",
        "actual_tokens",
        "estimated_credits",
        "actual_credits",
        "pricing_version",
        "pricing_rate",
        "processing_settings",
        "created_at",
        "started_at",
        "completed_at",
        "error_message",
        "error_code",
        # Async processing fields
        "celery_task_id",
        "progress_percent",
        "current_step",
        "total_chunks",
        "processed_chunks",
        "chunk_results",
        "failed_chunks",
        "retry_count",
        "max_retries",
        "is_cancelled",
        "cancelled_at",
        "cancelled_by",
        "processing_time_seconds",
        "gemini_api_calls",
        "gemini_tokens_used",
    ]

    # Verify jobs table
    jobs_ok = verify_table_columns(engine, "jobs", jobs_async_columns)

    # Verify other critical tables
    users_ok = verify_table_columns(
        engine, "users", ["id", "email", "name", "google_id", "created_at", "is_active"]
    )

    history_ok = verify_table_columns(
        engine, "history", ["id", "user_id", "job_id", "timestamp", "original_filename"]
    )

    credit_ledger_ok = verify_table_columns(
        engine, "credit_ledger", ["id", "user_id", "month", "delta_credits", "reason", "timestamp"]
    )

    # Check for indexes on celery_task_id
    print("\n🔍 Checking indexes...")
    inspector = inspect(engine)
    indexes = inspector.get_indexes("jobs")
    celery_task_id_indexed = any("celery_task_id" in idx.get("column_names", []) for idx in indexes)

    if celery_task_id_indexed:
        print("✅ Index on 'celery_task_id' exists")
    else:
        print("⚠️  No index on 'celery_task_id' (this may impact performance)")

    # Summary
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)

    all_ok = jobs_ok and users_ok and history_ok and credit_ledger_ok

    if all_ok:
        print("✅ All verifications passed!")
        print("🎉 Database is ready for async processing")
        sys.exit(0)
    else:
        print("❌ Some verifications failed")
        print("\n💡 Next steps:")
        print("   1. Run database migrations: flask db upgrade")
        print("   2. Or apply fix_jobs_table.sql directly")
        print("   3. Re-run this verification script")
        sys.exit(1)


if __name__ == "__main__":
    main()
