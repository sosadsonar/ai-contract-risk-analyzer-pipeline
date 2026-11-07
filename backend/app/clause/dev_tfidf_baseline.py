"""Fixed 1-nearest-neighbor clause-label baseline trained on D1 Dev only.

The feature map and neighbor count are fixed here; no T1/T2 label, keyword
proposal, validation score, or test-derived tuning enters model fitting.
"""

import unicodedata
from dataclasses import dataclass
from typing import Sequence

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFC", text).casefold()


@dataclass
class DevTfidfBaseline:
    vectorizer: TfidfVectorizer
    reference_vectors: object
    labels: tuple[tuple[str, ...], ...]

    @classmethod
    def fit(cls, texts: Sequence[str], labels: Sequence[Sequence[str]]) -> "DevTfidfBaseline":
        if not texts or len(texts) != len(labels) or any(not row for row in labels):
            raise ValueError("nonempty D1 training text and labels must align")
        vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(3, 5), min_df=1, norm="l2")
        vectors = vectorizer.fit_transform(_normalize(text) for text in texts)
        return cls(vectorizer, vectors, tuple(tuple(row) for row in labels))

    def predict(self, texts: Sequence[str]) -> tuple[tuple[str, ...], ...]:
        if not texts:
            return ()
        queries = self.vectorizer.transform(_normalize(text) for text in texts)
        similarity = linear_kernel(queries, self.reference_vectors)
        return tuple(self.labels[int(row.argmax())] for row in similarity)
