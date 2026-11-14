## Backend W1 Foundation

PR này bổ sung phần backend cơ bản cho AI Contract Risk Analyzer.

### Đã hoàn thành
- Khởi tạo backend bằng FastAPI.
- Thêm health check API để kiểm tra server.
- Thêm API upload hợp đồng PDF.
- Trích xuất text từ PDF bằng PyMuPDF.
- Cấu hình PostgreSQL và kết nối bằng SQLAlchemy.
- Thiết lập Alembic để quản lý database migration.
- Tạo `Contract` model để lưu:
  - filename
  - extracted text
  - status
  - created time
- Tách logic backend thành API / Service / Repository.
- Thêm `.env.example` và cấu hình database qua environment variables.
- Chuẩn bị các integration adapter cho Clause AI, Risk AI và Explanation AI.

### Flow hiện tại

PDF Upload  
→ FastAPI  
→ Extract Text  
→ Contract Service  
→ Repository  
→ PostgreSQL

### API hiện tại
- `GET /health`
- `POST /api/v1/contracts/upload`

### Next
W2 sẽ tích hợp pipeline:

`PDF → Text → Clause AI → Risk AI → Explanation AI → Storage/API Response`