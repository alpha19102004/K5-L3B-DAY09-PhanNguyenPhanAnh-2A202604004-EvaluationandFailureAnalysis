# Judge audit

Người thực hiện: Phan Nguyen Phan Anh — 2A202604004 — K5-L3B. Dữ liệu: hai CSV replay công khai, mỗi CSV 100 dòng. FAIL là lớp dương; đánh giá khả năng phát hiện lỗi.

| Tiêu chí | n | κ | Precision | Recall | Floors | Quyết định |
| --- | --- | --- | --- | --- | --- | --- |
| tone_ok | 100 | 0.757 | 0.857 | 0.8 | PASS | Dùng cho giọng điệu |
| helpful | 100 | 0.375 | 1.0 | 0.3 | FAIL | Loại khỏi gate |

Floors đồng thời: κ≥0.6, Precision≥0.8, Recall≥0.7. κ không xác định phải FAIL. Tone đạt cả ba sàn; helpful chỉ phát hiện 9/30 lỗi, bỏ sót 21/30 dù precision bằng 1 nên không đủ điều kiện làm gate.

| Judge | TP | FP | FN | TN | Tỷ lệ FAIL quan sát | Rogan–Gladen |
| --- | --- | --- | --- | --- | --- | --- |
| tone | 24 | 4 | 6 | 66 | 0.28 | 0.3 |
| helpful | 9 | 0 | 21 | 70 | 0.09 | 0.3 |

Rogan–Gladen = (p_obs + specificity − 1)/(sensitivity + specificity − 1), chặn về [0,1]. Tone: sensitivity=24/30, specificity=66/70, p_obs=0.28 → 0.30. Helpful: sensitivity=9/30, specificity=70/70, p_obs=0.09 → 0.30. Hiệu chỉnh tỷ lệ không sửa được việc bỏ sót lỗi trên từng case; helpful vẫn bị loại.

## Rà soát mười bất đồng tone

| Case | Judge | Nhãn nguồn | Kết luận rà soát | Sửa rubric / dữ liệu |
| --- | --- | --- | --- | --- |
| H-008 | PASS | FAIL | Nhãn nguồn FAIL | Cấm xưng em/nha suồng sã; thêm ví dụ âm dù câu có vẻ thân thiện. |
| H-017 | PASS | FAIL | Nhãn nguồn FAIL | Chỉ dùng anh/chị theo văn phong CSKH; không cho Dạ bù cho bạn ơi/nha. |
| H-029 | PASS | FAIL | Nhãn nguồn FAIL | Chấm toàn câu; không cần nhắn thêm là mệnh lệnh dù mở đầu lịch sự. |
| H-042 | FAIL | PASS | Nhãn nguồn PASS | Không bắt buộc xin lỗi nếu câu đã lịch sự, rõ kết quả và thời gian. |
| H-051 | FAIL | PASS | Nhãn nguồn PASS | Cho phép từ refund trong từ điển nghiệp vụ; không phạt tiếng Anh riêng lẻ. |
| H-063 | PASS | FAIL | Nhãn nguồn FAIL | Không chấp nhận lời hứa hoàn thêm ngoài kết quả đã được hệ thống xác nhận. |
| H-070 | PASS | FAIL | Nhãn nguồn FAIL | Bổ sung ví dụ emoji cười không phù hợp ngữ cảnh khiếu nại. |
| H-081 | FAIL | PASS | Judge FAIL theo ghi chú nguồn | Nguồn ghi nhãn PASS do đọc nhầm ticket; lưu sửa nhãn sang phiên bản mới, giữ CSV v1 để tái lập số đo. |
| H-088 | FAIL | PASS | Nhãn nguồn PASS | Không phạt lặp Dạ một lần do lỗi gõ nếu ý và thái độ vẫn đúng. |
| H-094 | PASS | FAIL | Nhãn nguồn FAIL | Bổ sung tiêu chí tiếng Việt có dấu và ví dụ dịch máy thiếu dấu. |

Kết luận H-081 dựa trên cột `note` của fixture. Các chỉ số phía trên giữ nguyên nhãn CSV gốc để so sánh với test tham chiếu; bảng rà soát không được âm thầm đổi ground truth của v1.

## Bảy bất đồng helpful

| Case | Judge | Nhãn nguồn | Lỗi | Bằng chứng |
| --- | --- | --- | --- | --- |
| HL-015 | PASS | FAIL | sai tiền | ledger ghi 40.000đ |
| HL-016 | PASS | FAIL | sai tiền | ledger ghi 35.000đ |
| HL-020 | PASS | FAIL | sai tiền | ledger ghi 120.000đ |
| HL-028 | PASS | FAIL | sai tiền | ledger ghi 35.000đ |
| HL-035 | PASS | FAIL | sai tiền | ledger ghi 35.000đ |
| HL-041 | PASS | FAIL | sai tiền | ledger ghi 40.000đ |
| HL-043 | PASS | FAIL | sai tiền | ledger ghi 20.000đ |

HL-015/016/020/028/035/041/043 phải FAIL vì số tiền trái ledger. Rubric helpful đang thưởng lời xin lỗi và độ dài thay vì kiểm chứng kết quả. Tách thành các điều kiện bắt buộc: đúng ledger, đúng trạng thái, nêu hành động tiếp theo phù hợp; thiếu một điều kiện thì FAIL. Grader `ReplyLedgerCorrect` kiểm tiền bằng code, không giao tiêu chí này cho judge.

## Quyết định sử dụng

Tone chỉ đủ điều kiện cho tiêu chí ngôn ngữ trên tập replay này; chưa đưa tone vào quyết định tiền. Helpful bị loại khỏi release gate. Rubric sửa cần một eval-set version mới và tập dữ liệu mới tách khỏi CSV dùng để điều chỉnh. Mẫu công khai nhỏ và replay không đo được biến động của judge trực tiếp.

Bằng chứng: [tone log](../src/reports/logs/tone.txt), [helpful log](../src/reports/logs/helpful.txt), [analysis.json](../src/reports/analysis.json). `lab9.judge` tone exit 0, helpful exit 1 là kết quả mong đợi.
