import tarfile
from pathlib import Path
import threading
import time
import os

os.makedirs("test_dir", exist_ok=True)
with open("test_dir/active.log", "w") as f:
    f.write("A" * 1024 * 1024 * 10) # 10MB

def modify_file():
    time.sleep(0.005)
    with open("test_dir/active.log", "w") as f:
        f.write("B")

t = threading.Thread(target=modify_file)
t.start()

try:
    with tarfile.open("test.tar.gz", "w:gz") as tar:
        def _add_safe(p: Path, arc: str):
            if not p.exists(): return
            try:
                tar.add(p, arcname=arc, recursive=False)
            except OSError as e:
                print(f"Skipped {p} due to error: {e}")
                return
            if p.is_dir():
                try:
                    children = list(p.iterdir())
                except OSError:
                    return
                for c in children:
                    _add_safe(c, f"{arc}/{c.name}")
        _add_safe(Path("test_dir"), "test_dir")
    print("Success with safe method")
except Exception as e:
    print(f"Failed with {type(e).__name__}: {e}")
t.join()
