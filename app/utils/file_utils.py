import os

def list_files(base_path: str):
    """Recursively list all files in repo (excluding noise)"""
    ignored = {".git", "__pycache__", "node_modules", ".venv", "env"}
    files = []
    for root, dirs, filenames in os.walk(base_path):
        dirs[:] = [d for d in dirs if d not in ignored]
        for fname in filenames:
            rel_path = os.path.relpath(os.path.join(root, fname), base_path)
            files.append(rel_path)
    return files
