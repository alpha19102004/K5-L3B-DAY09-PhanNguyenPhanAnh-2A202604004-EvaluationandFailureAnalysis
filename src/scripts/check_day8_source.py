"""Verify the frozen Day 8 source against the imported upstream manifest."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / "config/day8_source.json").read_text(encoding="utf-8"))
problems = []
for relative, expected in manifest["files"].items():
    path = root / relative
    if not path.is_file():
        problems.append(f"missing {relative}")
    elif hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest() != expected:
        problems.append(f"changed {relative}")
extra = {p.relative_to(root).as_posix() for p in (root / "lab8").rglob("*.py")} - manifest["files"].keys()
problems += [f"unexpected {p}" for p in sorted(extra)]
result = {"passed": not problems, "repository": manifest["repository"], "commit": manifest["commit"],
          "checked_files": len(manifest["files"]), "problems": problems}
(root / "reports").mkdir(exist_ok=True)
(root / "reports/source_integrity.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
print(f"Day 8 source: {len(manifest['files'])} files, {len(problems)} changes; commit {manifest['commit']}")
for problem in problems:
    print(problem)
raise SystemExit(1 if problems else 0)
