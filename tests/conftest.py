import os, tempfile
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")   # never touch the real DB
os.environ.pop("ANTHROPIC_API_KEY", None)                             # tests are offline
