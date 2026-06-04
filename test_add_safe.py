import tarfile
from pathlib import Path
import os

os.makedirs("test_brain/conv1", exist_ok=True)
with open("test_brain/conv1/project_analysis.md", "w") as f:
    f.write("hello")

with tarfile.open("test.tar.gz", "w:gz") as tar:
    def tar_filter(tarinfo): return tarinfo
    def _add_safe(path_to_add: Path, arc_name: str) -> None:
        if not path_to_add.exists(): return
        try:
            tar.add(path_to_add, arcname=arc_name, recursive=False, filter=tar_filter)
        except OSError: return
        if path_to_add.is_dir():
            for child in path_to_add.iterdir():
                _add_safe(child, f"{arc_name}/{child.name}")
    _add_safe(Path("test_brain"), "test_brain")

with tarfile.open("test.tar.gz", "r:gz") as tar:
    tar.list()
