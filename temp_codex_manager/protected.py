import os
import shlex
import shutil

PROTECTED_DIRS = ["antigravity-cli"]

def get_tar_excludes():
    """Return a string of --exclude='name' arguments for tar commands."""
    return " ".join([f"--exclude={shlex.quote(name)}" for name in PROTECTED_DIRS])

def get_diff_excludes():
    """Return a string of -x 'name' arguments for diff commands."""
    return " ".join([f"-x {shlex.quote(name)}" for name in PROTECTED_DIRS])

def is_protected(name: str) -> bool:
    """Check if a file or directory name is protected."""
    return name in PROTECTED_DIRS

def copytree_excluding_protected(src: str, dst: str):
    """Copy a directory tree without protected top-level children."""
    return shutil.copytree(
        src,
        dst,
        symlinks=True,
        ignore=shutil.ignore_patterns(*PROTECTED_DIRS),
    )

def remove_protected_children(root: str):
    """Remove protected top-level children from a temporary tree."""
    for name in PROTECTED_DIRS:
        path = os.path.join(root, name)
        if not os.path.lexists(path):
            continue
        if os.path.isdir(path) and not os.path.islink(path):
            shutil.rmtree(path)
        else:
            os.remove(path)

class ProtectedPathManager:
    """Manages moving protected paths out of a target directory temporarily, then moving them back."""
    def __init__(self, target_dir: str):
        self.target_dir = target_dir
        self.parked_paths = {}

    def park_protected_paths(self):
        """Move protected paths out of the target_dir to a safe temporary sibling location."""
        if not os.path.exists(self.target_dir):
            return

        parent_dir = os.path.dirname(os.path.abspath(self.target_dir))
        target_basename = os.path.basename(os.path.abspath(self.target_dir))

        for name in PROTECTED_DIRS:
            src_path = os.path.join(self.target_dir, name)
            if os.path.lexists(src_path):
                safe_dest = os.path.join(parent_dir, f".{target_basename}.{name}.protected-tmp")
                if os.path.exists(safe_dest):
                    # Clean up orphaned temp dir from a previous failed run
                    if os.path.isdir(safe_dest) and not os.path.islink(safe_dest):
                        shutil.rmtree(safe_dest)
                    else:
                        os.remove(safe_dest)

                shutil.move(src_path, safe_dest)
                self.parked_paths[name] = safe_dest

    def restore_protected_paths(self):
        """Move parked paths back into the target_dir."""
        for name, safe_dest in self.parked_paths.items():
            if os.path.exists(safe_dest):
                dest_path = os.path.join(self.target_dir, name)
                # If for some reason dest_path exists, remove it first
                if os.path.exists(dest_path):
                    if os.path.isdir(dest_path) and not os.path.islink(dest_path):
                        shutil.rmtree(dest_path)
                    else:
                        os.remove(dest_path)

                os.makedirs(self.target_dir, exist_ok=True)
                shutil.move(safe_dest, dest_path)
        self.parked_paths.clear()

    def cleanup(self):
        """Attempt to restore parked paths instead of destroying them if we abort."""
        self.restore_protected_paths()
