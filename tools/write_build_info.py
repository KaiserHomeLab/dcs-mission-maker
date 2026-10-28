"""Writes app/build_info.py for a release build: the GitHub repository (owner/name) whose
releases the Windows app's update check looks at. See app/updates.py.

    python tools/write_build_info.py owner/name
"""
import pathlib
import re
import sys

repo = sys.argv[1] if len(sys.argv) > 1 else ""
if not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
    raise SystemExit(f"Expected a GitHub repository like owner/name, got {repo!r}")
out = pathlib.Path(__file__).resolve().parent.parent / "app" / "build_info.py"
out.write_text(f'"""Written by tools/write_build_info.py for a release build."""\nREPO = {repo!r}\n', encoding="utf-8")
print(f"{out}: REPO = {repo}")
