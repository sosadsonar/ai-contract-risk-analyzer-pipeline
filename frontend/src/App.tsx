import { useState } from "react";
import type { Role } from "./api/types";
import Upload from "./pages/Upload";

// Chưa dùng react-router: demo chỉ có 1 luồng Upload → Progress → Result.
// Khi làm Progress/Result, thêm vào `view` bên dưới (hoặc đổi sang router nếu cần).
export default function App() {
  const [session, setSession] = useState<{ id: string; role: Role } | null>(null);

  if (!session) return <Upload onCreated={(id, role) => setSession({ id, role })} />;

  return (
    <main className="page">
      <h1>Đã tạo phiên</h1>
      <p className="lead">Mã phiên: {session.id} ({session.role}). Trang Tiến trình và Kết quả sẽ làm ở bước tiếp theo.</p>
      <button onClick={() => setSession(null)}>Tải hợp đồng khác</button>
    </main>
  );
}
