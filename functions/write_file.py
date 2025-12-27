import os

from ._utils import normalize_path


def write_file(path: str, content: str, encoding: str = "utf-8") -> str:
    """Write content to a file at the specified path, creating any necessary directories."""
    norm = normalize_path(path)
    parent = os.path.dirname(norm)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)
    with open(norm, "w", encoding=encoding) as f:
        f.write(content)
    return f"Wrote {len(content)} bytes to {norm}"
