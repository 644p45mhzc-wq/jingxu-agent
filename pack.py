"""Build a distributable zip.

    python pack.py              # for teammates: keeps .git so they can read history
    python pack.py --no-git     # for delivery: drops .git too

Always excluded: virtual environments, caches, and .env (the real key).
.env.example ships instead. Note that .env is excluded by name, but a key
committed earlier is still recoverable from .git history, so rotate the key
rather than relying on this script to hide it.
"""
import os
import sys
import zipfile

SKIP_DIRS = {'.venv', '.venv-local', '.venv-run', '.venv-local-unix',
             '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache',
             '.claude', '.tmptest', '.idea', '.vscode', 'data'}
SKIP_FILES = {'.env', '.DS_Store'}
SKIP_SUFFIXES = ('.pyc', '.pyo', '.zip', '.log', '.db', '.sqlite3', '.sqlite3-wal', '.sqlite3-shm')
NAME = 'aiopc_v3'


def excluded_directory(path, name, skip_dirs):
    return (name in skip_dirs or name.startswith('.venv')
            or os.path.isfile(os.path.join(path, name, 'pyvenv.cfg')))


def build(drop_git):
    root = os.path.dirname(os.path.abspath(__file__))
    skip_dirs = SKIP_DIRS | ({'.git'} if drop_git else set())
    target = os.path.join(os.path.dirname(root), f'{NAME}{"_交付" if drop_git else "_给队友"}.zip')
    count = 0
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not excluded_directory(dirpath, d, skip_dirs)]
            for name in sorted(filenames):
                if name in SKIP_FILES or (name.startswith('.env.') and name != '.env.example') or name.endswith(SKIP_SUFFIXES):
                    continue
                full = os.path.join(dirpath, name)
                bundle.write(full, os.path.join(NAME, os.path.relpath(full, root)))
                count += 1
    size = os.path.getsize(target) / 1024
    print(f'{target}\n  {count} 个文件，{size:.0f} KB')
    leaked = [n for n in zipfile.ZipFile(target).namelist() if os.path.basename(n) == '.env']
    print('  .env：', leaked or '未包含（正确）')
    print('  .git：', '已排除' if drop_git else '已包含（旧密钥可从历史还原，务必轮换）')


if __name__ == '__main__':
    build('--no-git' in sys.argv)
