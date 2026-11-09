# Hướng dẫn render sơ đồ Mermaid (X-14)

## File nguồn

| File nguồn | Thay thế ảnh cũ |
|---|---|
| `docs/diagrams/pipeline.mmd` | `docs/diagrams/pipeline.png` |
| `docs/diagrams/state_machine.mmd` | `docs/diagrams/state_machine.png` |

## Cách render bằng một lệnh

### Cách 1: Chạy npm script từ thư mục frontend/ (khuyến nghị, đa nền tảng Windows/macOS/Linux)
Lệnh này chạy qua `scripts/render_diagrams.mjs` (Node.js thuần túy, tự động phân giải đường dẫn và shell trên Windows):
```bash
cd frontend
npm run render:diagrams
```

### Cách 2: Chạy script shell (dành cho Linux / macOS)
```bash
bash scripts/render_diagrams.sh
```

### Cách 3: Chạy trực tiếp qua npx
```bash
npx -y @mermaid-js/mermaid-cli -i docs/diagrams/pipeline.mmd -o docs/diagrams/pipeline.png -b white
npx -y @mermaid-js/mermaid-cli -i docs/diagrams/state_machine.mmd -o docs/diagrams/state_machine.png -b white
```

### Cách 4: Online (không cần Node.js hay mạng dev)
1. Mở https://mermaid.live
2. Dán nội dung từng file `.mmd` vào editor
3. Xuất PNG và lưu đè vào `docs/diagrams/pipeline.png` / `docs/diagrams/state_machine.png`

## Thay đổi so với state_machine.png cũ (O-11 — PROGRESS §9)

Bản cũ (SDD §8) thiếu hai chuyển trạng thái quan trọng:
- **VALIDATING → FAILED**: xảy ra khi có lỗi nội bộ cục bộ (không phải lỗi input → REJECTED).
- **FAILED → VALIDATING**: retry thủ công khi lỗi xảy ra ở giai đoạn cục bộ (trước AI).

File `state_machine.mmd` đã bổ sung cả hai, khớp với ARCHITECTURE.md §4 và ghi chú O-11 trong PROGRESS §9.
