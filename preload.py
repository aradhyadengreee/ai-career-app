# preload.py
"""
Preload embedding model + vector DB at Docker build time.

This script will:
- set CHROMA / cache dirs to /app/chroma-db (so they are baked into the image)
- attempt to call common initializer functions in vector_db.py (robust to different names/signatures)
- fail (exit 1) if none of the heuristics worked so the build stops and you can fix things.
"""

import os
import sys
import importlib
import inspect
import traceback

# ensure deterministic places for caches and DB
os.environ.setdefault("CHROMA_DB_DIR", "/app/chroma-db")
os.environ.setdefault("CHROMA_HOME", "/app/chroma-db")
os.environ.setdefault("TRANSFORMERS_CACHE", "/root/.cache/huggingface/transformers")
os.environ.setdefault("HF_HOME", "/root/.cache/huggingface")
os.environ.setdefault("TORCH_HOME", "/root/.cache/torch")

# make sure dirs exist
os.makedirs("/app/chroma-db", exist_ok=True)
os.makedirs("/root/.cache", exist_ok=True)

DATA_PATH_GUESS = "/app/careers_data.xlsx"   # your .xlsx in repo (adjust if different)
CHROMA_DIR_GUESS = "/app/chroma-db"

print("Preload started. CHROMA_DB_DIR=", os.environ.get("CHROMA_DB_DIR"))
print("Looking for vector_db module...")

try:
    vector_db = importlib.import_module("vector_db")
except Exception as e:
    print("ERROR: could not import vector_db.py from project root:", e)
    traceback.print_exc()
    sys.exit(1)

# helper to call a function with best-effort args
def try_call(fn):
    sig = None
    try:
        sig = inspect.signature(fn)
    except Exception:
        sig = None

    kwargs = {}
    if sig:
        params = sig.parameters
        # common parameter names we've seen: data_path, datafile, data_file, path, chroma_dir, persist_directory, persist_dir
        if "data_path" in params:
            kwargs["data_path"] = DATA_PATH_GUESS
        if "datafile" in params or "data_file" in params:
            key = "datafile" if "datafile" in params else "data_file"
            kwargs[key] = DATA_PATH_GUESS
        if "path" in params and "data" in str(params):
            kwargs["path"] = DATA_PATH_GUESS
        if "chroma_dir" in params:
            kwargs["chroma_dir"] = CHROMA_DIR_GUESS
        if "persist_directory" in params:
            kwargs["persist_directory"] = CHROMA_DIR_GUESS
        if "persist_dir" in params:
            kwargs["persist_dir"] = CHROMA_DIR_GUESS
    # try call with kwargs; fallback to no-arg call
    try:
        print(f"Attempting call {fn.__name__} with kwargs: {kwargs}")
        return fn(**kwargs) if kwargs else fn()
    except TypeError as te:
        # maybe the function expects no args
        try:
            print(f"Retrying {fn.__name__} with no args (got TypeError): {te}")
            return fn()
        except Exception as e2:
            print(f"Failed calling {fn.__name__}: {e2}")
            traceback.print_exc()
            raise

# candidate function names to try (ordered preference)
candidates = [
    "create_vector_db",
    "create_db",
    "build_vector_db",
    "init_vector_db",
    "build_chroma",
    "create_chroma",
    "init_chroma",
    "create_and_populate",
    "prepare_vectorstore",
    "main",
    "run",
]

succeeded = False
for name in candidates:
    fn = getattr(vector_db, name, None)
    if callable(fn):
        try:
            print(f"Found function {name} in vector_db.py, invoking...")
            try_call(fn)
            print(f"Function {name} succeeded.")
            succeeded = True
            break
        except Exception:
            print(f"Function {name} raised an error; trying next candidate.")
            continue

# If candidate names didn't exist, search for any callable that looks like it builds DB
if not succeeded:
    print("No canonical initializer found — searching for any callable in vector_db module to try...")
    for attr in dir(vector_db):
        if attr.startswith("_"):
            continue
        obj = getattr(vector_db, attr)
        if callable(obj) and attr.lower().startswith(("create", "build", "init", "prepare")):
            try:
                print(f"Trying discovered candidate {attr}()")
                try_call(obj)
                print(f"{attr} succeeded.")
                succeeded = True
                break
            except Exception:
                print(f"{attr} failed; continuing search.")
                continue

if not succeeded:
    print("\nCould not find or run any initializer in vector_db.py automatically.")
    print("Please either:")
    print(" - add a function named `create_vector_db(data_path, chroma_dir)` in vector_db.py (recommended), or")
    print(" - ensure vector_db.py has a callable `main()` or `create_db()` that builds the embed model and persists the DB.")
    sys.exit(1)

print("Preload finished successfully.")
