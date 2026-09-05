# NCKH — Student Research Code Standard

Mục tiêu: code sạch, rõ, dễ giải thích, dễ test, dễ biết ai làm gì.

## Bắt buộc
1. Tên file/function/class/biến phải rõ chức năng.
2. Một module chỉ nên có một trách nhiệm chính.
3. Tách function dài khi việc tách làm code dễ hiểu hơn.
4. Comment giải thích WHY, không kể lại từng dòng code.
5. Không thêm abstraction/design pattern nếu chưa cần.
6. Không tự thêm feature ngoài scope.
7. Không refactor lan sang module khác khi task không yêu cầu.
8. Input/Output của chức năng quan trọng phải rõ.
9. Chức năng quan trọng phải có focused test.
10. Mỗi task báo: INPUT, OUTPUT, FILES, TESTS, COMMIT, BLOCKERS.
11. DETECTED không tự động thành APPROVED.
12. Không sửa dataset/gold chỉ để test pass.
13. Không tự approve semantic/research grading.
14. P/N/O phải dễ map tới methodology, không giấu trong abstraction sâu.
15. Ưu tiên code mà nhóm sinh viên Software Engineering có thể đọc và trình bày được.

## Tránh
- over-engineering
- enterprise pattern không cần thiết
- comment dài kiểu AI
- file/class khổng lồ
- generic utils chứa mọi thứ
- fake production complexity
- speculative feature
