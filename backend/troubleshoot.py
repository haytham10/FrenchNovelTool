#!/usr/bin/env python3
"""
Railway/Supabase Deployment Troubleshooting Tool

This script checks common deployment issues and provides actionable fixes.

Usage:
    python troubleshoot.py
    
Environment Variables Required:
    DATABASE_URL - PostgreSQL connection string
    REDIS_URL - Redis connection string (optional)
"""
import os
import sys


def print_header(text):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)


def check_environment_variables():
    """Check required environment variables"""
    print_header("Environment Variables Check")
    
    required = ['DATABASE_URL', 'SECRET_KEY', 'GEMINI_API_KEY']
    optional = ['REDIS_URL', 'GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET']
    
    all_ok = True
    
    print("\n✓ Required Variables:")
    for var in required:
        value = os.getenv(var)
        if value:
            # Show first 20 chars for security
            display = value[:20] + "..." if len(value) > 20 else value
            print(f"  ✅ {var}: {display}")
        else:
            print(f"  ❌ {var}: NOT SET")
            all_ok = False
    
    print("\n✓ Optional Variables:")
    for var in optional:
        value = os.getenv(var)
        if value:
            display = value[:20] + "..." if len(value) > 20 else value
            print(f"  ✅ {var}: {display}")
        else:
            print(f"  ⚠️  {var}: not set")
    
    return all_ok


def check_database_connection():
    """Check database connectivity"""
    print_header("Database Connection Check")
    
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL not set")
        return False
    
    try:
        from sqlalchemy import create_engine, text
        
        # Handle postgres:// -> postgresql://
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        
        print(f"\n📍 Database: {db_url.split('@')[1].split('/')[0] if '@' in db_url else 'unknown'}")
        
        engine = create_engine(db_url, pool_pre_ping=True, connect_args={'connect_timeout': 10})
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✅ Connection successful!")
            print(f"   PostgreSQL version: {version.split(',')[0]}")
            
            # Check if tables exist
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]
            
            expected_tables = ['users', 'jobs', 'history', 'credit_ledger', 'user_settings']
            missing_tables = [t for t in expected_tables if t not in tables]
            
            if missing_tables:
                print(f"\n⚠️  Missing tables: {', '.join(missing_tables)}")
                print("   Run: flask db upgrade")
            else:
                print(f"✅ All expected tables exist: {', '.join(expected_tables)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Check DATABASE_URL is correct")
        print("   2. Verify network connectivity to Supabase")
        print("   3. Check if IP is whitelisted (if applicable)")
        return False


def check_redis_connection():
    """Check Redis connectivity"""
    print_header("Redis Connection Check")
    
    redis_url = os.getenv('REDIS_URL')
    if not redis_url:
        print("⚠️  REDIS_URL not set (will use memory:// for rate limiting)")
        return True
    
    if redis_url == 'memory://':
        print("ℹ️  Using memory:// backend (no actual Redis)")
        return True
    
    try:
        import redis
        
        print(f"\n📍 Redis: {redis_url.split('@')[1] if '@' in redis_url else 'localhost'}")
        
        r = redis.from_url(redis_url, socket_connect_timeout=5, socket_timeout=5)
        r.ping()
        
        print("✅ Redis connection successful!")
        
        # Get Redis info
        info = r.info()
        print(f"   Redis version: {info.get('redis_version', 'unknown')}")
        print(f"   Connected clients: {info.get('connected_clients', 0)}")
        print(f"   Used memory: {info.get('used_memory_human', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Check REDIS_URL is correct")
        print("   2. Verify Redis service is running in Railway")
        print("   3. Check if SSL/TLS is required (set REDIS_TLS=true)")
        return False


def check_config():
    """Check application configuration"""
    print_header("Application Configuration Check")
    
    try:
        from config import Config
        
        print("\n✅ Config loaded successfully")
        
        # Check pool settings
        pool_size = Config.SQLALCHEMY_ENGINE_OPTIONS.get('pool_size')
        pool_recycle = Config.SQLALCHEMY_ENGINE_OPTIONS.get('pool_recycle')
        pool_pre_ping = Config.SQLALCHEMY_ENGINE_OPTIONS.get('pool_pre_ping')
        
        print(f"\n📊 Database Pool Settings:")
        print(f"   Pool size: {pool_size}")
        print(f"   Max overflow: {Config.SQLALCHEMY_ENGINE_OPTIONS.get('max_overflow')}")
        print(f"   Pool recycle: {pool_recycle}s")
        print(f"   Pre-ping: {pool_pre_ping}")
        
        if pool_size < 5:
            print("   ⚠️  Pool size is low, consider increasing for production")
        
        # Check Celery settings
        print(f"\n📋 Celery Settings:")
        print(f"   Broker: {Config.CELERY_BROKER_URL[:30]}...")
        print(f"   Backend: {Config.CELERY_RESULT_BACKEND[:30]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Config load failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_migrations():
    """Check if migrations are up to date"""
    print_header("Database Migrations Check")
    
    try:
        from sqlalchemy import create_engine, text
        
        db_url = os.getenv('DATABASE_URL')
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        
        engine = create_engine(db_url, pool_pre_ping=True)
        
        with engine.connect() as conn:
            # Check alembic version
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            version = result.scalar()
            print(f"✅ Current migration: {version}")
            
            # Check for async columns in jobs table
            result = conn.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'jobs' 
                  AND column_name IN ('celery_task_id', 'progress_percent', 'current_step')
            """))
            async_columns = [row[0] for row in result]
            
            if len(async_columns) == 3:
                print("✅ Async processing columns exist")
            else:
                print(f"❌ Missing async columns: {3 - len(async_columns)}")
                print("\n💡 Fix:")
                print("   Option 1: Run migrations: flask db upgrade")
                print("   Option 2: Run fix_jobs_table.sql directly")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration check failed: {e}")
        return False


def main():
    """Main troubleshooting function"""
    print("\n" + "🔧" * 30)
    print("Railway/Supabase Deployment Troubleshooting Tool")
    print("🔧" * 30)
    
    results = {
        'env_vars': check_environment_variables(),
        'config': check_config(),
        'database': check_database_connection(),
        'redis': check_redis_connection(),
        'migrations': check_migrations(),
    }
    
    print_header("Summary")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    print(f"\n✓ Checks passed: {passed}/{total}\n")
    
    for check, result in results.items():
        status = "✅" if result else "❌"
        print(f"  {status} {check.replace('_', ' ').title()}")
    
    if passed == total:
        print("\n🎉 All checks passed! Deployment should work correctly.")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total - passed} checks failed. Review errors above.")
        print("\nFor detailed help, see:")
        print("  - docs/Deployment/RAILWAY_DEPLOYMENT.md")
        print("  - docs/Deployment/RAILWAY_QUICK_CHECKLIST.md")
        sys.exit(1)


if __name__ == '__main__':
    main()
