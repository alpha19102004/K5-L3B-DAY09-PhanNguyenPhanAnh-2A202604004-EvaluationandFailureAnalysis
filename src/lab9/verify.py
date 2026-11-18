"""Reproduce the complete M0-M7 submission and preserve its machine-generated evidence.

Run from src/: python -m lab9.verify
Reports and logs are produced here; no report is edited by hand.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from lab8.console import utf8_stdio


def write_json(path: str, value) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def collect_evidence() -> None:
    import tempfile

    from lab8.shapes import SHAPES
    from lab9 import gate, stats
    from lab9.eval import load_spec, load_world, make_task, per_item
    from lab9.graders import GRADERS
    from lab9.judge import calibrate
    from lab9.mutation import detect
    from lab9.variant_agent import make_shape
    from pydantic_evals.evaluators import EvaluatorContext

    spec = load_spec()
    v2 = load_spec(Path("config/metric_spec_v2.yaml"))
    read = lambda name: json.loads(Path(name).read_text(encoding="utf-8"))
    base = read("reports/baseline_v1.json")
    baseline2 = read("reports/baseline_v2.json")
    comparisons = {}
    for name in ("fixed", "seeded_regression"):
        report = read(f"reports/eval_{name}.json")
        a, b = per_item(report, "pass_rate"), per_item(base, "pass_rate")
        keys = sorted(a)
        comparisons[name] = {"run_id": report["run_id"], "baseline_run_id": base["run_id"],
            "pass_rate_delta_ci": stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys]),
            "blocked": gate.check(report, base, spec, spec)[0]}
    det, fa = detect(spec)
    aa = read("reports/aa_v2.json")
    deltas = {key: round(value - baseline2["metrics"][key], 8) for key, value in aa["metrics"].items()}
    checks = {}
    for name in ("fixed", "honest_refactor", "seeded_regression", "slice_regression", "flaky_regression"):
        report = read(f"reports/eval_{name}_v2.json")
        blocked, lines = gate.check(report, baseline2, v2, v2)
        checks[name] = {"run_id": report["run_id"], "metrics": report["metrics"],
                        "blocked": blocked, "gate_lines": lines}
    write_json("reports/analysis.json", {"core": comparisons, "detection": det, "false_alarm_rate": fa,
        "judge_tone": calibrate(Path("data/eval/judge_tone_public.csv")),
        "judge_helpful": calibrate(Path("data/eval/judge_helpful_public.csv")),
        "aa": {"spec_seeds": v2["seeds"], "alternate_seeds": aa["manifest"]["seeds"], "deltas": deltas},
        "v2": checks})

    probes = [
        ("FM-01", "C-001", {"no_override", "leaky_trace"}, "debug_claim_row"),
        ("FM-02", "C-007", {"no_override", "ignore_denied"}, "reply"),
        ("FM-03", "C-002", {"ticket_trust"}, "model_override"),
        ("FM-04", "C-014", {"no_override", "sum_parts"}, "proposal"),
        ("FM-05", "C-014", {"no_override", "pre_deducted"}, "proposal"),
        ("FM-06", "C-006", {"no_override", "stale_clause"}, "quote"),
        ("FM-07", "C-010", {"no_override", "sibling_refund"}, "batch_refund"),
        ("FM-08", "C-008", {"no_override", "misreport"}, "reply"),
        ("FM-09", "C-110", {"no_override"}, None),
    ]
    world, claims = load_world(v2)
    labels = read(v2["labels"])
    evidence = {}
    with tempfile.TemporaryDirectory(prefix="lab9-evidence-", ignore_cleanup_errors=True) as tmp:
        for fm, claim, switches, first_kind in probes:
            name = f"taxonomy_{fm.lower()}"
            shape = make_shape(name, switches)
            SHAPES[name] = shape
            try:
                trial = make_task(name, world, claims, labels, Path(tmp))({"claim_id": claim, "seed": 11})
                ctx = EvaluatorContext(name=f"{claim}@11", inputs={}, metadata=None,
                    expected_output=labels[claim], output=trial, duration=0.0, _span_tree=None, attributes={}, metrics={})
                grades = {key: {"value": (result := cls().evaluate(ctx)).value, "reason": result.reason}
                          for key, cls in GRADERS.items()}
                evidence[fm] = {"claim_id": claim, "seed": 11, "shape": name, "switches": sorted(switches),
                    "first_wrong_step": next((i for i, e in enumerate(trial["events"], 1) if e["kind"] == first_kind), None),
                    "label": labels[claim], "result": trial["result"], "snapshot": trial["snapshot"],
                    "unexpected_rows": trial["unexpected_rows"], "events": trial["events"], "grades": grades}
            finally:
                SHAPES.pop(name, None)
    write_json("reports/taxonomy_evidence.json", evidence)


def main() -> int:
    utf8_stdio()
    if not Path("lab9").is_dir():
        raise SystemExit("Run this command from src/.")
    Path("reports/logs").mkdir(parents=True, exist_ok=True)
    outcomes = []

    def command(name, args, expected=0):
        print(f"[{name}] python {' '.join(args)}", flush=True)
        completed = subprocess.run([sys.executable, *args], capture_output=True, text=True,
            encoding="utf-8", errors="replace", env={**os.environ, "PYTHONUTF8": "1"})
        output = completed.stdout + completed.stderr
        Path(f"reports/logs/{name}.txt").write_text(output, encoding="utf-8")
        outcomes.append({"name": name, "command": "python " + " ".join(args),
                         "expected_exit": expected, "actual_exit": completed.returncode,
                         "ok": completed.returncode == expected})
        print(f"  exit {completed.returncode} (expected {expected})", flush=True)
        if completed.returncode != expected:
            print(output, flush=True)
            write_json("reports/verification.json", {"passed": False, "commands": outcomes})
            raise RuntimeError(f"verification stopped at {name}")

    command("smoke", ["-m", "lab9.smoke"])
    command("evalset_v1", ["-m", "lab9.evalset", "--build", "--check"])
    command("evalset_v2", ["-m", "lab9.evalset", "--v2", "--build"])
    command("source_integrity", ["scripts/check_day8_source.py"])
    command("host_tests", ["-m", "pytest", "-q"])
    command("lab9_tests", ["-m", "pytest", "-q", "-m", "student", "-o", "addopts=", "-k", "lab9"])
    command("tone", ["-m", "lab9.judge", "--csv", "data/eval/judge_tone_public.csv", "--audit", "10"])
    command("helpful", ["-m", "lab9.judge", "--csv", "data/eval/judge_helpful_public.csv", "--audit", "10"], 1)
    for version, spec_path in (("v1", "config/metric_spec.yaml"), ("v2", "config/metric_spec_v2.yaml")):
        shapes = ["swarm", "fixed", "seeded_regression"]
        if version == "v2":
            shapes += ["honest_refactor", "slice_regression", "flaky_regression"]
        for shape in shapes:
            target = f"reports/baseline_{version}.json" if shape == "swarm" else f"reports/eval_{shape}{'_v2' if version == 'v2' else ''}.json"
            command(f"eval_{shape}_{version}", ["-m", "lab9.eval", "--shape", shape, "--spec", spec_path, "--out", target])
            command(f"gate_{shape}_{version}", ["-m", "lab9.gate", "--pr", target,
                "--baseline", f"reports/baseline_{version}.json", "--spec", spec_path, "--base-spec", spec_path],
                1 if shape in ("seeded_regression", "slice_regression", "flaky_regression") else 0)
    command("ci_baseline", ["-m", "lab9.ci_check", "--pr", "reports/baseline_v1.json",
        "--baseline", "reports/baseline_v1.json"])
    command("detection", ["-m", "lab9.mutation", "--detect"])
    command("aa_report", ["-m", "lab9.eval", "--shape", "swarm", "--spec", "config/metric_spec_v2.yaml",
        "--seeds", "66,77,88,99,110", "--out", "reports/aa_v2.json"])
    command("aa", ["-m", "lab9.mutation", "--spec", "config/metric_spec_v2.yaml", "--aa", "66,77,88,99,110"])
    command("mutation", ["-m", "lab9.mutation", "--spec", "config/metric_spec_v2.yaml",
        "--baseline", "reports/baseline_v2.json", "--base-spec", "config/metric_spec_v2.yaml"])
    command("traps", ["-m", "lab9.traps", "--pr", "reports/eval_slice_regression_v2.json",
        "--baseline", "reports/baseline_v2.json", "--spec", "config/metric_spec_v2.yaml"])
    for path in sorted(Path("reports/traps").glob("*.json")):
        spec_path = path.with_suffix(".spec.yaml")
        command(f"trap_{path.stem}", ["-m", "lab9.gate", "--pr", path.as_posix(),
            "--baseline", "reports/baseline_v2.json", "--spec",
            spec_path.as_posix() if spec_path.is_file() else "config/metric_spec_v2.yaml",
            "--base-spec", "config/metric_spec_v2.yaml"], 1)
    for shape in ("seeded_regression", "fixed"):
        command(f"trace_{shape}", ["-m", "lab9.trace_case", "--shape", shape, "--claim", "C-002", "--seed", "11"])
    collect_evidence()
    write_json("reports/verification.json", {"passed": True, "commands": outcomes})
    command("write_docs", ["scripts/write_lab9_docs.py"])
    write_json("reports/verification.json", {"passed": True, "commands": outcomes})
    print(f"M0-M7 PASS: {len(outcomes)} commands; reports/verification.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
