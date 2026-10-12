# Text Extraction Contract

**Owner:** Person 4 — System / Backend  
**Consumers:** Person 1 — Clause AI, Person 5 — Frontend / Product

This document defines the rules for producing and using `canonical_text` across the system.

---

## 1. Canonical Text

For each contract, the backend produces one **canonical text** string.

This exact string is used for:

- storage in the backend/database,
- input to Clause AI,
- clause span calculation,
- frontend highlighting.

After Clause AI starts using this text, it must not be reformatted or modified.

---

## 2. Unicode and Encoding

All extracted text must preserve Unicode characters, including Vietnamese diacritics.

When text is read from or written to files, UTF-8 must be used.

Before storing or passing text to Clause AI, normalize Unicode to NFC:

```python
import unicodedata

text = unicodedata.normalize("NFC", text)
```

Lossy encodings such as `cp1252` or `latin-1` must not be used for Vietnamese text.

---

## 3. Newlines

Newlines that represent document structure must be preserved.

In particular, keep the newline between a clause heading and its content.

Correct:

```text
Điều 1. Công việc
Người lao động có trách nhiệm...
```

Incorrect:

```text
Điều 1. Công việc Người lao động có trách nhiệm...
```

Do not collapse the whole document into a single line.

---

## 4. Whitespace

Whitespace normalization must follow the same rules for all supported document formats.

Rules:

- convert tabs to a single space,
- collapse consecutive spaces into a single space,
- preserve newlines,
- do not convert newlines into spaces.

Example:

```python
import re

text = text.replace("\t", " ")
text = re.sub(r"[ ]{2,}", " ", text)
```

Do not use:

```python
" ".join(text.split())
```

because it removes meaningful newlines.

---

## 5. Reading Order

`canonical_text` must follow the natural human reading order of the source document.

This rule applies to:

- PDF
- DOC
- DOCX

For multi-column documents, content must not be interleaved across columns.

Example for a two-column page:

```text
left column top -> left column bottom
-> right column top -> right column bottom
```

instead of alternating line-by-line between columns.

---

## 6. Header and Footer

Repeated page headers, footers, and page numbers should be removed when they can be identified reliably.

Removal must happen **before** `canonical_text` is stored or passed to Clause AI.

The parser must avoid removing real contract content that only looks similar to a header or footer.

---

## 7. Span Convention

Clause spans always refer to the exact `canonical_text`.

Convention:

- `start_char`: inclusive
- `end_char`: exclusive

The following invariant must hold:

```python
canonical_text[start_char:end_char] == clause.original_text
```

If this invariant cannot be satisfied:

- the span is considered invalid,
- the system must not silently guess a replacement span,
- the frontend must not highlight an uncertain location.

If the Clause AI pipeline uses `review_zone`, an invalid span should be treated as a review-required case such as `RED`.

---

## 8. Determinism

Given the same source document and the same extraction implementation, the backend must produce identical `canonical_text`.

Repeated extraction of the same file must not randomly change:

- whitespace,
- newlines,
- reading order,
- header/footer handling.

---

## 9. Extraction Changes

If extraction or normalization logic changes in a way that changes `canonical_text`, previously generated clause spans must be regenerated.

Old spans must never be reused with newly extracted canonical text.

For this project, no parser version field is required in the database. The team only needs to ensure that affected contracts are reprocessed when extraction logic changes.

---

## 10. Responsibility and Review

Person 4 owns document extraction and production of `canonical_text`.

Changes that affect any of the following must be synchronized with Person 1 and Person 5:

- whitespace normalization,
- newline behavior,
- reading order,
- header/footer removal,
- span semantics.

Minor documentation-only changes do not require cross-team review.

---

## Extraction Versioning

Each stored canonical text must be associated with an `extraction_version`.

The version represents the extraction and normalization logic used to
produce `canonical_text`.

Example:

- `1.0`: initial extraction pipeline
- `2.0`: updated parser or normalization rules

The extraction version must be incremented whenever a change can modify
the resulting `canonical_text`.

If a contract is re-extracted using a newer extraction version:

- the new canonical text replaces the old canonical text,
- previously calculated clause spans must be regenerated,
- old spans must not be reused with the new canonical text.

Clause spans are valid only for the canonical text version on which
they were originally calculated.

## Core Invariant

The most important rule in this contract is:

```python
canonical_text[start_char:end_char] == clause.original_text
```

The backend, Clause AI, and frontend must all operate on the same canonical text so that clause boundaries and highlighting remain consistent.
