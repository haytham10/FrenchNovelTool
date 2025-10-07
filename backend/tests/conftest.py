import os
import sys

# Ensure the repository root (parent of backend/) is on sys.path so tests
# can import the top-level `app` shim package (app/__init__.py).
HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(BACKEND_DIR)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Optionally expose global constants for tests
REPO_ROOT_PATH = REPO_ROOT
