import pytest

from scripts.evaluate_t1_t2_equivalent_gate import derive_inserted_privacy_spans


def test_projection_keeps_exact_unmodified_field_text():
    source = "abc\nxyz"
    injected = "abc\nBAD\n\nxyz"
    rows = [{"insertion_span": {"start_char": 4, "end_char": 7}}]
    pii, preserve = derive_inserted_privacy_spans(
        source,
        injected,
        rows,
        [{"start_char": 4, "end_char": 7}],
        [{"start_char": 4, "end_char": 7}],
    )
    assert pii == ((9, 12),)
    assert preserve == ((9, 12),)
    assert injected[9:12] == source[4:7]


def test_projection_rejects_new_pii_in_injection():
    source = "abc\nxyz"
    injected = "abc\n0912345678\n\nxyz"
    rows = [{"insertion_span": {"start_char": 4, "end_char": 14}}]
    with pytest.raises(ValueError, match="new PII detector hits"):
        derive_inserted_privacy_spans(source, injected, rows, [], [])
