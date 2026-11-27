"""Read-only Dev risk support audit; never infer risk labels from clause labels."""
import argparse
import hashlib
import json
from pathlib import Path

from app.risk.taxonomy import RISK_LABELS

ALLOWED = {'D1_m2_risk_gold_v03': ('risk_gold_v1', 'items'),
           'D2_injection_gold_v01': ('injected_error_gold_v2', 'injections')}


def audit(paths, risk_labels):
    """Count declared annotations, not synthetic role-expanded retrieval rows."""
    paths = [Path(p).resolve() for p in paths]
    if len(set(paths)) != len(paths):
        raise ValueError('duplicate input path')
    # All paths must pass before even one file is read.
    if any(p.parent.name not in ALLOWED for p in paths):
        raise ValueError('only explicitly allowed Dev Gold directories may be read')
    support = dict.fromkeys(sorted(risk_labels), 0)
    debt, bindings = [], {}
    for path in paths:
        raw = path.read_bytes()
        payload = json.loads(raw)
        schema, key = ALLOWED[path.parent.name]
        if payload.get('schema_version') != schema or not isinstance(payload.get(key), list):
            raise ValueError('unexpected Dev annotation schema')
        bindings[str(path)] = hashlib.sha256(raw).hexdigest()
        for row in payload[key]:
            label = row.get('risk_label')
            if not isinstance(label, str) or label not in support:
                debt.append({'source': str(path), 'clause_id': row.get('clause_id'),
                             'declared_risk_label': label, 'action': 'OWNER_ADJUDICATION_PENDING'})
            else:
                support[label] += 1
    return {'status': 'SCHEMA_DEBT' if debt else 'VALID_DECLARED_SUPPORT',
            'support': support, 'invalid_annotations': debt, 'sources_sha256': bindings,
            'held_out_read': False, 'risk_acceptance': 'NOT_ESTABLISHED'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.source, RISK_LABELS)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps({'status': result['status'], 'invalid_annotations': len(result['invalid_annotations'])}))


if __name__ == '__main__':
    main()
