# Thiết kế C-13(b): Mở rộng Data Graph

## Mục tiêu

Hoàn thiện truy xuất graph in-memory theo TDD §14.6 trên fixture kiểm thử: mở rộng một bước từ seeds, áp dụng giới hạn neighbor, xếp hạng và fallback về baseline khi graph phát sinh lỗi. Mục tiêu là bảo đảm graph on/off trả cùng ngân sách `final_k`; đây chưa phải bằng chứng graph cải thiện Recall@5.

## Phạm vi

- Thêm `DataGraph.expand(seeds, pool, cfg)` và `get_candidates(retriever, graph | None, masked_text, labels, analysis_date, cfg)` theo interface trong SKELETON §5.7.
- Giữ hướng cạnh gốc; áp dụng điểm thưởng loại cạnh và hướng traversal theo TDD §14.6.
- Giới hạn tổng graph-only neighbor mỗi seed bằng `GRAPH_MAX_NEIGHBORS_PER_SEED`; giới hạn số child của `PARENT_OF` bằng `GRAPH_MAX_CHILDREN_PER_SEED`.
- Giữ top seeds ở đầu; hợp nhất phần còn lại của baseline pool với graph-only neighbors, loại trùng citation ID và cắt đến `final_k`.
- Khi graph tắt, vắng mặt hoặc lỗi trong lúc mở rộng, trả baseline pool; chỉ trường hợp lỗi graph bật mới đánh dấu `graph_fallback=True`.
- Dùng fixture đã có; không đổi corpus luật thật, release status, checksum hoặc SQLite.

## Ngoài phạm vi

- Không xác nhận tính pháp lý của provisions hoặc cạnh MANUAL.
- Không mở corpus DRAFT cho runtime và không nối vào pipeline production.
- Không đo hoặc tuyên bố kết quả M8/Recall@5; việc đó cần gold D1 đã duyệt.
- Không tune trọng số từ T1/T2; dùng default TDD để kiểm tính đúng đắn.

## Phương án

1. **Triển khai đầy đủ C-13(b) theo TDD §14.6 bằng fixture (chọn):** hoàn thành expansion, caps, ranking, merge và fallback trong module legal hiện có. Đây là hướng trực tiếp đáp ứng phần còn thiếu đã ghi ở `PROGRESS.md`, đồng thời không phụ thuộc corpus thật.
2. **Chỉ viết metric M8 trước:** chưa phù hợp vì pipeline/eval runner và gold D1 chưa sẵn sàng; metric khi đó sẽ chỉ được thử bằng dữ liệu giả và dễ bị nhầm là số đo chất lượng.
3. **Chờ duyệt corpus thật rồi làm cả hai:** bảo đảm dựa trên dữ liệu đã xác minh nhưng chặn phần code thuần kỹ thuật vốn kiểm thử được độc lập.

## Ràng buộc kỹ thuật

- Mỗi seed mở rộng tối đa một hop.
- TDD default: `REFERS_TO=0.30`, `GUIDES=0.25`, `PARENT_OF=0.15`; hướng ưu tiên `+0.05`, hướng ngược `+0.00`; graph score bắt đầu bằng `0.60 * seed.baseline_score`.
- `PARENT_OF` mở rộng hai hướng; child selection dùng baseline/BM25 relevance. `REFERS_TO` ưu tiên outgoing và cho phép incoming thứ cấp. `GUIDES` đi hai hướng.
- Graph failure không làm hỏng retrieval; baseline pool là kết quả fallback.
- Giữ tương thích model/fixture hiện có và không thêm dependency.

## Cách kiểm chứng

Viết test trước cho: hướng/cap mỗi edge type, cap tổng neighbor và child, nhiều seed trỏ cùng neighbor, seed-first và cùng `final_k`, graph-off, graph lỗi fallback, ngày hiệu lực ở hai endpoint. Chạy test mới rồi toàn bộ test suite và Ruff theo cấu hình hiện tại; báo riêng các test bị skip do private data submodule. Không đổi nội dung corpus để làm test pass.
