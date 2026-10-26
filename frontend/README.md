# Frontend — AI Contract Risk Analyzer (N5)

```bash
cd frontend
cp .env.example .env     # VITE_USE_MOCK=true: chạy không cần backend
npm install
npm run dev              # http://localhost:5173
npm test                 # test lib/offset (INV-12)
npm run build            # kiểm tra kiểu TypeScript + build
```
Đổi `VITE_USE_MOCK=false` để gọi backend thật (`/api` proxy sang http://localhost:8000).
Mock: tên file chứa "busy" → SYSTEM_BUSY, "scan" → REJECTED, "fail" → FAILED, còn lại → COMPLETED.
