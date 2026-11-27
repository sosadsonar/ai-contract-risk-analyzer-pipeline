"""Fixed 1-nearest-neighbor clause-label baseline trained on D1 Dev only.

The feature map and neighbor count are fixed here; no T1/T2 label, keyword
proposal, validation score, or test-derived tuning enters model fitting.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Sequence

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from app.clause.taxonomy import MAX_LABELS_PER_CLAUSE, OTHER_LABEL, validate_labels


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFC", text).casefold()


_SECURITY_WORKING_CONDITIONS = re.compile(
    r"ký\s+quỹ|đặt\s+cọc|tiền\s+bảo\s+đảm|giữ\s+bản\s+chính"
)


def add_source_working_conditions(
    texts: Sequence[str], predictions: Sequence[Sequence[str]]
) -> tuple[tuple[str, ...], ...]:
    """Add a Dev-only source signal without changing the frozen TF-IDF model.

    Risk taxonomy v0.1 associates deposit and original-document retention
    with the WORKING_CONDITIONS clause label. Keep the model's leading label
    and add at most one source-derived second label on matching clauses.
    OTHER and predictions at the taxonomy limit stay as returned by the model.
    This can miss the secondary signal when the model predicts OTHER.
    """
    if len(texts) != len(predictions):
        raise ValueError("Dev clause texts and predictions must align")
    result = []
    for text, labels in zip(texts, predictions):
        validated = tuple(validate_labels(list(labels)))
        if (OTHER_LABEL not in validated and len(validated) < MAX_LABELS_PER_CLAUSE
                and "WORKING_CONDITIONS" not in validated and _SECURITY_WORKING_CONDITIONS.search(_normalize(text))):
            validated = (validated[0], "WORKING_CONDITIONS")
        result.append(validated)
    return tuple(result)


@dataclass
class DevTfidfBaseline:
    vectorizer: TfidfVectorizer
    reference_vectors: object
    labels: tuple[tuple[str, ...], ...]

    @classmethod
    def fit(cls, texts: Sequence[str], labels: Sequence[Sequence[str]]) -> "DevTfidfBaseline":
        if not texts or len(texts) != len(labels):
            raise ValueError("nonempty D1 training text and labels must align")
        validated_labels = tuple(tuple(validate_labels(list(row))) for row in labels)
        vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(3, 5), min_df=1, norm="l2")
        vectors = vectorizer.fit_transform(_normalize(text) for text in texts)
        return cls(vectorizer, vectors, validated_labels)

    def predict(self, texts: Sequence[str]) -> tuple[tuple[str, ...], ...]:
        if not texts:
            return ()
        queries = self.vectorizer.transform(_normalize(text) for text in texts)
        similarity = linear_kernel(queries, self.reference_vectors)
        return tuple(self.labels[int(row.argmax())] for row in similarity)
