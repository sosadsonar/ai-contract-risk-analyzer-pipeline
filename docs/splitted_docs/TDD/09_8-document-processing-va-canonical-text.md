<!-- nguồn: TDD_AI_Labor_Contract_Risk_Analyzer_v0.2.md | mục: 8. Document Processing và canonical text | 3185 ký tự | trước: 08_7-analysis-orchestrator-state-machine-va-retry-res.md | sau: 10_9-scope-precheck.md -->

# 8. Document Processing và canonical text

## 8.1 Extraction contract

Extractor sinh một `canonical_text` + `extraction_version`. Parser-specific coordinates chỉ phục vụ dựng reading order; downstream không phụ thuộc PDF/DOCX coordinate. Mọi offset là **Unicode code point index sau NFC**.

Extraction/PyMuPDF/DOCX OOXML parsing chạy trong bounded threadpool để không block asyncio event loop; status endpoint phải vẫn đáp ứng NFR-PERF-02.

## 8.2 PDF

* Validate MIME/extension, hard byte cap <=10MB; page_count <=30 trước full extraction.
* PyMuPDF đọc blocks/words; two-column page cluster x-position và đọc top-to-bottom trong từng cột.
* Header/footer lặp: normalized line xuất hiện >=60% trang ở vùng đầu/cuối trang; loại khỏi body. Page number đơn độc bị loại.
* Table: nếu detect rows/cells thì flatten row bằng ` | `, newline giữa rows.
* Text rỗng/image-only -> NO_EXTRACTABLE_TEXT.
* Sau extraction chạy quality gates §8.5, gồm legacy-font/mojibake heuristic cho TCVN3/VNI.

## 8.3 DOCX

* python-docx đọc paragraph/table theo document order; lxml/OOXML xử lý numbering, tracked changes, textbox.
* Automatic numbering được materialize thành prefix text theo fixture hỗ trợ.
* Tracked changes: lấy accepted-state text; deleted bỏ, inserted giữ. Comment/footnote bỏ khỏi canonical body theo FR-08.
* Textbox đưa gần anchor paragraph; case không tái dựng ổn định phải ghi known limitation/fixture.
* Canonical char limit 100.000 sau normalization.

## 8.4 Canonicalization

```text
canonicalize(chunks):
  1. normalize mỗi chunk Unicode NFC
  2. CRLF/CR -> LF
  3. NBSP -> normal space
  4. trim trailing spaces per line; không collapse structural newline
  5. cap blank lines liên tiếp ở 2
  6. join chunks theo document order bằng LF
  7. NFC lại và assert Unicode hợp lệ
```

Không lowercase, không bỏ dấu, không thay số/tiền/tỉnh/chức danh.

## 8.5 Quality gates

| Gate | Default TDD 0.2 | Kết quả |
|---|---|---|
| Text hữu ích | >=100 ký tự non-whitespace | Dưới: NO_EXTRACTABLE_TEXT |
| Replacement U+FFFD | <= max(5, 0.2% chars) | Vượt: UNSUPPORTED_TEXT_ENCODING |
| Control chars ngoài LF/TAB | <=0.1% | Vượt: UNSUPPORTED_TEXT_ENCODING |
| Printable ratio | >=95% | Dưới: UNSUPPORTED_TEXT_ENCODING |
| Legacy-font suspicious glyph ratio | configurable, default >1% trên text >=200 chars | Kích hoạt secondary check |
| Vietnamese plausibility | secondary: từ phổ biến + dấu tiếng Việt + mojibake pattern | Fail -> UNSUPPORTED_TEXT_ENCODING |

Legacy-font detector không chỉ dựa U+FFFD. Nó dò các pattern thường gặp khi TCVN3/VNI bị extract sai như `®`, `¸`, `µ`, `¶`, `¬`, chuỗi dạng `Hîp`, `®ång`, kết hợp với tỷ lệ từ tiếng Việt hợp lệ thấp. Một ký tự đơn lẻ không đủ để reject; fixture font cũ trong D1/test phải fail như NFR-DATA-03 yêu cầu.

Các ngưỡng là cấu hình extraction version; chỉ tune trên D1, không T1/T2.

## 8.6 Offset contract cross-runtime

Backend tính `start_char/end_char` bằng Python Unicode code point. API trả `offset_unit="unicode_code_point"`. Frontend JavaScript không được dùng trực tiếp index này với UTF-16 string khi có non-BMP; phải build mapping code point -> UTF-16 offset rồi mới highlight. Fixture có emoji/non-BMP để kiểm tra.
