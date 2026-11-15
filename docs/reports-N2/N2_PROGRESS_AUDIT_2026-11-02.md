# N2 Data Lead progress audit — 2026-11-02

## Counting method

Count only the 19 top-level checkboxes directly under `**N2**` across Weeks
1–7 in `PROGRESS.md`; exclude nested subtasks, other roles and week gates.
This is a checkbox count, not an estimate of hours, effort or accepted project
value.

## Current result

At the initial audit checkpoint the checklist had **7/19 complete = 36.8%**.
After the scoped X-03 draft-import and offline-smoke verification, the count
was **9/19 = 47.4%**. The source-checked C-13(a) technical batch documented at
the end of this audit brought the count to **10/19 = 52.6%**. The X-10 intake
kickoff is now recorded at its planned start-only scope, bringing the current
count to **11/19 = 57.9%**. This is the N2 checklist ratio only, not overall
project completion or legal readiness.

Completed items:

1. Week 1 — corpus format and development provisions (DRAFT only).
2. Week 1 — draft tier-one law catalog (not MS-1 legal approval).
3. Week 3 — C-12(a) offline corpus loader/validator and fixtures.
4. Week 4 — C-12(b) fixture-backed BaselineRetriever.
5. Week 5 — C-13(b) offline graph expansion/ranking/fallback fixture scope.
6. Week 1 — D1 inventory and working scope: HDLD001–004 = 183 clauses per
   BRD §8.2; HDLD005 remains an additional 51-clause v06 source. Local regex
   scan found no email/phone/continuous 9–12 digit pattern in canonical text,
   but did not establish de-identification. Manual review of names, images,
   metadata, indirect identifiers and source rights remains open.
7. Week 6 — N2 evaluation harness scope: strict `load_dataset`, M3a/M4/M5,
   paired M8 metric and callback runner. Focused pipeline tests report **32
   passed**. This closes the N2-scoped fixture/offline task only; C-18 overall
   remains open for production wiring, other-role metrics, approved gold and
   D1/T2 execution.
8. Week 2 — X-03 initial import: 16 unique DRAFT provision candidates and
   five label mappings are present. Legal wording/effectivity review remains
   pending; this closes only the planned import of the draft batch.
9. Week 3 — X-03 offline baseline smoke: the existing focused test loads the
   real DRAFT corpus with explicit `allow_draft=True` and confirms the
   BaselineRetriever returns candidates. Default loading still rejects DRAFT;
   this is not a retrieval benchmark or Recall@5 result.
10. Week 4 — C-13(a) first technical batch: automatic `PARENT_OF` plus one
    literal Article 14 self-reference edge visually checked against page 7 of
    the official 18/VBHN-VPQH PDF. The PDF SHA-256 is
    `5A01A5B4B778B78C7BC9372E3A7270735BD98C28160604BFF95DB06BB3345A6F`;
    corpus and graph tests pass (50 tests). This does not establish current
    effectivity or independent legal sign-off; the corpus remains DRAFT.
11. Week 2 — X-10 kickoff only: candidate-source triage, intake/reuse-rights
    and de-identification workflow, and outreach queues exist. The manifest has
    22 candidates and 0 T1-eligible records; permission requests remain unsent.
    Intake-gate tests report 9 passed. This closes the planned kickoff, not the
    X-10 target of at least 10 accepted, de-identified contracts.

## Work advanced but still open

- Law source collection expanded to six official-source OCR candidates with
  restricted metadata-only hierarchy indexes (4,826 nodes total). Every node
  remains `PENDING_LEGAL_REVIEW`; no provision, graph edge or effectivity
  interval was approved. Decree 283/2026 is the current penalty-law candidate
  from 2026-09-10; Decree 12/2022 is retained for historical/transition review.
- At least 10 rights-cleared, independently reviewed and de-identified T1
  contracts; independent legal review/effectivity verification and expansion of the
  tier-one corpus, D1 gold
  labels/segmentation/privacy and X-10 remain open. C-18 overall also remains
  open across roles. They require verified legal content, human adjudication,
  rights/privacy evidence or remaining evaluation/runtime work. Do not count
  OCR coverage or synthetic fixtures as accepted corpus/gold/benchmark evidence.

## Verification

- Direct parse of `PROGRESS.md`: 19 top-level N2 items, currently 11 marked
  `[x]` (57.9%).
- D-drive data repository full test suite on 2026-11-02: **94 passed** after
  adding the visual-review source-receipt regression test.
- D1 review-queue audit: **PASS**, 183/183 rows covered with valid candidate
  spans; reviewer/note fields are filled on 0/183, so there is still no gold
  segmentation or M1 result.
