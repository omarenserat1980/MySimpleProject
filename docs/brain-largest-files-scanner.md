# Brain Largest Files Scanner

A read-only utility for finding the largest files in a directory. It can scan a local Downloads folder when run on a device that has access to that folder, or scan a mounted/downloaded directory in a cloud runner.

## Run

```bash
# Auto-detect a common Downloads path
python tools/brain_largest_files.py

# Explicit path (recommended when using Termux or a cloud runner)
python tools/brain_largest_files.py --root "$HOME/storage/downloads"

# Show the 10 largest files
python tools/brain_largest_files.py --root "$HOME/Downloads" --limit 10

# Machine-readable report
python tools/brain_largest_files.py --root "$HOME/Downloads" --json

# CSV output
python tools/brain_largest_files.py --root "$HOME/Downloads" --csv

# Include hidden files/directories
python tools/brain_largest_files.py --root "$HOME/Downloads" --include-hidden
```

## Safety and evidence

- Read-only: never deletes, moves, or modifies scanned files.
- Does not follow symbolic links.
- Sorts by byte size descending; ties are ordered deterministically by path.
- Reports unreadable paths as warnings instead of silently claiming a complete scan.
- JSON includes the scan root, number of regular files scanned, warnings, and top results.
- A cloud runner can only scan files actually present or mounted in that runner. It cannot inspect a disconnected phone's private Downloads folder merely by running this script in CI.

## Tests

```bash
python -m pytest -q tests/test_brain_largest_files.py
```
