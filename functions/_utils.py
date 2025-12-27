import os


def normalize_path(path: str) -> str:
    """Normalize the given path to an absolute path, expanding any user shortcuts."""
    return os.path.abspath(os.path.expanduser(path))
