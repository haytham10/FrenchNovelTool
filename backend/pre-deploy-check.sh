#!/bin/bash
# Pre-Deployment Validation Script for Railway
# Run this locally before deploying to catch issues early

set -e

echo "🚀 Railway Deployment Pre-Flight Check"
echo "========================================"
echo ""

ERRORS=0
WARNINGS=0

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

error() {
    echo -e "${RED}❌ ERROR: $1${NC}"
    ERRORS=$((ERRORS + 1))
}

warning() {
    echo -e "${YELLOW}⚠️  WARNING: $1${NC}"
    WARNINGS=$((WARNINGS + 1))
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

info() {
    echo "ℹ️  $1"
}

# Check 1: Required files exist
echo "📁 Checking required files..."
FILES=(
    "backend/config.py"
    "backend/app/__init__.py"
    "backend/app/routes.py"
    "backend/app/tasks.py"
    "backend/celery_worker.py"
    "backend/Dockerfile.railway-worker"
    "backend/railway-worker-entrypoint.sh"
    "backend/verify_migrations.py"
    "backend/fix_jobs_table.sql"
    "backend/requirements.txt"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        success "Found $file"
    else
        error "Missing required file: $file"
    fi
done
echo ""

# Check 2: Python syntax validation
echo "🐍 Validating Python syntax..."
PYTHON_FILES=(
    "backend/config.py"
    "backend/app/__init__.py"
    "backend/app/routes.py"
    "backend/app/tasks.py"
    "backend/celery_worker.py"
    "backend/verify_migrations.py"
    "backend/troubleshoot.py"
)

for file in "${PYTHON_FILES[@]}"; do
    if python3 -m py_compile "$file" 2>/dev/null; then
        success "Valid syntax: $file"
    else
        error "Syntax error in: $file"
    fi
done
echo ""

# Check 3: Shell script syntax
echo "📜 Validating shell scripts..."
SHELL_SCRIPTS=(
    "backend/railway-worker-entrypoint.sh"
)

for script in "${SHELL_SCRIPTS[@]}"; do
    if bash -n "$script" 2>/dev/null; then
        success "Valid syntax: $script"
    else
        error "Syntax error in: $script"
    fi
done
echo ""

# Check 4: File permissions
echo "🔐 Checking file permissions..."
EXECUTABLE_FILES=(
    "backend/railway-worker-entrypoint.sh"
    "backend/verify_migrations.py"
    "backend/troubleshoot.py"
)

for file in "${EXECUTABLE_FILES[@]}"; do
    if [ -x "$file" ]; then
        success "Executable: $file"
    else
        warning "$file should be executable (chmod +x $file)"
    fi
done
echo ""

# Check 5: Environment variable template
echo "📝 Checking environment configuration..."
if [ -f "backend/.env.production.example" ]; then
    success "Found .env.production.example"
    
    # Check for required variables in template
    REQUIRED_VARS=(
        "DATABASE_URL"
        "SECRET_KEY"
        "JWT_SECRET_KEY"
        "GEMINI_API_KEY"
        "GOOGLE_CLIENT_ID"
        "GOOGLE_CLIENT_SECRET"
        "REDIS_URL"
        "CORS_ORIGINS"
    )
    
    for var in "${REQUIRED_VARS[@]}"; do
        if grep -q "^$var=" "backend/.env.production.example"; then
            success "Template has $var"
        else
            warning "Template missing $var"
        fi
    done
else
    error "Missing .env.production.example"
fi
echo ""

# Check 6: Docker files
echo "🐳 Checking Docker configuration..."
DOCKER_FILES=(
    "backend/Dockerfile.web"
    "backend/Dockerfile.worker"
    "backend/Dockerfile.railway-worker"
)

for dockerfile in "${DOCKER_FILES[@]}"; do
    if [ -f "$dockerfile" ]; then
        success "Found $dockerfile"
        # Basic validation
        if grep -q "FROM python" "$dockerfile"; then
            success "  Uses Python base image"
        else
            error "  Invalid base image in $dockerfile"
        fi
    else
        if [[ "$dockerfile" == *"Dockerfile.web"* ]]; then
            error "Missing required: $dockerfile"
        else
            warning "Missing optional: $dockerfile"
        fi
    fi
done
echo ""

# Check 7: Railway configuration
echo "🚂 Checking Railway configuration..."
if [ -f "backend/railway.json" ]; then
    success "Found backend/railway.json"
    # Validate JSON
    if python3 -c "import json; json.load(open('backend/railway.json'))" 2>/dev/null; then
        success "  Valid JSON syntax"
    else
        error "  Invalid JSON in railway.json"
    fi
else
    warning "Missing backend/railway.json (optional but recommended)"
fi

if [ -f "backend/railway.worker.json" ]; then
    success "Found backend/railway.worker.json"
    if python3 -c "import json; json.load(open('backend/railway.worker.json'))" 2>/dev/null; then
        success "  Valid JSON syntax"
    fi
else
    warning "Missing backend/railway.worker.json (optional)"
fi
echo ""

# Check 8: Dependencies
echo "📦 Checking requirements.txt..."
if [ -f "backend/requirements.txt" ]; then
    success "Found requirements.txt"
    
    REQUIRED_PACKAGES=(
        "Flask"
        "celery"
        "redis"
        "psycopg2-binary"
        "Flask-SQLAlchemy"
        "gunicorn"
    )
    
    for package in "${REQUIRED_PACKAGES[@]}"; do
        if grep -qi "^$package" "backend/requirements.txt"; then
            success "  Has $package"
        else
            error "  Missing $package in requirements.txt"
        fi
    done
else
    error "Missing requirements.txt"
fi
echo ""

# Check 9: Database migrations
echo "🗄️  Checking database migrations..."
if [ -d "backend/migrations" ]; then
    success "Found migrations directory"
    
    MIGRATION_COUNT=$(find backend/migrations/versions -name "*.py" ! -name "__pycache__" 2>/dev/null | wc -l)
    if [ "$MIGRATION_COUNT" -gt 0 ]; then
        success "  Found $MIGRATION_COUNT migration files"
    else
        warning "  No migration files found"
    fi
else
    error "Missing migrations directory"
fi
echo ""

# Check 10: Documentation
echo "📚 Checking deployment documentation..."
DOCS=(
    "docs/Deployment/RAILWAY_DEPLOYMENT.md"
    "docs/Deployment/RAILWAY_QUICK_CHECKLIST.md"
    "docs/Deployment/RAILWAY_ARCHITECTURE.md"
)

for doc in "${DOCS[@]}"; do
    if [ -f "$doc" ]; then
        success "Found $doc"
    else
        warning "Missing documentation: $doc"
    fi
done
echo ""

# Summary
echo "========================================"
echo "📊 Pre-Flight Check Summary"
echo "========================================"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! Ready to deploy.${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Review docs/Deployment/RAILWAY_QUICK_CHECKLIST.md"
    echo "  2. Ensure you have all environment variables ready"
    echo "  3. Deploy to Railway"
    echo "  4. Run verify_migrations.py after deployment"
    echo ""
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  $WARNINGS warnings found, but no errors.${NC}"
    echo "   You can proceed with deployment, but review warnings above."
    echo ""
    exit 0
else
    echo -e "${RED}❌ $ERRORS errors found!${NC}"
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}⚠️  $WARNINGS warnings found.${NC}"
    fi
    echo ""
    echo "Please fix the errors above before deploying."
    echo ""
    exit 1
fi
