import pytest

from ai_pipeline.evaluation.metrics.bootstrap import (
    bootstrap_classification_intervals,
    bootstrap_cluster_interval,
)


def test_bootstrap_cluster_interval_interpolates_percentiles_deterministically():
    result = bootstrap_cluster_interval(
        {"zero": (0.0,), "one": (1.0,)},
        lambda rows: sum(rows) / len(rows),
        iterations=2,
        random_seed=3,
    )

    assert result.low == pytest.approx(0.025)
    assert result.high == pytest.approx(0.975)
    assert result.confidence_level == 0.95
    assert result.iterations == 2
    assert result.cluster_count == 2
    assert result.valid_replicate_count == 2


def test_bootstrap_cluster_interval_is_reproducible_and_resamples_whole_clusters():
    clusters = {
        "doc-a": (("doc-a", 0), ("doc-a", 1)),
        "doc-b": (("doc-b", 0), ("doc-b", 1)),
        "doc-c": (("doc-c", 0), ("doc-c", 1)),
    }
    observed_samples = []

    def statistic(rows):
        counts = {}
        for cluster_id, _ in rows:
            counts[cluster_id] = counts.get(cluster_id, 0) + 1
        observed_samples.append(tuple(counts.values()))
        assert all(count % 2 == 0 for count in counts.values())
        return len(counts) / len(clusters)

    first = bootstrap_cluster_interval(clusters, statistic, iterations=25, random_seed=17)
    second = bootstrap_cluster_interval(
        clusters,
        lambda rows: len({cluster_id for cluster_id, _ in rows}) / len(clusters),
        iterations=25,
        random_seed=17,
    )

    assert (first.low, first.high) == (second.low, second.high)
    assert len(observed_samples) == 25
    assert first.cluster_count == 3
    assert first.valid_replicate_count == 25


@pytest.mark.parametrize(
    ("iterations", "random_seed"),
    [(0, 0), (True, 0), (2, True), (2, "0")],
)
def test_bootstrap_cluster_interval_rejects_invalid_iteration_or_seed(iterations, random_seed):
    with pytest.raises(ValueError):
        bootstrap_cluster_interval(
            {"a": (1,), "b": (2,)},
            lambda rows: float(sum(rows)),
            iterations=iterations,
            random_seed=random_seed,
        )


def test_bootstrap_cluster_interval_ignores_empty_clusters_and_reports_empty_input():
    result = bootstrap_cluster_interval(
        {"empty": (), "a": (1,), "b": (2,)},
        lambda rows: float(sum(rows)),
        iterations=10,
    )

    assert result.cluster_count == 2
    assert result.valid_replicate_count == 10

    empty = bootstrap_cluster_interval({}, lambda rows: None, iterations=10)
    assert empty.low is None
    assert empty.high is None
    assert empty.cluster_count == 0
    assert empty.valid_replicate_count == 0


def test_bootstrap_cluster_interval_returns_null_bounds_for_one_cluster():
    result = bootstrap_cluster_interval(
        {"only": (1, 2)},
        lambda rows: float(sum(rows)),
        iterations=10,
    )

    assert result.low is None
    assert result.high is None
    assert result.cluster_count == 1
    assert result.valid_replicate_count == 0


def test_bootstrap_classification_intervals_match_independent_cluster_reference():
    clusters = {
        "doc-a": {"A": (2, 1, 1), "B": (0, 1, 2)},
        "doc-b": {"A": (1, 0, 2), "B": (1, 1, 0)},
        "doc-c": {"A": (0, 0, 0), "B": (0, 0, 0), "C": (1, 0, 0)},
    }
    eligible = frozenset({"A", "B"})
    reporting = frozenset({"A", "B", "C"})
    macro, per_class = bootstrap_classification_intervals(
        clusters,
        eligible_macro_labels=eligible,
        reporting_labels=reporting,
        iterations=80,
        random_seed=17,
    )

    def reference(field, label=None):
        def contributes(counts):
            if label is None:
                return any(sum(counts.get(candidate, (0, 0, 0))) > 0 for candidate in eligible)
            tp, fp, fn = counts.get(label, (0, 0, 0))
            return tp + fp > 0 if field == "precision" else tp + fn > 0 if field == "recall" else tp + fp + fn > 0

        selected = {
            document_id: tuple(counts.items())
            for document_id, counts in clusters.items()
            if contributes(counts)
        }

        def statistic(rows):
            totals = {candidate: [0, 0, 0] for candidate in reporting}
            for candidate, triple in rows:
                for index, value in enumerate(triple):
                    totals[candidate][index] += value
            if label is None:
                if not any(sum(totals[candidate]) > 0 for candidate in eligible):
                    return None
                values = []
                for candidate in eligible:
                    tp, fp, fn = totals[candidate]
                    denominator = 2 * tp + fp + fn
                    values.append(2 * tp / denominator if denominator else 0.0)
                return sum(values) / len(values)
            tp, fp, fn = totals[label]
            denominator = tp + fp if field == "precision" else tp + fn if field == "recall" else 2 * tp + fp + fn
            if denominator == 0:
                return None
            return tp / denominator if field != "f1" else 2 * tp / denominator

        return bootstrap_cluster_interval(selected, statistic, iterations=80, random_seed=17)

    assert macro == reference("f1")
    for label in reporting:
        for field in ("precision", "recall", "f1"):
            assert per_class[label][field] == reference(field, label)
