<!-- nguồn: PII_MEASUREMENT_2026-11-01.md | mục: Số đo PII đầu tiên (C-09 b, MS-2) > 6. Kết luận cho quyết định OI-12 (local NER) | 958 ký tự | trước: 05_5-d1-kiem-tra-che-nham-va-quet-long.md | sau: - -->

## 6. Kết luận cho quyết định OI-12 (local NER)

- Trên fixture tổng hợp, regex/heuristic đạt cả hai nhóm và tỷ lệ giữ nguyên, **nhưng** fixture do chính người viết detector đánh dấu và chỉ có 2 ca giới hạn cố ý (tên không anchor, địa chỉ không anchor). Con số này không đại diện cho hợp đồng thật.
- Điểm yếu cấu trúc còn lại là nhóm B không có anchor: tên và địa chỉ đứng trong câu văn thường (vd. người liên hệ, nơi cư trú trong điều khoản). Regex không bắt được; chỉ NER hoặc gold thật mới đo được.
- Đề xuất cho MS-2: **chưa chốt bỏ NER**. Điều kiện chốt: chạy lại script này trên gold privacy D1 (N2) hoặc 2-3 hợp đồng thật đã gán span (T1). Nếu nhóm B < 90% trên gold thật thì mở local NER (OI-12); nếu ≥ 90% thì giữ regex và ghi giới hạn vào thông báo người dùng (BRD §7.6).
- Rủi ro rò rỉ lớn nhất không nằm ở số đo: placeholder cùng độ dài nên LLM thấy được độ dài tên; và tên pháp nhân bị che nhưng từ vai trò giữ nguyên (đúng thiết kế TDD §10.2).
