import os
from typing import Any, Dict, List

from ._utils import normalize_path


def get_file_info(path: str) -> Dict[str, Any]:
    """List non-recursive info for the given directory path.

    Returns structure:
    {
      "current_path": str,
      "items": [
         {"name": str, "path": str, "type": "file"|"directory", "extension": str|None, "size": int|None}
      ]
    }
    """
    norm = normalize_path(path)
    if not os.path.exists(norm):
        raise FileNotFoundError(f"Path does not exist: {norm}")
    if not os.path.isdir(norm):
        raise NotADirectoryError(f"Path is not a directory: {norm}")

    items: List[Dict[str, Any]] = []
    for name in sorted(os.listdir(norm)):
        child_path = os.path.join(norm, name)
        if os.path.isdir(child_path):
            items.append(
                {
                    "name": name,
                    "path": child_path,
                    "type": "directory",
                    "extension": None,
                    "size": None,
                }
            )
        elif os.path.isfile(child_path):
            _, ext = os.path.splitext(name)
            try:
                size = os.path.getsize(child_path)
            except OSError:
                size = None
            items.append(
                {
                    "name": name,
                    "path": child_path,
                    "type": "file",
                    "extension": ext[1:] if ext.startswith(".") else ext or None,
                    "size": size,
                }
            )
        # ignore symlinks/others for MVP
    return {"current_path": norm, "items": items}
