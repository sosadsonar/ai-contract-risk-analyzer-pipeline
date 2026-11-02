# Annotation Guideline Alignment Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bring the data repository annotation guideline into explicit, traceable alignment with the frozen 12-label taxonomy and the existing OI-10 proposal, without claiming pending N2/N3 approvals.

**Architecture:** Edit only the authoritative guideline in the data repository and add a versioned alignment note to the pipeline repository. Preserve current taxonomy definitions; identify proposed rules separately from approved procedure and leave MS-1 freeze open pending sign-off.

**Tech Stack:** Markdown, PowerShell/Python for consistency checks, Git diff checks.

## Global Constraints

- Preserve the frozen 12-label vocabulary and fingerprint.
- OI-10 policy and three unresolved topics remain proposals until N2/N3 sign-off.
- Do not change BRD/SRS/SDD/TDD or accepted labels/data.
- Do not mark a checklist gate complete without approval evidence.

## Review Focus

- Labels remain identical to taxonomy v0.3 and the frozen code set.
- Single-label historic data is not silently reinterpreted as multi-label gold.
- Reviewers can distinguish binding current rules from pending proposals.
- MS-1 status remains pending until N2/N3 confirmation.

### Task 1: Guideline alignment draft

**Files:** Modify `D:/DHCN/Nam3_Ky1/CVDKHMT/ai-contract-risk-analyzer/docs/annotation_guideline.md`; add alignment note in pipeline repository.

- [ ] Record taxonomy/version provenance and the existing approved single-label rules.
- [ ] Add clearly marked OI-10 proposal text for 1–3 labels, primary-label tie-break, OTHER handling, and historic v06 conversion limitations.
- [ ] Add the three disputed-topic mappings as pending proposals, not operative policy.
- [ ] Add sign-off table/status and changelog; do not freeze MS-1.
- [ ] Verify label list, proposal attribution, no BRD/SRS edits, diff cleanliness, and document consistency.
