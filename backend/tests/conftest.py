import os
import sys

# Ensure the backend root is on sys.path so `from app import app` works
BACKEND_ROOT = os.path.dirname(os.path.dirname(__file__))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)
