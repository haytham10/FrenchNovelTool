# Deployment Scripts

This directory contains utility scripts to help with deployment and validation.

## Available Scripts

### `validate-deployment-config.sh`

Validates that all deployment configuration files are in place and properly formatted.

**Usage:**
```bash
./scripts/validate-deployment-config.sh
```

**What it checks:**
- ✓ All deployment files exist (vercel.json, .env templates, etc.)
- ✓ JSON configuration files are valid
- ✓ YAML configuration files are valid
- ✓ Required dependencies are in requirements.txt
- ✓ Environment templates have correct settings
- ✓ Documentation is properly linked

**Exit codes:**
- `0` - All checks passed
- `1` - Errors found (deployment not ready)

Run this script before deploying to catch configuration issues early.
