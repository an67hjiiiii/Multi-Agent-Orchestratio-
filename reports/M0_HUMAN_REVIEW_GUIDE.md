# M0 Human Review Guide

Mở M0_HUMAN_REVIEW.html bằng trình duyệt local. Bộ này gồm đúng 12 case real Ollama; hai ô điểm được để trống để Human chấm.

## Chấm điểm

- Correctness: **2** = đúng/đủ; **1** = đúng một phần; **0** = sai.
- Faithfulness: **2** = mọi claim chính bám evidence; **1** = có phần chưa được evidence support; **0** = bịa hoặc mâu thuẫn evidence.

Với case NO_EVIDENCE, nếu model từ chối vì tài liệu không có thông tin thì chấm correctness **2**, faithfulness **2**. Nếu model tự đoán khi không có evidence thì chấm **0/0**.

Chỉ cần chấm đủ 12 case và ghi reviewer_note khi cần. HTML có filter, progress, summary chỉ dựa trên điểm Human đã nhập, và nút export CSV local. Dòng HUMAN_GATE_PASS candidate chỉ là gợi ý, không phải quyết định chính thức.

Gold answer points không có trong calibration artifact nên được ghi NOT_AVAILABLE_IN_ARTIFACT; không tự bổ sung hoặc sửa câu trả lời model.
