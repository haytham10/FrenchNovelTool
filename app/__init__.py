import os
import sys
import runpy

# Loader shim: execute the real backend/app/__init__.py inside this module's
# namespace so tests importing `app` get the actual create_app, db, and
# extension instances defined in backend/app.
ROOT = os.path.dirname(os.path.abspath(__file__))
# Repo root is one level above this `app/` shim directory
REPO_ROOT = os.path.dirname(ROOT)
backend_init = os.path.join(REPO_ROOT, 'backend', 'app', '__init__.py')

# Ensure backend package root is on sys.path so imports like `from config import Config`
# (which expect `backend/config.py`) resolve when we execute the backend package
backend_pkg_dir = os.path.join(REPO_ROOT, 'backend')
if backend_pkg_dir not in sys.path:
    sys.path.insert(0, backend_pkg_dir)

if os.path.isfile(backend_init):
    # Ensure sys.modules contains the current module object under the name 'app'
    # so relative imports in the executed file resolve correctly.
    # Set explicitly to avoid accidentally inserting a None value.
    sys.modules['app'] = sys.modules.get(__name__)

    # Prepare package context for execution
    globals()['__package__'] = 'app'
    globals()['__path__'] = [os.path.dirname(backend_init)]

    # Load backend/app/__init__.py as module 'app' using importlib so
    # it is treated as a proper package and relative imports work.
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        'app', backend_init, submodule_search_locations=[os.path.dirname(backend_init)]
    )
    backend_module = importlib.util.module_from_spec(spec)

    # Put the backend module into sys.modules under the name 'app' so
    # imports reference the correct module object during execution.
    sys.modules['app'] = backend_module

    # Set package attributes expected by import machinery
    backend_module.__file__ = backend_init
    backend_module.__package__ = 'app'
    backend_module.__path__ = spec.submodule_search_locations

    # Execute the backend module
    spec.loader.exec_module(backend_module)

    # Copy non-private attributes into this shim's globals so modules that
    # imported this shim earlier still see expected symbols (create_app, db, etc.)
    for name, value in backend_module.__dict__.items():
        if name.startswith('_'):
            continue
        globals()[name] = value
else:
    # If the backend package isn't where we expect, leave this shim minimal;
    # imports will fail and tests will show the mismatch.
    pass

# If the real Celery instance wasn't created (e.g., create_app wasn't called
# at import time), provide a dummy object with a `.task` decorator so modules
# that use `@get_celery().task(...)` at import time don't crash during tests.
if globals().get('celery') is None:
    class _DummyCelery:
        def task(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator

    celery = _DummyCelery()
    globals()['celery'] = celery