- VBHN visual-review log: all 3 page records now match the OCR candidate's
  receipted PDF hash and page range. Pages 44, 45 and 61 were visually
  rechecked from the receipt-matched PDF; this is structural Data QA, not legal
  review, and the OCR index remains unchanged.
- OCR/source and six index receipt audit: **6/6 receipt pairs**, source and
  candidate hashes matched, page markers complete, node IDs unique, parent IDs
  present, no provision-text columns, all nodes pending review.
- No CI/GitHub merge claim is made by this local audit.

## Additional legal source work — 2026-11-02 (not counted as a checkbox)

The official Government Portal attachment for 18/VBHN-VPQH was downloaded again
from the linked PDF and OCRed page-by-page (86/86 pages). A metadata-only
hierarchy index was rebuilt with 1,082 rows: 220 expected articles, 610 clause
candidates and 251 point candidates. Five article headings were not detected
by OCR (76, 77, 78, 79, 166). The restricted source/candidate/index hashes and
counts are recorded in the D-drive data repository receipts. All rows remain
`PENDING_LEGAL_REVIEW`; this adds no approved provision, verified effectivity,
edge, gold label or X-03 completion. The original corpus files and checklist
count at that checkpoint remained 7/19 (36.8%); see the later scoped X-03
recount below.

## Guideline alignment draft — 2026-11-02 (not counted as frozen)

Updated the authoritative data-repository annotation guideline to distinguish
its historic/current single-label procedure from the proposed OI-10 rules.
Added proposal wording for the 1–3 label policy, v06/M7 conversion limits,
three unresolved topic mappings, and an N1/N2/N3 sign-off table. The changes do
not modify taxonomy/code/data or BRD/SRS, and do not claim MS-1 approval. The
N2 checklist item “Freeze annotation guideline; chốt danh mục tầng 1” remains
open until N2/N3 and project owners confirm both guideline policy and the tier-one
catalog. Count remains 7/19 (36.8%).

## Release receipt integrity recovery — 2026-11-02

The working guideline was restored byte-for-byte from the current Git object
(`HEAD:docs/annotation_guideline.md`), whose SHA-256 matches the v06-rc1
manifest. The unapproved OI-10 content is preserved separately in
`docs/annotation_guideline_oi10_draft.md`. The targeted release receipt test
and full data repository suite both pass (81 tests). This repairs release
integrity; it does not constitute annotation-policy approval or close the MS-1
N2 checkbox. N2 checklist remains 7/19 (36.8%).

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

## Scoped X-03 closure and recount — 2026-11-02

Closed the two X-03 checklist items only at their stated draft/offline scope:
the 16-row tier-one candidate import with five label mappings, and the actual
corpus smoke test that explicitly opts into DRAFT and returns baseline
candidates. The default approval gate remains in force. No law has been
approved, no current-effectivity claim was added, and no Recall@5 or legal
retrieval quality result is claimed. Direct recount of the 19 top-level N2
checkboxes in Weeks 1–7 now gives **9/19 = 47.4%**; one more verified checkbox
is required to reach 50%.

## Source-checked C-13(a) first batch — 2026-11-02

Added one `REFERS_TO` edge from Article 14 clause 1 to clause 2 after visually
checking page 7 of the local official 18/VBHN-VPQH attachment. The page shows
the literal phrase “khoản 2 Điều này” in clause 1 and the referenced clause 2
in the same article. The source SHA-256 is recorded above and in
`data/legal_corpus/README.md`. Both the corpus and graph regression tests pass;
the corpus validator confirms the edge endpoints exist and the manifest
checksum matches. This closes C-13(a)'s first technical batch, not independent
legal approval, effectivity review, whole-law coverage, or release readiness.
The corpus remains `DRAFT`, default loading remains blocked, and this work
supports no legal citation, contract-risk assessment, or Recall@5 claim. The
C-13(a) checkpoint count was **10/19 = 52.6%**.

## X-10 intake kickoff — 2026-11-02

Verified the D-drive intake manifest has 22 unique candidate IDs and all 22
have `t1_eligible=no`. The intake guide documents source/rights review,
manual privacy screening, independent acceptance and evaluation separation;
the source-holder queue and public contact routes are prepared, but requests
remain unsent. The focused intake-gate test file reports 9 passed. This is
enough to close only the Week 2 “begin acquisition and establish the process”
kickoff checkbox. No T1 contract was accepted, no de-identification was
approved, and the X-10 target remains open. Current direct recount:
**11/19 = 57.9%**.
