# Corpus v2 runtime release gate — 15/11/2026

The v1 runtime snapshot `legal_corpus_2026-11-14_v02` is preserved exactly and its three file checksums are pinned in the loader. Its manifest states `APPROVED`, while its README still says `DRAFT`; a per-item human approval packet was not found in the inspected branch. This historical mismatch remains an open evidence issue. The new gate applies to any other approved corpus version; it does not retroactively claim v1 legal sign-off.

An approved v2 manifest must pin SHA-256 for `provisions.jsonl`, `edges.jsonl`, `label_map.yaml` and `review_receipts.json`. A DRAFT manifest can be opened only with `allow_draft=True` and is never a runtime-approved release. A new approved release missing the fourth checksum or receipt file fails closed. The receipt bundle has five collections:

| Collection | Required evidence checked by the loader |
| --- | --- |
| `sources` | Distinct source ID, document ID, HTTPS official-source link, 64-digit SHA-256, access date, rights decision `APPROVED` |
| `provisions` | Exactly one receipt for each citation ID and version, matching content hash and effective interval; source ID, page/article locator and nonempty amendment history |
| `edges` | Exactly one receipt for every manual runtime edge, with source ID and locator |
| `labels` | Exactly one receipt for every runtime label/citation/weight mapping, with source ID and locator |
| `release` | Release note and human decision |

Each item and the release decision require `decision: APPROVED`, two distinct named reviewers (`reviewer_n2`, `reviewer_independent`) and an ISO review date. The loader also checks provision IDs, NFC, nonempty text, version intervals, graph endpoints and overlapping edge-effective intervals. These checks establish traceability and consistency; the named reviewers must still inspect the signed legal source, exact text, amendment effect and permitted use. A JSON receipt is a review record, not cryptographic proof of a person's identity.

The [Data source review packet](https://github.com/24021368-DucAnh/ai-contract-risk-analyzer/pull/22) and its follow-up PR supply candidate source metadata. No candidate OCR or held-out T1/T2 content has been admitted into this runtime branch. After N2/N3 and an independent reviewer fill and approve the per-item receipts, create a new versioned corpus folder/manifest, compare Dev Graph Off/On and citation relevance, then freeze model and corpus before one newly versioned held-out measurement. Preserve the v1 pin for rollback until that release is accepted.
