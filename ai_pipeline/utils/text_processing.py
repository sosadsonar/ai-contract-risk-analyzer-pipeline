import re
from typing import List, Dict

CLAUSE_PATTERN = re.compile(r'(?m)^(?:\s*)(Điều\s+\d+[\.:]?|\d+\.\d+[\.:]?|[a-z]\))\s+(.+)$')

def normalize_text_length(text: str) -> int:
    """Loại bỏ khoảng trắng thừa và ngắt dòng liên tiếp để đo độ dài thực tế chống nhiễu OCR/PDF."""
    return len(re.sub(r'\s+', ' ', text).strip())

def compute_normalized_match_ratio(raw_text: str, matched_spans_text: List[str]) -> float:
    """Tính Character Coverage Ratio sau khi đã chuẩn hóa khoảng trắng."""
    total_effective_chars = normalize_text_length(raw_text)
    if total_effective_chars == 0:
        return 0.0
    matched_effective_chars = sum(normalize_text_length(span) for span in matched_spans_text)
    return min(1.0, matched_effective_chars / total_effective_chars)

def document_router(raw_text: str) -> str:
    """Quyết định dùng thuật toán nào để cắt hợp đồng."""
    matches = list(CLAUSE_PATTERN.finditer(raw_text))
    matched_texts = [raw_text[m.start():m.end()] for m in matches] # Giả lập span text
    
    match_ratio = compute_normalized_match_ratio(raw_text, matched_texts)
    
    if match_ratio >= 0.40:
        return "PIPELINE_A_REGEX"
    else:
        return "PIPELINE_B_LLM_CHUNK"