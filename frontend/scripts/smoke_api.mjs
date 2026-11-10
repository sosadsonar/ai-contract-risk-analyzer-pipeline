#!/usr/bin/env node
/**
 * Smoke test API trực tiếp với backend dev (:8000) không qua giao diện UI.
 * Thuần Node.js (dùng fetch, FormData, Blob có sẵn từ Node 18+), không thêm thư viện ngoài.
 *
 * Kiểm tra các tệp mẫu theo TDD §5 và TDD §6:
 * - norisk.pdf: rủi ro rỗng
 * - insufficient.pdf: rủi ro có evidence_status = INSUFFICIENT_EVIDENCE -> severity null, citation_ids rỗng
 * - emoji.pdf: ký tự non-BMP, offset code point partition
 *
 * Các điều kiểm tra:
 * 1. Đủ khóa theo src/api/types.ts (FinalResult)
 * 2. Offset clause là partition không chồng lấn
 * 3. canonical_text tương ứng với clauses
 * 4. insufficient thì severity null và citation_ids rỗng
 * 5. DELETE session -> status là EXPIRED (hoặc tombstone)
 */

const BASE_URL = process.env.API_URL || "http://127.0.0.1:8000/api/v1";

const REQUIRED_FINAL_RESULT_KEYS = [
  "schema_version",
  "offset_unit",
  "session_id",
  "role",
  "status",
  "analysis_date",
  "canonical_text",
  "clauses",
  "risks",
  "citations",
  "disclaimer",
  "data_notice",
  "version_pins",
];

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Tạo một file PDF giả lập nhỏ hợp lệ với header %PDF-1.4
 */
function makeDummyPdf(name) {
  const content = `%PDF-1.4\n%âãÏÓ\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R>>endobj\nxref\n0 4\n0000000000 65535 f \n0000000015 00000 n \n0000000060 00000 n \n0000000111 00000 n \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n186\n%%EOF\n`;
  return new File([content], name, { type: "application/pdf" });
}

/**
 * Đếm số lượng Unicode code point của chuỗi (khớp INV-12)
 */
function countCodePoints(str) {
  return Array.from(str).length;
}

/**
 * Cắt chuỗi theo Unicode code point [start, end)
 */
function cpSlice(text, start, end) {
  const codePoints = Array.from(text);
  return codePoints.slice(start, end).join("");
}

