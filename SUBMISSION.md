# Nộp bài (bài cá nhân, hạn nộp theo ca làm bài)
1. Commit mã nguồn, dữ liệu, tài liệu và report sinh bằng script. Bản nộp này giữ `src/reports/` trong repo; `git add -A` bao gồm report và log. Lệnh `git add -f reports/*.json` trong thư mục `src/` vẫn dùng được.
2. Mở PR `starter/d09` → `main` **trong bản fork của bạn**, không mở vào repo gốc. Dán output gate exit 1 của `seeded_regression` vào mô tả PR.
3. Job `eval-gate` xanh thì **merge PR vào `main`**. Giảng viên chấm nhánh `main` của bản fork; commit sau hạn của ca không tính.
4. Dán [link repo fork](https://github.com/alpha19102004/K5-L3B-DAY09-PhanNguyenPhanAnh-2A202604004-EvaluationandFailureAnalysis) lên LMS.

Làm thêm Advanced/Expert sau buổi: tiếp tục trên nhánh, mở PR mới rồi merge lại trước hạn.

## Core (nên xong trước 17:00)
- [x] `src/lab9/{stats,graders,evalset,gate}.py` hoàn thành M1–M4
- [x] `src/data/eval/eval_set_v1.jsonl` có `failure_modes`, `labels_v1.json` tách riêng
- [x] `docs/failure_taxonomy.md`, `docs/trace_case.md` cùng regression test, `docs/judge_audit.md`, `docs/eval_card.md`, `docs/PRD_v1.1.md`
- [x] `src/reports/baseline_v1.json`, `eval_fixed.json`, `eval_seeded_regression.json` sinh bằng script
- [x] `src/harness_map.yaml` có section `eval`
- [x] Lệnh Core chạy thành công local; output `seeded_regression` exit 1 nằm trong `docs/PR_DESCRIPTION.md`
- [ ] Mở PR trên GitHub, job `eval-gate` xanh rồi merge vào `main`

## Advanced / Expert (tới hạn nộp)
- [x] `src/config/fm_map.yaml`, `metric_spec_v2.yaml`, `stats.pass_at_k/pass_hat_k`, `gate.slice_check`, `gate.integrity_check` và ratchet
- [x] `src/data/eval/eval_set_v2.jsonl` + `labels_v2.json` sinh bằng script, 28 item
- [x] `src/reports/baseline_v2.json` và các report biến thể v2 sinh bằng script
- [x] `docs/PR_DESCRIPTION.md` chứa mutation scorecard, A/A và bốn dòng trap exit 1
- [x] `docs/eval_card.md` có kết quả v2, ngưỡng từ A/A, slice gate và giới hạn cỡ mẫu
- [x] `python -m lab9.verify` tái lập toàn bộ; log và trạng thái ở `src/reports/verification.json`
- [ ] Job `eval-gate-v2` xanh trên GitHub và PR được merge
