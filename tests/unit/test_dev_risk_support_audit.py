"""Risk taxonomy debt must remain distinct from clause-label Gold."""
import json

import pytest

from scripts.audit_dev_risk_support import audit


def write(tmp_path, folder, payload):
    file = tmp_path / folder / 'HDLD001.json'
    file.parent.mkdir(exist_ok=True)
    file.write_text(json.dumps(payload), encoding='utf-8')
    return file


def test_unknown_clause_label_is_debt_not_risk_support(tmp_path):
    path = write(tmp_path, 'D2_injection_gold_v01', {'schema_version': 'injected_error_gold_v2',
        'injections': [{'clause_id': 'x', 'risk_label': 'EMPLOYEE_OBLIGATIONS_DISCIPLINE', 'role': 'EMPLOYEE'},
                       {'clause_id': 'y', 'risk_label': 'DEPOSIT_DOCUMENT_HELD', 'role': 'EMPLOYEE'}]})
    before = path.read_bytes()
    result = audit([path], {'DEPOSIT_DOCUMENT_HELD', 'DISCIPLINE_OBLIGATION'})
    assert result['status'] == 'SCHEMA_DEBT'
    assert result['support'] == {'DEPOSIT_DOCUMENT_HELD': 1, 'DISCIPLINE_OBLIGATION': 0}
    assert len(result['invalid_annotations']) == 1
    assert path.read_bytes() == before


def test_held_out_path_is_rejected_before_read(tmp_path):
    with pytest.raises(ValueError, match='Dev'):
        audit([tmp_path / 'T1_m2_risk_gold_v01' / 'missing.json'], {'RISK'})


def test_missing_label_is_schema_debt(tmp_path):
    path = write(tmp_path, 'D1_m2_risk_gold_v03', {'schema_version': 'risk_gold_v1',
        'items': [{'clause_id': 'x', 'role': 'EMPLOYEE'}]})
    assert audit([path], {'RISK'})['status'] == 'SCHEMA_DEBT'


def test_duplicate_input_does_not_inflate_support(tmp_path):
    path = write(tmp_path, 'D1_m2_risk_gold_v03', {'schema_version': 'risk_gold_v1', 'items': []})
    with pytest.raises(ValueError, match='duplicate'):
        audit([path, path], {'RISK'})
