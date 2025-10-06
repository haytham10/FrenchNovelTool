import os
import sys
import runpy

# Loader shim: execute the real backend/app/__init__.py inside this module's
# namespace so tests importing `app` get the actual create_app, db, and
# extension instances defined in backend/app.
ROOT = os.path.dirname(os.path.abspath(__file__))
backend_init = os.path.join(ROOT, 'backend', 'app', '__init__.py')

if os.path.isfile(backend_init):
    # Ensure sys.modules contains the current module under the name 'app'
    # so relative imports in the executed file resolve correctly.
    sys.modules['app'] = sys.modules.get(__name__, None) or sys.modules.setdefault('app', sys.modules.get(__name__))

    # Prepare package context for execution
    globals()['__package__'] = 'app'
    globals()['__path__'] = [os.path.dirname(backend_init)]

    # Execute the backend/app __init__.py in this module's globals so that
    # symbols defined there become available as if this were the real package.
    runpy.run_path(backend_init, init_globals=globals())
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
