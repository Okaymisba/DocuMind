import os

from ._utils import normalize_path


def read_file(path: str, encoding: str = "utf-8") -> str:
    norm = normalize_path(path)
    if not os.path.exists(norm):
        raise FileNotFoundError(f"File does not exist: {norm}")
    if not os.path.isfile(norm):
        raise IsADirectoryError(f"Not a file: {norm}")
    with open(norm, "r", encoding=encoding) as f:
        return f.read()
