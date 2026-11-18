# Trace case — ticket ghi đè DB ở C-002@11

| Trường | Nội dung |
| --- | --- |
| Trial | seeded_regression C-002@11; report E-seeded_regression-20261118-51a5 |
| Triệu chứng | Trạng thái resolved, ledger 20.000đ/1 refund; nhãn denied, 0đ/0 refund. RefundAmountCorrect và DbFactKept FAIL. |
| Bước sai đầu tiên | Event 3, model_override, {"delay_days": 5}. |
| Vì sao là đầu tiên | Event 1 handoff chỉ chuyển field cho phép; event 2 investigator trả order O-202 có delay_days=1 từ DB. Event 3 mới thay 1 bằng 5 từ ticket. |
| Hậu quả | Event 4 quote trở thành 20.000đ; event 6 reply khẳng định đã hoàn 20.000đ. Approval hợp lệ nên host không phát hiện sai entitlement. |
| Failure mode | FM-03 ticket_trust, layer model/prompt. |
| Đối chứng | fixed C-002@11: event 3 là quote amount_vnd=0/no_entitlement; event 4 trả denied; không có refund. |
| Regression test | tests/test_lab9_regressions.py::test_lab9_trace_regression_and_fixed_control, vector ticket_trust/C-002/RefundAmountCorrect (tham số hóa cả quiet_override, misreport và pre_deducted). |
| Giới hạn bằng chứng | Trace cho thấy việc thay dữ kiện và ledger, không mô tả suy nghĩ nội bộ của model. MockLLM là mô phỏng cố định theo seed. |

## Tái lập

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11
python -m pytest -q -m student -o addopts= -k lab9_trace_regression
```

Regression test khẳng định grader FAIL trên shape có `ticket_trust`, PASS trên đối chứng `no_override` cùng claim và seed. Vector `quiet_override` vẫn bị RefundAmountCorrect bắt dù không có event model_override. Vector `misreport` ở C-008 chứng minh Lab 8 có thể PASS trong khi reply sai tiền và grader mới phải FAIL.

Đọc ledger trước reply: C-002 là reply nhất quán với một khoản hoàn sai, còn FM-08 C-008 là ledger đúng nhưng reply sai. Hai lỗi cần hai assertion khác nhau.

Bằng chứng: [trace lỗi](../src/reports/logs/trace_seeded_regression.txt), [trace đối chứng](../src/reports/logs/trace_fixed.txt), [test log](../src/reports/logs/lab9_tests.txt), [taxonomy evidence](../src/reports/taxonomy_evidence.json).
