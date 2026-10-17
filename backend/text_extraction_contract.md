# Text Extraction Contract

**Owner:** Person 4 — System / Backend
**Consumers:** Person 1 — Clause AI, Person 5 — Frontend / Product
**Authority:** SRS 1.4 (FR-05, FR-07, FR-08, DEC-26, NFR-DATA-02/03) and TDD 0.2 §8 (canonical text), §9–§11 (masking, segmentation). If this file disagrees with them, they win. Updated 17/10/2026 (SRS Appendix C, C-19).

Supported inputs are PDF and DOCX only. Legacy `.doc` and scans/image-only files are rejected (FR-05, FR-06).

---

## 1. Canonical Text

For each session the backend produces one **canonical text** string (plus an `extraction_version`).

`canonical_text` is the single source for quotes, clause spans, highlighting and export quotes.

It is kept in the in-memory session only (TTL 60 minutes). It is **not** stored in a database or any persistent store (NFR-DATA-04). SQLite holds metadata only.

Clause AI (the LLM) never receives `canonical_text`, original text or offsets. PII masking runs on the whole `canonical_text` first, and only the **masked text** (same length) is sent out. The LLM does not create or change spans or quotes.

After segmentation starts, `canonical_text` must not be reformatted or modified.

---

## 2. Unicode and Encoding

Preserve Unicode, including Vietnamese diacritics. Use UTF-8 for any file read/write.

Normalize to NFC before anything else uses the text:

```python
import unicodedata

text = unicodedata.normalize("NFC", text)
```

Do not use lossy encodings (`cp1252`, `latin-1`) for Vietnamese. Text with replacement characters, control characters, mojibake or legacy-font patterns (TCVN3/VNI) beyond the TDD §8.5 thresholds is **REJECTED** (`UNSUPPORTED_TEXT_ENCODING`), not passed to AI (NFR-DATA-03).

---

## 3. Newlines

Structural newlines are preserved, in particular between a clause heading and its content.

Correct:

```text
Điều 1. Công việc
Người lao động có trách nhiệm...
```

Incorrect:

```text
Điều 1. Công việc Người lao động có trách nhiệm...
```

CRLF/CR become LF. Do not collapse the document into one line.

---

## 4. Whitespace

One rule set for every format (TDD §8.4):

- NBSP becomes a normal space; tabs become a single space,
- trim trailing spaces per line,
- do not collapse structural newlines or turn newlines into spaces,
- cap consecutive blank lines at 2.

Do not use `" ".join(text.split())`: it removes meaningful newlines. Do not lowercase, strip diacritics, or change numbers, amounts, place names or job titles.

---

## 5. Reading Order

`canonical_text` follows natural human reading order for PDF and DOCX.

For multi-column pages, read each column top to bottom and do not interleave lines across columns:

```text
left column top -> left column bottom
-> right column top -> right column bottom
```

---

## 6. Header and Footer

Repeated page headers, footers and lone page numbers are removed **before** `canonical_text` is produced, when they can be identified reliably (TDD §8.2: a normalized line repeated on at least 60% of pages in the header/footer zone). Do not remove real contract content that only looks like a header or footer.

---

## 7. Offset and Span Convention

All offsets are **Unicode code points after NFC** (DEC-26), not bytes and not UTF-16 units. The API returns `offset_unit = "unicode_code_point"`. Frontend JavaScript must convert code point to UTF-16 index before slicing or highlighting (TDD §8.6).

- `start_char`: inclusive
- `end_char`: exclusive

For every clause:

```python
canonical_text[start_char:end_char] == clause.original_text
```

Clauses are a **non-overlapping partition**; no boundary may fall inside a PII placeholder; at most 150 clauses. A parent clause ends before the body of its child clause.

If the invariant cannot be satisfied, the span is invalid: the system must not silently guess a replacement span and the frontend must not highlight an uncertain location. The run fails with a typed error; partial results are never returned.

Evaluation data note: dataset rows with `offset_quality = CONTEXT` have no exact span (`span = null`) and are never scored as exact gold spans (TDD §18.3).

---

## 8. Determinism

The same source file and the same `extraction_version` must produce identical `canonical_text`. Repeated extraction must not change whitespace, newlines, reading order or header/footer handling.

---

## 9. Extraction Versioning

Every canonical text is associated with an `extraction_version` (for example `extract_v1.1`, as in the TDD VersionPins). It is recorded in the output version pins (FR-29) and in metadata-only RunLog.

Increment it whenever a change can alter `canonical_text`, including normalization rules and quality-gate thresholds (thresholds are tuned on D1/D2 only, never on T1/T2).

A session is never re-extracted into an old result: a retry or new run recomputes all downstream artifacts (masking, spans, graph, AI output) from the new canonical text. Old spans are never reused with a different canonical text.

---

## 10. Responsibility and Review

Person 4 owns document extraction and production of `canonical_text`.

Changes to whitespace/newline behavior, reading order, header/footer removal, offset semantics or quality gates must be synchronized with Person 1 and Person 5 (and Person 3 for masking). Documentation-only changes do not need cross-team review.

---

## Core Invariant

```python
canonical_text[start_char:end_char] == clause.original_text
```

Backend, segmentation and frontend operate on the same canonical text so clause boundaries and highlighting stay consistent.
