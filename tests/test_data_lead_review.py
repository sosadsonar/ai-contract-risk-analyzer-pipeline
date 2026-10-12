import importlib.util
import csv
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('review_taxonomy', ROOT / 'ai_pipeline/config/taxonomy.py')
taxonomy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(taxonomy)
audit_spec = importlib.util.spec_from_file_location('review_audit', ROOT / 'scripts/audit_data_lead.py')
auditor = importlib.util.module_from_spec(audit_spec)
audit_spec.loader.exec_module(auditor)


class TaxonomyReviewTests(unittest.TestCase):
    def test_effective_date_is_only_defined_as_contract_term(self):
        self.assertIn('hiệu lực', taxonomy.LABEL_DEFINITIONS['CONTRACT_TERM'])
        self.assertNotIn('hiệu lực', taxonomy.LABEL_DEFINITIONS['OTHER'])

    def test_employer_compensation_obligation_is_explicit(self):
        self.assertIn('phải bồi thường cho NLĐ', taxonomy.LABEL_DEFINITIONS['EMPLOYER_RIGHTS_OBLIGATIONS'])
        self.assertIn('quyền được bồi thường của NLĐ', taxonomy.LABEL_DEFINITIONS['OTHER'])

    def test_unapproved_topics_are_not_preassigned_by_v03_mirror(self):
        self.assertNotIn('không cạnh tranh', taxonomy.LABEL_DEFINITIONS['EMPLOYEE_OBLIGATIONS_DISCIPLINE'])
        self.assertNotIn('giải quyết tranh chấp', taxonomy.LABEL_DEFINITIONS['OTHER'])

    def test_definition_revision_is_explicit_and_label_vocabulary_is_unchanged(self):
        self.assertEqual(taxonomy.TAXONOMY_VERSION, 'v04')
        self.assertEqual(set(taxonomy.CLAUSE_LABELS), {
            'JOB_INFO','CONTRACT_TERM','COMPENSATION_BENEFITS','WORKING_TIME','LEAVE',
            'INSURANCE_SAFETY','WORKING_CONDITIONS','TRAINING',
            'EMPLOYEE_OBLIGATIONS_DISCIPLINE','EMPLOYER_RIGHTS_OBLIGATIONS','TERMINATION','OTHER'})
        with self.assertRaises(TypeError):
            taxonomy.LABEL_DEFINITIONS['OTHER'] = 'mutated'


class ContextAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data_root = ROOT / 'ai_pipeline/data'
        with (cls.data_root / 'data/processed/clauses_v06.csv').open(encoding='utf-8-sig', newline='') as f:
            cls.context = next(r for r in csv.DictReader(f) if r['offset_quality'] == 'CONTEXT')
        cls.raw = (cls.data_root / 'data/processed/raw_text' / (cls.context['contract_id'] + '.txt')).read_text(encoding='utf-8')

    def test_audit_covers_all_nine_without_exact_gold_or_legal_labels(self):
        report = auditor.audit(self.data_root)
        self.assertEqual({c['clause_id'] for c in report['cases']}, {
            'HDLD001_C014','HDLD003_C018','HDLD003_C018A','HDLD004_C023',
            'HDLD004_C024','HDLD004_C025','HDLD004_C026','HDLD004_C027','HDLD004_C043'})
        for case in report['cases']:
            self.assertFalse(case['exact_span_eligible'])
            self.assertIsNone(case['legal_risk_ground_truth'])

    def test_promoting_context_to_exact_rejects_the_nonmatching_reference(self):
        row = dict(self.context, offset_quality='EXACT')
        with self.assertRaisesRegex(ValueError, 'EXACT mismatch'):
            auditor.validate_reference(row, self.raw)

    def test_out_of_bounds_reference_is_rejected(self):
        row = dict(self.context, end_offset=str(len(self.raw) + 1))
        with self.assertRaisesRegex(ValueError, 'out of bounds'):
            auditor.validate_reference(row, self.raw)

    def test_context_without_audit_note_is_rejected(self):
        row = dict(self.context, notes='')
        with self.assertRaisesRegex(ValueError, 'missing CONTEXT note'):
            auditor.validate_reference(row, self.raw)


if __name__ == '__main__':
    unittest.main()
