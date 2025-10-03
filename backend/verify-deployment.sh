#!/bin/bash

# Deployment Verification Script for French Novel Tool
# Run this after deploying PR #36 to verify everything is working

set -e

echo "========================================"
echo "French Novel Tool - Deployment Verification"
echo "PR #36: Async PDF Processing"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the backend directory
if [ ! -f "run.py" ]; then
    echo -e "${RED}❌ Error: Must be run from the backend directory${NC}"
    exit 1
fi

echo "Step 1: Checking Python environment..."
if python -c "import celery" 2>/dev/null; then
    VERSION=$(python -c "import celery; print(celery.__version__)")
    echo -e "${GREEN}✓ Celery $VERSION installed${NC}"
else
    echo -e "${RED}❌ Celery not installed. Run: pip install celery==5.3.4${NC}"
    exit 1
fi

echo ""
echo "Step 2: Checking database migration..."
CURRENT_VERSION=$(python -m flask db current 2>&1 | grep -E "^[a-z0-9_]+" || echo "error")
if [ "$CURRENT_VERSION" = "add_job_progress_tracking (head)" ] || [ "$CURRENT_VERSION" = "add_job_progress_tracking" ]; then
    echo -e "${GREEN}✓ Database at correct migration: $CURRENT_VERSION${NC}"
else
    echo -e "${YELLOW}⚠ Database at: $CURRENT_VERSION${NC}"
    echo -e "${YELLOW}  Expected: add_job_progress_tracking${NC}"
fi

echo ""
echo "Step 3: Checking database schema..."
COLUMNS=$(python -c "
from app import create_app, db
app = create_app()
with app.app_context():
    result = db.session.execute(db.text(\"SELECT column_name FROM information_schema.columns WHERE table_name='jobs' AND column_name IN ('total_chunks', 'completed_chunks', 'progress_percent', 'celery_task_id')\")).fetchall()
    print(','.join([r[0] for r in result]))
" 2>/dev/null || echo "error")

if echo "$COLUMNS" | grep -q "celery_task_id"; then
    echo -e "${GREEN}✓ All required columns present${NC}"
    echo "  Columns: $COLUMNS"
else
    echo -e "${RED}❌ Missing columns. Found: $COLUMNS${NC}"
    echo -e "${YELLOW}  Run the manual schema fix from PR_MERGE_CHECKLIST.md${NC}"
fi

echo ""
echo "Step 4: Checking Redis connection..."
REDIS_URL=$(python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('REDIS_URL', 'not-set'))")

if [ "$REDIS_URL" != "not-set" ]; then
    echo -e "${GREEN}✓ REDIS_URL configured: $REDIS_URL${NC}"
    
    if echo "$REDIS_URL" | grep -q "memory://"; then
        echo -e "${YELLOW}  ⚠ Using in-memory mode (development only)${NC}"
    fi
else
    echo -e "${YELLOW}⚠ REDIS_URL not set in .env${NC}"
fi

echo ""
echo "Step 5: Checking environment variables..."
REQUIRED_VARS=("ASYNC_PROCESSING_ENABLED" "CHUNKING_THRESHOLD_PAGES" "CHUNK_SIZE_PAGES")
ALL_SET=true

for VAR in "${REQUIRED_VARS[@]}"; do
    VALUE=$(python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('$VAR', 'not-set'))" 2>/dev/null || echo "error")
    if [ "$VALUE" != "not-set" ]; then
        echo -e "${GREEN}✓ $VAR = $VALUE${NC}"
    else
        echo -e "${RED}❌ $VAR not set${NC}"
        ALL_SET=false
    fi
done

echo ""
echo "Step 6: Testing Celery worker (if running)..."
if pgrep -f "celery.*worker" > /dev/null; then
    echo -e "${GREEN}✓ Celery worker process is running${NC}"
    
    # Try to ping the worker
    if celery -A app.celery_app.celery_app inspect ping 2>/dev/null | grep -q "pong"; then
        echo -e "${GREEN}✓ Celery worker responding to ping${NC}"
    else
        echo -e "${YELLOW}⚠ Celery worker not responding (may need restart)${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Celery worker process not running${NC}"
    echo "  Start with: celery -A app.celery_app.celery_app worker --loglevel=info"
fi

echo ""
echo "Step 7: Checking Flask app startup..."
if python -c "from app import create_app; app = create_app(); print('OK')" 2>&1 | grep -q "OK"; then
    echo -e "${GREEN}✓ Flask app starts successfully${NC}"
else
    echo -e "${RED}❌ Flask app failed to start${NC}"
fi

echo ""
echo "========================================"
echo "Verification Complete"
echo "========================================"
echo ""

# Summary
if [ "$ALL_SET" = true ] && echo "$COLUMNS" | grep -q "celery_task_id"; then
    echo -e "${GREEN}✅ All critical checks passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Start/restart Celery worker"
    echo "2. Test with a large PDF (>50 pages)"
    echo "3. Monitor logs for any errors"
    exit 0
else
    echo -e "${YELLOW}⚠️  Some checks failed. Review output above.${NC}"
    echo ""
    echo "See PR_MERGE_CHECKLIST.md for detailed deployment steps."
    exit 1
fi
