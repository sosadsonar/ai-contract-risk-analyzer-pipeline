<!-- nguồn: N2_PROGRESS_AUDIT_2026-11-02.md | mục: N2 Data Lead progress audit — 2026-11-02 > Release receipt integrity recovery — 2026-11-02 | 545 ký tự | trước: 06_guideline-alignment-draft-2026-11-02-not-counted-a.md | sau: 08_corpus-inventory-recheck-2026-11-02.md -->

## Release receipt integrity recovery — 2026-11-02

The working guideline was restored byte-for-byte from the current Git object
(`HEAD:docs/annotation_guideline.md`), whose SHA-256 matches the v06-rc1
manifest. The unapproved OI-10 content is preserved separately in
`docs/annotation_guideline_oi10_draft.md`. The targeted release receipt test
and full data repository suite both pass (81 tests). This repairs release
integrity; it does not constitute annotation-policy approval or close the MS-1
N2 checkbox. N2 checklist remains 7/19 (36.8%).
