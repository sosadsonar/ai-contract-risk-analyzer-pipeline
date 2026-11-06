<!-- nguồn: N2_PROGRESS_AUDIT_2026-11-02.md | mục: N2 Data Lead progress audit — 2026-11-02 > Corpus inventory recheck — 2026-11-02 | 1637 ký tự | trước: 07_release-receipt-integrity-recovery-2026-11-02.md | sau: 09_scoped-x-03-closure-and-recount-2026-11-02.md -->

## Corpus inventory recheck — 2026-11-02

The current pipeline working tree contains 16 unique provision candidates:
Articles 13 (2), 14 (2), 15 (2), 16 (2), 17 (3), and Article 21 clause 1
points c/d/đ/g/i (5). `label_map.yaml` has five mappings for the Article 21
points. These rows are still in a `DRAFT` corpus and are not approved retrieval
content. A whitespace-normalized exact-string comparison against the D-drive
OCR candidate for 18/VBHN-VPQH matched 7/16 rows; 9 did not match. Since the
OCR is unproofread, this comparison only identifies review work; it does not
establish legal text errors or effective dates. The discrepancy is documented
in `data/legal_corpus/README.md`; no provision text or checksum was changed.

Rechecked the D1 segmentation review package: 183/183 rows have unique IDs and
structurally valid code-point spans; 0/183 rows contain reviewer ID or notes.
The v07 preview remains 306 rows (234 `REVIEWED`, 72 `NEEDS_REVIEW`) over eight
contract IDs; this is preview status, not gold or accepted T1. These queue
checks do not close an N2 checkbox; at this checkpoint the count was 7/19.

A metadata-only reviewer queue for the 16 provisions was generated in the
D-drive data repository. It includes source/OCR hashes, page hints and blank
review fields; all 16 remain pending, and no provision text is copied into the
queue. The queue builder's 3 tests and the full data-repository suite
(93 tests) pass. Ruff is unavailable in that environment. Corpus checksums
match the manifest; no provision or release status changed. This provides a
review handoff but by itself does not close an N2 checklist item.
