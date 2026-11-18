"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from numbers import Real
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, aggregate, load_spec, per_item
from lab9.graders import GRADERS


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    problems = []
    metric_defs = spec.get("metrics", [])
    ids = [m["id"] for m in metric_defs]
    if len(ids) != len(set(ids)):
        problems.append("duplicate metric ids in spec")
    graded = {m["id"] for m in metric_defs if m["id"] in GRADERS or m.get("grader") == "code"}

    def finite(value):
        return isinstance(value, Real) and math.isfinite(value)

    def inspect(rep, name):
        manifest, rows, metrics = rep.get("manifest", {}), rep.get("rows"), rep.get("metrics", {})
        if not isinstance(rows, list) or not rows or not isinstance(metrics, dict):
            problems.append(f"{name}: missing rows or metrics")
            return {}, set()
        if "evaluator_failures" not in rep or rep["evaluator_failures"]:
            problems.append(f"{name}: evaluator_failures must be present and empty")
        for mid, value in metrics.items():
            if not finite(value):
                problems.append(f"{name}: {mid} summary is missing/non-finite")
        seeds, count = manifest.get("seeds", []), manifest.get("items")
        if (not seeds or any(type(s) is not int for s in seeds)
                or len(set(seeds)) != len(seeds) or type(count) is not int or count < 1):
            problems.append(f"{name}: invalid item/seed manifest")
            return {}, set()
        if len(rows) != count * len(seeds):
            problems.append(f"{name}: row count {len(rows)} != {count} x {len(seeds)}")
        pairs, tags, by_item = [], {}, {}
        row_metrics = graded if name == "PR" else graded & metrics.keys()
        invalid_values = False
        for index, row in enumerate(rows):
            if not isinstance(row, dict) or not isinstance(row.get("item_id"), str) or type(row.get("seed")) is not int:
                problems.append(f"{name}: invalid row identity at {index}")
                invalid_values = True
                continue
            item, seed = row["item_id"], row["seed"]
            pairs.append((item, seed))
            by_item.setdefault(item, set()).add(seed)
            slices = row.get("slices", [])
            if not isinstance(slices, list) or any(not isinstance(s, str) for s in slices):
                problems.append(f"{name}: invalid slices at {item}@{seed}")
                continue
            tag = frozenset(slices)
            if item in tags and tags[item] != tag:
                problems.append(f"{name}: inconsistent slice tags for {item}")
            tags[item] = tag
            for mid in row_metrics:
                value = row.get(mid)
                if not finite(value) or value not in (0, 1):
                    problems.append(f"{name}: invalid/missing graded value {mid} at {item}@{seed}")
                    invalid_values = True
            if ("cost" in row or "cost_per_success" in metrics) and (not finite(row.get("cost")) or row["cost"] < 0):
                problems.append(f"{name}: invalid cost at {item}@{seed}")
                invalid_values = True
        if any(n != 1 for n in Counter(pairs).values()):
            problems.append(f"{name}: duplicate (item_id, seed) rows")
        if len(by_item) != count or any(values != set(seeds) for values in by_item.values()):
            problems.append(f"{name}: rows do not cover the declared item x seed product")
        # A forged green summary cannot override red evidence in the rows.
        if not invalid_values:
            k_values = set(spec.get("pass_k", []))
            for mid in metrics:
                if mid.startswith(("pass_at_", "pass_hat_")) and mid.rsplit("_", 1)[-1].isdigit():
                    k_values.add(int(mid.rsplit("_", 1)[-1]))
            if "pass_rate" in row_metrics:
                calculated = aggregate([{**r, "cost": r.get("cost", 0)} for r in rows],
                                       sorted(row_metrics), sorted(k_values))
                for mid, value in calculated.items():
                    if mid in metrics and finite(metrics[mid]) and (not finite(value) or abs(metrics[mid] - value) > 1e-8):
                        problems.append(f"{name}: {mid} summary disagrees with rows")
        return tags, set(pairs)

    pr_tags, pr_pairs = inspect(pr, "PR")
    base_tags, base_pairs = inspect(base, "baseline")
    if pr_pairs != base_pairs:
        problems.append("PR (item_id, seed) set differs from baseline")
    if pr.get("manifest", {}).get("items") != base.get("manifest", {}).get("items"):
        problems.append("PR item count differs from baseline")
    if set(pr.get("manifest", {}).get("seeds", [])) != set(base.get("manifest", {}).get("seeds", [])):
        problems.append("PR seeds differ from baseline")
    if spec.get("seeds") and set(pr.get("manifest", {}).get("seeds", [])) != set(spec["seeds"]):
        problems.append("PR seeds differ from spec")
    if pr_tags != base_tags:
        problems.append("PR item slice tags differ from baseline")
    if pr.get("manifest", {}).get("labels_sha") != base.get("manifest", {}).get("labels_sha"):
        problems.append("PR labels differ from baseline")
    for mid in ids:
        if mid not in pr.get("metrics", {}):
            problems.append(f"PR: missing spec metric {mid}")

    if base_spec and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        def ratchet(old_entries, new_entries, key, threshold):
            new = {key(entry): entry for entry in new_entries}
            for old in old_entries:
                label = str(key(old))
                current = new.get(key(old))
                if current is None:
                    problems.append(f"ratchet: removed {label}")
                    continue
                if old.get("blocking") and not current.get("blocking"):
                    problems.append(f"ratchet: disabled blocking for {label}")
                before, after = threshold(old), threshold(current)
                for bound in ("min", "max", "max_increase"):
                    if bound in before and (bound not in after or not finite(after[bound]) or
                            (after[bound] < before[bound] if bound == "min" else after[bound] > before[bound])):
                        problems.append(f"ratchet: loosened {bound} for {label}")
                if before.get("no_significant_drop") and not after.get("no_significant_drop"):
                    problems.append(f"ratchet: dropped no_significant_drop for {label}")
        ratchet(base_spec.get("metrics", []), metric_defs, lambda m: m["id"], lambda m: m.get("threshold", {}))
        ratchet(base_spec.get("slices", []), spec.get("slices", []),
                lambda s: (s["name"], s["metric"]), lambda s: s)
    return list(dict.fromkeys(problems))


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for entry in spec.get("slices", []):
        name, mid = entry["name"], entry["metric"]
        identifier = f"slice:{name}/{mid}"
        a, b = per_item(pr, mid, name), per_item(base, mid, name)
        failed, note, value = False, "", None
        if not a or set(a) != set(b):
            failed, note = True, "missing or unpaired slice items"
        else:
            keys = sorted(a)
            value = sum(a.values()) / len(a)
            failed = ("min" in entry and value < entry["min"]) or ("max" in entry and value > entry["max"])
            if entry.get("no_significant_drop"):
                d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                    n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                    confidence=bs.get("confidence", 0.95))
                note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                failed = failed or hi < 0
        if failed and entry.get("blocking"):
            blocked.append(identifier)
        verdict = ("BLOCK" if entry.get("blocking") else "warn") if failed else "ok"
        lines.append(f"  {identifier:<36} {value!s:<20} {note:<28} {verdict}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if not pr.get("manifest", {}).get("eval_set_sha") or not base.get("manifest", {}).get("eval_set_sha"):
        return ["integrity"], ["  INTEGRITY missing eval-set identity"]
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid) is not None:
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(a)
            if not keys or set(a) != set(b):
                if m.get("blocking"):
                    blocked.append(mid)
                lines.append(f"  {mid}: missing paired item values")
                continue
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                                               confidence=bs.get("confidence", 0.95))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
