#!/bin/bash
# Deployment Configuration Validator
# This script validates that all necessary files and configurations are in place for deployment

set -e

echo "🔍 Validating Deployment Configuration..."
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

# Helper functions
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1 exists"
    else
        echo -e "${RED}✗${NC} $1 is missing"
        ERRORS=$((ERRORS + 1))
    fi
}

check_json() {
    if python -m json.tool "$1" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $1 is valid JSON"
    else
        echo -e "${RED}✗${NC} $1 has invalid JSON syntax"
        ERRORS=$((ERRORS + 1))
    fi
}

check_yaml() {
    if python -c "import yaml; yaml.safe_load(open('$1'))" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $1 is valid YAML"
    else
        echo -e "${RED}✗${NC} $1 has invalid YAML syntax"
        ERRORS=$((ERRORS + 1))
    fi
}

check_dependency() {
    if grep -q "$1" "$2"; then
        echo -e "${GREEN}✓${NC} $1 is in $2"
    else
        echo -e "${YELLOW}⚠${NC} $1 not found in $2"
        WARNINGS=$((WARNINGS + 1))
    fi
}

echo "📄 Checking deployment files..."
check_file "backend/vercel.json"
check_file "frontend/vercel.json"
check_file "backend/.env.production.example"
check_file "frontend/.env.production.example"
check_file "backend/.vercelignore"
check_file "frontend/.vercelignore"
check_file "DEPLOYMENT.md"
check_file "DEPLOYMENT_CHECKLIST.md"
check_file "DEPLOYMENT_QUICKSTART.md"

echo ""
echo "🔧 Validating JSON configurations..."
if [ -f "backend/vercel.json" ]; then
    check_json "backend/vercel.json"
fi
if [ -f "frontend/vercel.json" ]; then
    check_json "frontend/vercel.json"
fi

echo ""
echo "📦 Checking backend dependencies..."
check_dependency "psycopg2-binary" "backend/requirements.txt"
check_dependency "Flask" "backend/requirements.txt"
check_dependency "Flask-SQLAlchemy" "backend/requirements.txt"
check_dependency "gunicorn" "backend/requirements.txt"

echo ""
echo "🐳 Validating Docker configurations..."
check_yaml "docker-compose.yml"
check_yaml "docker-compose.dev.yml"

echo ""
echo "🔐 Checking environment templates..."
if [ -f "backend/.env.production.example" ]; then
    if grep -q "DATABASE_URL=postgresql://" "backend/.env.production.example"; then
        echo -e "${GREEN}✓${NC} Backend env template has PostgreSQL URL format"
    else
        echo -e "${YELLOW}⚠${NC} Backend env template may not have correct PostgreSQL URL format"
        WARNINGS=$((WARNINGS + 1))
    fi
    
    if grep -q "CORS_ORIGINS=https://frenchnoveltool.com" "backend/.env.production.example"; then
        echo -e "${GREEN}✓${NC} Backend env template has production CORS setting"
    else
        echo -e "${YELLOW}⚠${NC} Backend env template may not have correct CORS setting"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

if [ -f "frontend/.env.production.example" ]; then
    if grep -q "NEXT_PUBLIC_API_BASE_URL=https://api.frenchnoveltool.com" "frontend/.env.production.example"; then
        echo -e "${GREEN}✓${NC} Frontend env template has production API URL"
    else
        echo -e "${YELLOW}⚠${NC} Frontend env template may not have correct API URL"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

echo ""
echo "📚 Checking documentation..."
if grep -q "DEPLOYMENT.md" "README.md"; then
    echo -e "${GREEN}✓${NC} README references deployment documentation"
else
    echo -e "${YELLOW}⚠${NC} README may not reference deployment documentation"
    WARNINGS=$((WARNINGS + 1))
fi

echo ""
echo "================================"
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo "Ready for deployment."
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ ${WARNINGS} warning(s) found${NC}"
    echo "Deployment configuration is mostly ready, but review warnings above."
    exit 0
else
    echo -e "${RED}❌ ${ERRORS} error(s) and ${WARNINGS} warning(s) found${NC}"
    echo "Please fix the errors above before deploying."
    exit 1
fi
