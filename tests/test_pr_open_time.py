"""Regression tests for the pr_open_time metric.

pr_open_time is computed from raw pull request documents fetched from the
search backend. These tests patch ``get_all_index_data`` so no Elasticsearch
instance is required, and check that every PR contributes exactly one
observation of the expected duration.
"""
import datetime

import pytest

import compass_metrics.pr_metrics as pr_metrics

MERGED_PR = {
    "state": "merged",
    "created_at": "2026-01-01T00:00:00Z",
    "merged_at": "2026-02-01T00:00:00Z",
    "closed_at": "2026-02-01T00:00:00Z",
    "updated_at": "2026-02-01T00:00:00Z",
}
OPEN_PR = {
    "state": "open",
    "created_at": "2026-07-01T00:00:00Z",
    "merged_at": None,
    "closed_at": None,
    "updated_at": "2026-08-01T00:00:00Z",
}
CLOSED_PR = {
    "state": "closed",
    "created_at": "2026-01-01T00:00:00Z",
    "merged_at": None,
    "closed_at": "2026-03-01T00:00:00Z",
    "updated_at": "2026-03-01T00:00:00Z",
}

DATE = datetime.datetime(2026, 9, 5)
# merged PR: 2026-01-01 -> 2026-02-01 = 31 days
# closed PR: 2026-01-01 -> 2026-03-01 = 59 days
# open PR:   2026-07-01 -> analysis date 2026-09-05 = 66 days


def _item(source):
    return {"_source": source}


def test_merged_and_open_prs_counted_once_each(monkeypatch):
    items = [_item(dict(MERGED_PR)), _item(dict(OPEN_PR))]
    monkeypatch.setattr(pr_metrics, "get_all_index_data", lambda *args, **kwargs: items)

    result = pr_metrics.pr_open_time(None, "pr_index", DATE, ["https://github.com/o/r"])

    assert result["pr_open_time_avg"] == pytest.approx((31 + 66) / 2)
    assert result["pr_open_time_mid"] == pytest.approx((31 + 66) / 2)


def test_closed_pr_duration_uses_closed_at(monkeypatch):
    items = [_item(dict(CLOSED_PR))]
    monkeypatch.setattr(pr_metrics, "get_all_index_data", lambda *args, **kwargs: items)

    result = pr_metrics.pr_open_time(None, "pr_index", DATE, ["https://github.com/o/r"])

    assert result["pr_open_time_avg"] == pytest.approx(59)
    assert result["pr_open_time_mid"] == pytest.approx(59)


def test_open_pr_without_closed_at_field(monkeypatch):
    source = {key: value for key, value in OPEN_PR.items() if key != "closed_at"}
    monkeypatch.setattr(pr_metrics, "get_all_index_data", lambda *args, **kwargs: [_item(source)])

    result = pr_metrics.pr_open_time(None, "pr_index", DATE, ["https://github.com/o/r"])

    assert result["pr_open_time_avg"] == pytest.approx(66)


def test_mixed_states_produce_one_observation_per_pr(monkeypatch):
    items = [_item(dict(MERGED_PR)), _item(dict(CLOSED_PR)), _item(dict(OPEN_PR))]
    monkeypatch.setattr(pr_metrics, "get_all_index_data", lambda *args, **kwargs: items)

    result = pr_metrics.pr_open_time(None, "pr_index", DATE, ["https://github.com/o/r"])

    assert result["pr_open_time_avg"] == pytest.approx((31 + 59 + 66) / 3)
    assert result["pr_open_time_mid"] == pytest.approx(59)
