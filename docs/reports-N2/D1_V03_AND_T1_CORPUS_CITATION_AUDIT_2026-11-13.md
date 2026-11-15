# D1 v03 / T1 M2 citation audit — 2026-11-13

## Scope and sources

Read-only metadata audit of the user-supplied `M2_REVIEW_HANDOFF_DECISIONS_v2.0_2026-11-13`, Data repository D1 M2 worksheet v03 and T1 M2 candidate v02, Pipeline `data/legal_corpus/provisions.jsonl`, and TDD §18.3. No T1/T2 contract text was opened. This report records technical readiness; it does not authenticate the three named human decisions or adjudicate legal relevance.

## D1 proposal and existing Gold

- The directive lists 22 unique `HDLD001–003` employee units. All 22 IDs and proposed offsets match the 366-row D1 worksheet v03; all currently have adjudicated outcome `NO_RISK` in **Gold v02**.
- For all 22, the worksheet source SHA-256 matches the local D1 raw-text file and the stated `[start,end)` slice is nonempty and in range. This verifies location, not the proposed legal interpretation.
- The existing Gold v02 has six positive `UNILATERAL_CHANGE` items. Thus 28 positives is a **proposed v03 total**, not a current Gold count.
- Nine D1 clause IDs produce 18 `CONTEXT` role rows with blank source span. TDD §18.3 explicitly says `CONTEXT` clause-label rows have null span and are excluded from exact Gold span scoring for M1/M4. An M2 span-alignment exclusion policy needs to be stated in the M2 metric specification; §18.3 alone does not explicitly define its M2 denominator. Preserve these rows and do not silently count them as exact negatives or exact spans.

## Closed corpus inventory

The Pipeline corpus currently has 16 nodes, effective from 2021-01-01 and with no `effective_to` value. Exact IDs:

`BLLD2019:art21:cl1:ptc`, `BLLD2019:art21:cl1:ptd`, `BLLD2019:art21:cl1:ptđ`, `BLLD2019:art21:cl1:ptg`, `BLLD2019:art21:cl1:pti`, `BLLD2019:art13:cl1`, `BLLD2019:art13:cl2`, `BLLD2019:art14:cl1`, `BLLD2019:art14:cl2`, `BLLD2019:art15:cl1`, `BLLD2019:art15:cl2`, `BLLD2019:art16:cl1`, `BLLD2019:art16:cl2`, `BLLD2019:art17:cl1`, `BLLD2019:art17:cl2`, `BLLD2019:art17:cl3`.

`art21:cl1:pte`, `art21:cl1:ptk`, and proposed specialist nodes for Articles 22, 29, 35, 36, 48, 62, 103, 107, 111 and 129 are absent. Exact ID existence does not establish citation relevance. Do not substitute another Article 21 point solely to make M3a pass. `PENDING_CORPUS_NODE` / `INSUFFICIENT_EVIDENCE` are statuses, not corpus citation IDs; the existing D1 converter requires complete citation fields for each `RISK` item and does not validate membership in the closed corpus.

Of the 22 D1 proposals, eight have an explicit candidate ID that exists (`ptc`: 3, `ptđ`: 3, `ptg`: 2). The six training proposals name missing `ptk`; two wage proposals name missing `pte` as first choice, and the other six proposals lack their specialist node. Every proposed label and basis still requires source and legal review. No v03 Gold or v04 adjudicated worksheet was created by this audit.

## T1 candidate review

- The private packet has 1,494 rows, all `NEEDS_REVIEW`; reviewer/annotator/adjudicator fields are blank. Seven individual positive candidates are present and four grouped proposals are described in Data PR #20 review note. Only three of seven direct rows currently have a candidate citation ID; those three (`HDLD012_C005`, `C006`, `C016`) name existing Article 21 IDs. The remaining four need source/citation review.
- The grouped units are `HDLD011_C102–C107`, `HDLD011_C048–C049`, `HDLD011_C077–C078`, and `HDLD011_C111–C113` (all employee role). Their row-level anchor remains undecided. No label is copied across the group.
- The other 1,487 rows are `UNREVIEWED`, not verified negatives. Start offset 0 or short length alone does not prove ineligibility. Keep full segmentation coverage; classify eligibility and Gold risk decisions separately.
- T1 is held out. Any review of authorized T1 sources must be a controlled human annotation process, not a source of model/rule tuning. The current candidate packet and directive text do not prove that three independent decisions were entered.

## Release gate

Before creating D1 v03 or T1 Gold: obtain traceable row-level annotator/reviewer/adjudicator decisions; confirm source spans and source hashes; decide each label, basis and legally relevant citation; resolve the corpus gap or record an explicit versioned evidence exception; define M2 treatment of `CONTEXT` and non-clause units; run converter and hash/coverage checks. Preserve D1 v02 and the T1 candidate packet unchanged.
