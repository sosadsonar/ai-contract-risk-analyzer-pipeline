"""Audit the nine legacy unmatched references without turning CONTEXT into gold.

Run from repo root: python scripts/audit_data_lead.py --output docs/data_lead_span_audit.json
Reads the pinned data submodule only; does not modify annotations or call a model.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def validate_reference(row, raw):
    start, end = int(row['start_offset']), int(row['end_offset'])
    if not 0 <= start < end <= len(raw):
        raise ValueError(f"{row['clause_id']}: offset out of bounds")
    quote = raw[start:end]
    if not quote.strip():
        raise ValueError(f"{row['clause_id']}: blank source reference")
    if row['offset_quality'] == 'EXACT':
        if ' '.join(quote.split()) != ' '.join(row['clause_text'].split()):
            raise ValueError(f"{row['clause_id']}: EXACT mismatch")
    elif row['offset_quality'] == 'CONTEXT':
        if 'OFFSET_CONTEXT' not in row['notes']:
            raise ValueError(f"{row['clause_id']}: missing CONTEXT note")
    else:
        raise ValueError(f"{row['clause_id']}: unknown offset quality")
    return quote


def validate_context_reference(row, raw, expected):
    quote = validate_reference(row, raw)
    if (row['clause_id'] != expected['clause_id']
            or row['contract_id'] != expected['contract_id']
            or row['offset_quality'] != 'CONTEXT'
            or expected['offset_quality'] != 'CONTEXT'
            or (int(row['start_offset']), int(row['end_offset'])) !=
               (int(expected['start_offset']), int(expected['end_offset']))):
        raise ValueError(f"{row['clause_id']}: reviewed context anchor mismatch")
    return quote


def audit(data_root):
    processed = data_root / 'data/processed'
    legacy = read_csv(processed / 'clauses_v04.csv')
    rows = read_csv(processed / 'clauses_v06.csv')
    by_id = {r['clause_id']: r for r in rows}
    unmatched = [r for r in legacy if not r['start_offset'] and not r['end_offset']]
    if len(unmatched) != 9:
        raise ValueError('Expected the nine legacy v04 unmatched records')
    for old in legacy:
        row = by_id[old['clause_id']]
        for key in ('contract_id','section_title','clause_text','clause_type','annotation_status'):
            if row[key] != old[key]:
                raise ValueError(f"{row['clause_id']}: original annotation changed ({key})")
    raw_paths = {r['contract_id']: processed / 'raw_text' / (r['contract_id'] + '.txt') for r in rows}
    raw = {c:p.read_text(encoding='utf-8') for c,p in raw_paths.items()}
    anchor_script = data_root / 'scripts/build_context_offsets.py'
    anchor_spec = importlib.util.spec_from_file_location('reviewed_context_anchors', anchor_script)
    anchors = importlib.util.module_from_spec(anchor_spec)
    anchor_spec.loader.exec_module(anchors)
    # Reconstruct from the historical rows and pinned reviewed source anchors.
    # Merely pointing to a nonblank in-bounds slice cannot certify association.
    expected = {r['clause_id']: r for r in anchors.fill_context_offsets(legacy, raw)}
    for row in rows:
        validate_reference(row, raw[row['contract_id']])
    cases = []
    for old in unmatched:
        row = by_id[old['clause_id']]
        if row['offset_quality'] != 'CONTEXT':
            raise ValueError(f"{row['clause_id']}: legacy unmatched cannot be promoted to exact gold")
        reason = ('SOURCE_TEXT_DIFFERENCE' if row['clause_id'] == 'HDLD001_C014'
                  else 'EMPLOYEE_DAMAGE_RIGHT_TAXONOMY_GAP' if row['clause_id'] == 'HDLD004_C027'
                  else 'CONTEXT_REUSE_AFTER_SPLIT')
        cases.append({'clause_id':row['clause_id'],'contract_id':row['contract_id'],
                      'clause_type':row['clause_type'],'clause_text':row['clause_text'],
                      'start_offset':int(row['start_offset']),'end_offset':int(row['end_offset']),
                      'source_quote':validate_context_reference(row,raw[row['contract_id']],expected[row['clause_id']]),
                      'raw_text_sha256':hashlib.sha256(raw_paths[row['contract_id']].read_bytes()).hexdigest(),
                      'source_notes':row['notes'],'audit_reason':reason,
                      'source_reference_verified':True,'exact_span_eligible':False,
                      'legal_risk_ground_truth':None})
    spec = importlib.util.spec_from_file_location('audit_taxonomy', ROOT / 'backend/app/clause/taxonomy.py')
    taxonomy = importlib.util.module_from_spec(spec); spec.loader.exec_module(taxonomy)
    labels = {r['clause_type'] for r in rows}
    if labels != set(taxonomy.CLAUSE_LABELS):
        raise ValueError('Pipeline/data label vocabulary mismatch')
    dataset = processed / 'clauses_v06.csv'
    revision = None
    clean = None
    taxonomy_blob_hash = None
    try:
        top = subprocess.check_output(['git','-C',str(data_root),'rev-parse','--show-toplevel'],text=True,stderr=subprocess.DEVNULL).strip()
        if Path(top).resolve() == data_root.resolve():
            revision = subprocess.check_output(['git','-C',str(data_root),'rev-parse','HEAD'],text=True).strip()
            clean = not subprocess.check_output(['git','-C',str(data_root),'status','--porcelain','--untracked-files=no'],text=True).strip()
            taxonomy_blob = subprocess.check_output(['git','-C',str(data_root),'show',revision+':docs/clause_taxonomy_v03.md'])
            taxonomy_blob_hash = hashlib.sha256(taxonomy_blob).hexdigest()
    except (OSError, subprocess.CalledProcessError):
        pass  # An unpacked release can still be audited by its recorded file hashes.
    return {'source_data_commit':revision,'source_worktree_clean':clean,
            'dataset':'clauses_v06.csv','dataset_sha256':hashlib.sha256(dataset.read_bytes()).hexdigest(),
            'prompt_definition_version':taxonomy.TAXONOMY_VERSION,'data_taxonomy_version':'v03',
            'taxonomy_source_sha256':hashlib.sha256((data_root / 'docs/clause_taxonomy_v03.md').read_bytes()).hexdigest(),
            'taxonomy_source_git_blob_sha256':taxonomy_blob_hash,
            'context_anchor_script_sha256':hashlib.sha256(anchor_script.read_bytes()).hexdigest(),
            'clause_count':len(rows),'offset_quality_counts':dict(Counter(r['offset_quality'] for r in rows)),
            'preserved_legacy_annotation_count':len(legacy),
            'audited_unmatched_count':len(cases),'reason_counts':dict(Counter(c['audit_reason'] for c in cases)),
            'scope':'Source-reference/offset audit; inherited clause labels; no legal-risk adjudication',
            'cases':cases}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root',type=Path,default=ROOT / 'ai_pipeline/data')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    result=audit(args.data_root)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'clauses':result['clause_count'],'offsets':result['offset_quality_counts'],
                      'audited_unmatched':result['audited_unmatched_count'],'reasons':result['reason_counts']}))


if __name__ == '__main__':
    main()
