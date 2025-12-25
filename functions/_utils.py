import os


def normalize_path(path: str) -> str:
    return os.path.abspath(os.path.expanduser(path))