async function runTestCase(fileName, role = "EMPLOYEE") {
  console.log(`\n========================================`);
  console.log(`▶ BẮT ĐẦU KIỂM THỬ TỆP: ${fileName} (role: ${role})`);
  console.log(`========================================`);

  // 1. POST /sessions
  console.log(`[1] POST /sessions...`);
  const form = new FormData();
  form.append("role", role);
  form.append("file", makeDummyPdf(fileName));

  let createRes;
  try {
    createRes = await fetch(`${BASE_URL}/sessions`, {
      method: "POST",
      body: form,
    });
  } catch (err) {
    console.error(`  ❌ LỖI KẾT NỐI: Không kết nối được tới ${BASE_URL}/sessions`);
    console.error(`     Chi tiết: ${err.message}`);
    return false;
  }

  if (createRes.status !== 201) {
    const body = await createRes.text();
    console.error(`  ❌ THẤT BẠI: POST /sessions trả về HTTP ${createRes.status} thay vì 201 Created`);
    console.error(`     Response: ${body}`);
    return false;
  }

  const createData = await createRes.json();
  const sessionId = createData.session_id;
  console.log(`  ✓ Tạo phiên thành công: session_id = ${sessionId}, status = ${createData.status}`);

  // 2. Poll GET /sessions/{id}/status
  console.log(`[2] Polling GET /sessions/${sessionId}/status...`);
  const terminalStatuses = new Set(["COMPLETED", "FAILED", "REJECTED", "EXPIRED"]);
  let finalStatus = null;
  const pollStart = Date.now();

  while (Date.now() - pollStart < 30_000) {
    const statusRes = await fetch(`${BASE_URL}/sessions/${sessionId}/status`);
    if (!statusRes.ok) {
      console.error(`  ❌ LỖI: GET /status trả về HTTP ${statusRes.status}`);
      return false;
    }
    const statusData = await statusRes.json();
    process.stdout.write(`  ... status: ${statusData.status} (stage: ${statusData.stage || "none"})\r`);

    if (terminalStatuses.has(statusData.status)) {
      finalStatus = statusData;
      console.log(`\n  ✓ Đạt trạng thái cuối: ${finalStatus.status}`);
      break;
    }
    await sleep(500);
  }

  if (!finalStatus) {
    console.error(`\n  ❌ TIMEOUT: Quá 30 giây polling không đạt trạng thái kết thúc`);
    return false;
  }

  if (finalStatus.status !== "COMPLETED") {
    console.error(`  ❌ THẤT BẠI: Phiên kết thúc với trạng thái ${finalStatus.status} (error_code: ${finalStatus.error_code})`);
    return false;
  }

  // 3. GET /sessions/{id}/result
  console.log(`[3] GET /sessions/${sessionId}/result...`);
  const resultRes = await fetch(`${BASE_URL}/sessions/${sessionId}/result`);
  if (!resultRes.ok) {
    console.error(`  ❌ LỖI: GET /result trả về HTTP ${resultRes.status}`);
    return false;
  }
  const result = await resultRes.json();

  // 3.1 Kiểm tra các khóa bắt buộc
  console.log(`  Kiểm tra các khóa của FinalResult...`);
  const missingKeys = REQUIRED_FINAL_RESULT_KEYS.filter((k) => !(k in result));
  if (missingKeys.length > 0) {
    console.error(`  ❌ THẤT BẠI: Thiếu các khóa bắt buộc: ${missingKeys.join(", ")}`);
    return false;
  }
  console.log(`  ✓ Đầy đủ tất cả các khóa theo src/api/types.ts`);

  // 3.2 Kiểm tra offset là partition không chồng lấn
  console.log(`  Kiểm tra partition của clauses (INV-12)...`);
  const clauses = [...result.clauses].sort((a, b) => a.start_char - b.start_char);
  let prevEnd = 0;
  let partitionValid = true;

  for (let i = 0; i < clauses.length; i++) {
    const c = clauses[i];
    if (c.start_char < prevEnd) {
      console.error(`  ❌ LỖI PARTITION: Clause ${c.clause_id} có start_char (${c.start_char}) < end_char trước (${prevEnd})`);
      partitionValid = false;
      break;
    }
    if (c.end_char <= c.start_char) {
      console.error(`  ❌ LỖI PARTITION: Clause ${c.clause_id} có end_char (${c.end_char}) <= start_char (${c.start_char})`);
      partitionValid = false;
      break;
    }
    // So khớp lát cắt text theo code point
    const expectedSlice = cpSlice(result.canonical_text, c.start_char, c.end_char);
    if (c.original_text !== expectedSlice) {
      console.error(`  ❌ LỖI OFFSET: Text trích xuất [${c.start_char}, ${c.end_char}) không khớp original_text của ${c.clause_id}`);
      partitionValid = false;
      break;
    }
    prevEnd = c.end_char;
  }

  if (!partitionValid) return false;
  console.log(`  ✓ Offset là partition chuẩn xác không chồng lấn (${clauses.length} điều khoản)`);

  // 3.3 Kiểm tra theo từng tệp mẫu
  if (fileName.includes("norisk")) {
    console.log(`  Kiểm tra norisk.pdf: risks phải rỗng...`);
    if (result.risks.length !== 0) {
      console.error(`  ❌ THẤT BẠI: norisk.pdf nhưng có ${result.risks.length} rủi ro`);
      return false;
    }
    console.log(`  ✓ norisk.pdf: 0 rủi ro đúng quy chuẩn`);
  }

  if (fileName.includes("insufficient")) {
    console.log(`  Kiểm tra insufficient.pdf: rủi ro thiếu căn cứ...`);
    const insufficientRisk = result.risks.find((r) => r.evidence_status === "INSUFFICIENT_EVIDENCE");
    if (!insufficientRisk) {
      console.error(`  ❌ THẤT BẠI: Không tìm thấy rủi ro nào có evidence_status = INSUFFICIENT_EVIDENCE`);
      return false;
    }
    if (insufficientRisk.severity !== null) {
      console.error(`  ❌ THẤT BẠI: INSUFFICIENT_EVIDENCE phải có severity = null, nhận: ${insufficientRisk.severity}`);
      return false;
    }
    if (!Array.isArray(insufficientRisk.citation_ids) || insufficientRisk.citation_ids.length !== 0) {
      console.error(`  ❌ THẤT BẠI: INSUFFICIENT_EVIDENCE phải có citation_ids = []`);
      return false;
    }
    console.log(`  ✓ insufficient.pdf: severity = null và citation_ids = [] chính xác`);
  }

  if (fileName.includes("emoji")) {
    console.log(`  Kiểm tra emoji.pdf: văn bản non-BMP...`);
    const hasNonBmp = Array.from(result.canonical_text).some((ch) => ch.length > 1);
    const totalCp = countCodePoints(result.canonical_text);
    console.log(`  ✓ canonical_text có ${totalCp} Unicode code points (chứa ký tự non-BMP: ${hasNonBmp ? "CÓ" : "KHÔNG"})`);
  }

  // 4. DELETE /sessions/{id}
  console.log(`[4] DELETE /sessions/${sessionId}...`);
  const delRes = await fetch(`${BASE_URL}/sessions/${sessionId}`, { method: "DELETE" });
  if (!delRes.ok) {
    console.error(`  ❌ LỖI: DELETE /sessions trả về HTTP ${delRes.status}`);
    return false;
  }
  const delData = await delRes.json();
  if (delData.status !== "EXPIRED") {
    console.error(`  ❌ THẤT BẠI: DELETE phải trả về status = 'EXPIRED', nhận: ${delData.status}`);
    return false;
  }
  console.log(`  ✓ Kết thúc phiên thành công: status = ${delData.status}`);

  // 5. Kiểm tra status sau khi DELETE
  console.log(`[5] Kiểm tra lại GET /sessions/${sessionId}/status sau DELETE...`);
  const postDelRes = await fetch(`${BASE_URL}/sessions/${sessionId}/status`);
  if (postDelRes.status === 200) {
    const postDelData = await postDelRes.json();
    if (postDelData.status === "EXPIRED") {
      console.log(`  ✓ Phiên ở trạng thái tombstone EXPIRED hợp lệ`);
    } else {
      console.error(`  ❌ THẤT BẠI: Phiên đã xóa nhưng status = ${postDelData.status}`);
      return false;
    }
  } else if (postDelRes.status === 404) {
    console.log(`  ✓ Phiên đã được xóa sạch (404 SESSION_NOT_FOUND) hợp lệ`);
  } else {
    console.error(`  ❌ LỖI: Trạng thái không mong đợi sau khi xóa: HTTP ${postDelRes.status}`);
    return false;
  }

  console.log(`>>> TỆP ${fileName}: PASS TẤT CẢ CÁC ĐIỀU KIỆN! <<<\n`);
  return true;
}

