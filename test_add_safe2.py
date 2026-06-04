import tarfile
from pathlib import Path
import os

os.makedirs("test_dir2/subdir", exist_ok=True)
with open("test_dir2/subdir/file.txt", "w") as f:
    f.write("content")

with tarfile.open("test2.tar.gz", "w:gz") as tar:
    def tar_filter(tarinfo): return tarinfo
    def _add_safe(path_to_add: Path, arc_name: str) -> None:
        if not path_to_add.exists(): return
        try:
            tar.add(path_to_add, arcname=arc_name, recursive=False, filter=tar_filter)
        except OSError: return
        if path_to_add.is_dir():
            for child in path_to_add.iterdir():
                _add_safe(child, f"{arc_name}/{child.name}")
    _add_safe(Path("test_dir2"), "test_dir2")

with tarfile.open("test2.tar.gz", "r:gz") as tar:
    for m in tar.getmembers():
        print(f"Member: {m.name} size: {m.size}")
