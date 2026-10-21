"""Mock đầu ra Clause Classification theo schema `clause_output_v3` (C-04/C-17).

Để Risk AI (Người 3) và backend dùng ngay, không cần gọi LLM. Dữ liệu này được test hợp lệ
với schema tại tests/contract/test_clause_output_v3.py. Không còn contract_id/type_scores/
tier/review_zone (DEC-17).
"""


def get_mock_clause_output() -> dict:
    return {
        "schema_version": "clause_output_v3",
        "items": [
            {"clause_id": "cl_0001", "clause_labels": ["EMPLOYEE_OBLIGATIONS_DISCIPLINE", "TERMINATION"]},
            {"clause_id": "cl_0002", "clause_labels": ["COMPENSATION_BENEFITS"]},
        ],
        "model_id": "mock",
        "prompt_version": "clause_prompt_v1",
        "taxonomy_version": "clause_taxonomy_v03",
    }
