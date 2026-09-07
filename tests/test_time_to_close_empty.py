"""Regression tests for time_to_close with documents lacking the state field.

time_to_close collects per-issue durations only from documents whose _source
contains the 'state' field. When the fetched page is non-empty but every
document is missing 'state' (or has no usable timestamp), the collection
stays empty and the function used to divide sum([]) by len([]), raising
ZeroDivisionError. The sibling metric bug_issue_open_time guards this case
and returns None; time_to_close must do the same.

These tests patch the OpenSearch access so no instance or network access is
required.
"""
import datetime

import pytest

from compass_metrics.issue_metrics import time_to_close

DATE = datetime.date(2026, 9, 6)
REPOS = ["https://github.com/oss-compass/compass-metrics-model"]


def closed_issue(created_at, closed_at, state="closed"):
    return {"_source": {"created_at": created_at, "closed_at": closed_at, "state": state}}


def test_time_to_close_returns_none_when_no_issue_has_state(monkeypatch):
    # Non-empty page, but no document carries the 'state' field.
    items = [{"_source": {"created_at": "2026-06-01", "closed_at": "2026-06-11"}}]
    monkeypatch.setattr("compass_metrics.issue_metrics.get_all_index_data",
                        lambda client, index, body: items)
    result = time_to_close(None, "issue", DATE, REPOS)
    assert result == {"time_to_close_avg": None, "time_to_close_mid": None}


def test_time_to_close_averages_closed_and_open_issues(monkeypatch):
    # 10 days for the closed issue, 92 days (up to DATE) for the open one.
    items = [
        closed_issue("2026-06-01", "2026-06-11"),
        closed_issue("2026-06-06", None, state="open"),
    ]
    monkeypatch.setattr("compass_metrics.issue_metrics.get_all_index_data",
                        lambda client, index, body: items)
    result = time_to_close(None, "issue", DATE, REPOS)
    assert result["time_to_close_avg"] == pytest.approx(51.0)
    assert result["time_to_close_mid"] == pytest.approx(51.0)


def test_time_to_close_returns_none_when_page_is_empty(monkeypatch):
    monkeypatch.setattr("compass_metrics.issue_metrics.get_all_index_data",
                        lambda client, index, body: [])
    result = time_to_close(None, "issue", DATE, REPOS)
    assert result == {"time_to_close_avg": None, "time_to_close_mid": None}
