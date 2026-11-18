# Complete Lab 9: evaluation and failure analysis M0–M7

Hoàn thiện thống kê calibration/bootstrap/pass@k/pass^k; grader approval, ledger và FM-08; taxonomy chín FM, eval set v1/v2 và gate theo slice. Integrity phát hiện báo cáo thiếu/trùng dòng, NaN, lỗi grader, đổi seed/slice hoặc summary trái rows; ratchet bảo vệ metric và slice. Day 8 giữ nguyên từ mã nguồn gốc.

Kiểm tra local: `57 passed, 301 deselected in 1.96s`; `53 passed, 305 deselected in 3.42s`. Toàn bộ lệnh tái lập và report: `python -m lab9.verify`. Baseline v1 `E-swarm-20261118-51a5`; v2 `E-swarm-20261118-9047`.

## Gate seeded_regression — exit 1

```text
gate: PR E-seeded_regression-20261118-51a5 vs main E-swarm-20261118-51a5 · eval set 51a514bea930
  approval_bypass        0        {"max": 0}                                                            ok
  secret_leak            0        {"max": 0}                                                            ok
  db_fact_kept           0.9286   {"min": 0.95}                                                         warn
  full_quote_kept        0.8571   {"min": 0.95}                                                         warn
  refund_amount_correct  0.8571   {"min": 0.95, "no_significant_drop": true} Δ -0.129 CI [-0.315, +0.000] BLOCK
  pass_rate              0.7143   {"min": 0.85, "no_significant_drop": true} Δ -0.271 CI [-0.500, -0.057] BLOCK
  pass_5                 0.7143   {"min": 0.8}                                                          warn
  cost_per_success       81.202   {"max_increase": 0.1}                                                 warn
  reply_ledger_correct   0.7857   {"min": 1.0, "no_significant_drop": true} Δ -0.214 CI [-0.429, +0.000] BLOCK
exit 1 — blocked: refund_amount_correct, pass_rate, reply_ledger_correct
```

## Mutation scorecard

```text
fixed                expect merge got merge ok          
  honest_refactor      expect merge got merge ok          
  seeded_regression    expect block got block ok          refund_amount_correct, pass_rate, pass_hat_5, reply_ledger_correct, slice:money_movement/pass_rate, slice:adversarial/pass_rate, slice:denial/pass_rate
  slice_regression     expect block got block ok          slice:money_movement/pass_rate
  flaky_regression     expect block got block ok          pass_rate, pass_hat_5, slice:money_movement/pass_rate
mutation score 3/3 · false alarms 0
```

## A/A — hai bộ seed

```text
metric                 spec seeds  alt seeds    delta
approval_bypass                 0          0  +0.0000
secret_leak                     0          0  +0.0000
db_fact_kept               0.9786     0.9786  +0.0000
full_quote_kept               1.0        1.0  +0.0000
refund_amount_correct      0.9786     0.9786  +0.0000
pass_rate                  0.9786     0.9786  +0.0000
reply_ledger_correct          1.0        1.0  +0.0000
pass_5                     0.8929     0.8929  +0.0000
pass_at_1                  0.9786     0.9786  +0.0000
pass_hat_1                 0.9786     0.9786  +0.0000
pass_at_3                     1.0        1.0  +0.0000
pass_hat_3                 0.9357     0.9357  +0.0000
pass_at_5                     1.0        1.0  +0.0000
pass_hat_5                 0.8929     0.8929  +0.0000
cost_per_success          50.8077    50.8077  +0.0000
```

## Bốn trap — exit 1

```text
cherry_picked_seeds: exit 1 — blocked: integrity
dropped_failing_rows: exit 1 — blocked: integrity
evaluator_errors_as_nan: exit 1 — blocked: integrity
loosened_spec: exit 1 — blocked: integrity
```

Eval card, PRD v1.1, judge audit và trace case đi kèm trong `docs/`. Các con số thuộc thử nghiệm offline MockLLM/judge replay, với v1 14 item và v2 28 item.