async function main() {
  console.log(`Khởi động Smoke Test API: Target URL = ${BASE_URL}`);

  // Kiểm tra kết nối ban đầu
  try {
    const probe = await fetch(`${BASE_URL.replace("/api/v1", "")}/docs`, { method: "HEAD" });
    console.log(`✓ Backend online (HTTP ${probe.status})`);
  } catch (err) {
    console.error(`❌ KHÔNG THỂ KẾT NỐI TỚI BACKEND TẠI ${BASE_URL}`);
    console.error(`   Nguyên nhân: Backend server chưa được khởi chạy hoặc không lắng nghe tại cổng này.`);
    console.error(`   Hướng dẫn: Khởi chạy backend trên terminal bằng lệnh:`);
    console.error(`     APP_ENV=dev uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000`);
    console.error(`   Sau đó chạy lại script này: node frontend/scripts/smoke_api.mjs`);
    process.exit(1);
  }

  const testFiles = ["norisk.pdf", "insufficient.pdf", "emoji.pdf"];
  const results = [];

  for (const file of testFiles) {
    const pass = await runTestCase(file);
    results.push({ file, pass });
  }

  console.log(`\n================ TỔNG KẾT SMOKE TEST API ================`);
  let allPass = true;
  for (const r of results) {
    console.log(`- ${r.file.padEnd(20)}: ${r.pass ? "✅ PASS" : "❌ FAIL"}`);
    if (!r.pass) allPass = false;
  }
  console.log(`========================================================`);

  if (!allPass) {
    process.exit(1);
  }
}

main().catch((err) => {
  console.error("Lỗi thực thi script:", err);
  process.exit(1);
});

