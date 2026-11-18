"""Behavioral regression cases for the first wrong step, FM-08 and report integrity."""
import copy

import pytest

pytestmark = pytest.mark.student


def _ctx(trial, label=None):
    from pydantic_evals.evaluators import EvaluatorContext

    return EvaluatorContext(name="regression", inputs={}, metadata=None, expected_output=label or {},
                            output=trial, duration=0.0, _span_tree=None, attributes={}, metrics={})


@pytest.mark.parametrize("amount,text,want", [
    (20000, "Dạ, LogiX đã hoàn 35.000đ cho đơn O-808.", False),
    (20000, "LogiX đã hoàn phí 20,000 VND cho đơn O-808 của anh/chị ạ.", True),
    (20000, "Đề xuất 35.000đ; LogiX đã hoàn 20 000 đồng.", True),
    (20000, "Mức hoàn phí dự kiến 35.000đ; LogiX đã hoàn 20.000đ.", True),
    (20000, "LogiX đã hoàn 25000 VNĐ cho đơn O-808.", False),
    (0, "Dạ, đơn O-808 chưa đủ điều kiện hoàn theo chính sách.", True),
    (0, "Dạ, LogiX đã hoàn 35.000đ cho đơn O-808.", False),
])
def test_lab9_reply_ledger_checks_money_and_allows_paraphrases(amount, text, want):
    from lab9.graders import ReplyLedgerCorrect

    trial = {"result": {"status": "resolved" if amount else "denied"},
             "snapshot": {"refund_vnd": amount, "refund_count": int(amount > 0)},
             "events": [{"kind": "reply", "payload": {"text": text}}]}
    assert ReplyLedgerCorrect().evaluate(_ctx(trial)).value is want


@pytest.mark.parametrize("bugs,claim,grader", [
    ({"ticket_trust"}, "C-002", "RefundAmountCorrect"),
    ({"quiet_override"}, "C-002", "RefundAmountCorrect"),
    ({"no_override", "misreport"}, "C-008", "ReplyLedgerCorrect"),
    ({"no_override", "pre_deducted"}, "C-013", "FullQuoteKept"),
])
def test_lab9_trace_regression_and_fixed_control(tmp_path, monkeypatch, bugs, claim, grader):
    from lab8.shapes import SHAPES
    from lab9 import graders
    from lab9.eval import load_spec, load_world, make_task
    from lab9.variant_agent import make_shape
    import json
    from pathlib import Path

    spec = load_spec()
    world, claims = load_world(spec)
    labels = json.loads(Path(spec["labels"]).read_text(encoding="utf-8"))
    for name, switches, want in (("regression_probe", bugs, False), ("fixed_control", {"no_override"}, True)):
        monkeypatch.setitem(SHAPES, name, make_shape(name, switches))
        trial = make_task(name, world, claims, labels, tmp_path)({"claim_id": claim, "seed": 11})
        assert getattr(graders, grader)().evaluate(_ctx(trial, labels[claim])).value is want
        if "ticket_trust" in switches:
            assert trial["events"][2] == {"kind": "model_override", "payload": {"delay_days": 5}}
        if "quiet_override" in switches:
            assert not any(e["kind"] == "model_override" for e in trial["events"])
        if "misreport" in switches:
            assert trial["lab8_pass"] is True  # Legacy outcome grader alone misses FM-08.


def _clean_report():
    from lab9.eval import aggregate

    rows = [{"item_id": f"E-{i}", "seed": seed, "slices": ["money_movement"],
             "pass_rate": True, "cost": 1.0} for i in range(3) for seed in (11, 22)]
    return {"manifest": {"eval_set_sha": "same", "items": 3, "seeds": [11, 22]},
            "rows": rows, "metrics": aggregate(rows, ["pass_rate"]), "evaluator_failures": []}


@pytest.mark.parametrize("attack", ["duplicate", "grader_failure", "relabel", "nan_row", "forged_summary", "incomplete_item"])
def test_lab9_advanced_integrity_rejects_hidden_evidence(attack):
    from lab9 import gate

    base = _clean_report()
    pr = copy.deepcopy(base)
    if attack == "duplicate":
        pr["rows"][-1] = copy.deepcopy(pr["rows"][0])
    elif attack == "grader_failure":
        pr["evaluator_failures"] = ["grader crashed despite green summary"]
    elif attack == "relabel":
        for row in pr["rows"]:
            row["slices"] = []
    elif attack == "nan_row":
        pr["rows"][0]["pass_rate"] = float("nan")
    elif attack == "forged_summary":
        pr["rows"][0]["pass_rate"] = False
    else:
        pr["rows"][-1]["seed"] = 33
    spec = {"metrics": [{"id": "pass_rate", "blocking": True, "threshold": {"min": 0.8}}]}
    assert gate.check(base, base, spec)[0] == []
    blocked, lines = gate.check(pr, base, spec)
    assert blocked == ["integrity"]
    assert all("INTEGRITY" in line for line in lines)


@pytest.mark.parametrize("target", ["min", "max", "max_increase", "blocking", "drop_ci", "remove", "slice"])
def test_lab9_advanced_ratchet_checks_every_constraint(target):
    from lab9 import gate

    spec = {"eval_set_version": "v2", "metrics": [{"id": "pass_rate", "blocking": True,
            "threshold": {"min": 0.8, "max": 1.0, "max_increase": 0.1, "no_significant_drop": True}}],
            "slices": [{"name": "money_movement", "metric": "pass_rate", "min": 0.8,
                        "blocking": True, "no_significant_drop": True}]}
    loose = copy.deepcopy(spec)
    metric = loose["metrics"][0]
    if target in ("min", "max", "max_increase"):
        metric["threshold"][target] += -0.1 if target == "min" else 0.1
    elif target == "blocking":
        metric["blocking"] = False
    elif target == "drop_ci":
        metric["threshold"].pop("no_significant_drop")
    elif target == "remove":
        loose["metrics"] = []
    else:
        loose["slices"][0].pop("no_significant_drop")
    report = _clean_report()
    assert any("ratchet" in p for p in gate.integrity_check(report, report, loose, spec))


@pytest.mark.parametrize("args", [(0, 0, 1), (-1, 0, 1), (5, -1, 1), (5, 2, -1), (5.0, 2, 1), (True, 1, 1)])
def test_lab9_advanced_pass_k_rejects_invalid_domains(args):
    from lab9 import stats

    for fn in (stats.pass_at_k, stats.pass_hat_k):
        with pytest.raises(ValueError):
            fn(*args)
