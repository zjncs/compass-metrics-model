"""Regression tests for the no-data guard of the issue ratio metrics.

issue_unresponsive_ratio, issue_completion_ratio and
issue_completion_ratio_year guarded the NUMERATOR ('count > 0'), so a
window with issues but zero closed/unresponsive issues returned None
("no data") instead of the meaningful ratio 0.0. The codebase idiom
guards the DENOMINATOR (see pr_issue_linked_ratio in pr_metrics.py and
commit_pr_linked_ratio in git_metrics.py): a ratio is undefined only
when the total is zero, and zero-over-N is a valid 0.0.

These tests patch the count helpers, so no OpenSearch instance or
network access is required.
"""
import datetime

import compass_metrics.issue_metrics as im

DATE = datetime.date(2026, 9, 6)
REPOS = ["https://github.com/oss-compass/compass-metrics-model"]


def patch_close_counts(monkeypatch, closed, total):
    monkeypatch.setattr(
        im, "create_close_issue_count",
        lambda client, index, date, repos, from_date=None: {"create_close_issue_count": closed})
    monkeypatch.setattr(
        im, "issue_count",
        lambda client, index, date, repos, from_date=None: {"issue_count": total})


def test_completion_ratio_zero_when_issues_exist_but_none_closed(monkeypatch):
    patch_close_counts(monkeypatch, 0, 10)
    assert im.issue_completion_ratio(
        None, "issue", DATE, REPOS)["issue_completion_ratio"] == 0.0


def test_completion_ratio_year_zero_when_issues_exist_but_none_closed(monkeypatch):
    patch_close_counts(monkeypatch, 0, 10)
    assert im.issue_completion_ratio_year(
        None, "issue", DATE, REPOS)["issue_completion_ratio_year"] == 0.0


def test_unresponsive_ratio_zero_when_all_issues_answered(monkeypatch):
    monkeypatch.setattr(
        im, "issue_unresponsive_count",
        lambda client, index, date, repos, from_date=None: {"issue_unresponsive_count": 0})
    monkeypatch.setattr(
        im, "issue_count",
        lambda client, index, date, repos, from_date=None: {"issue_count": 10})
    assert im.issue_unresponsive_ratio(
        None, "issue", DATE, REPOS)["issue_unresponsive_ratio"] == 0.0


def test_completion_ratios_value_unchanged(monkeypatch):
    patch_close_counts(monkeypatch, 4, 10)
    assert im.issue_completion_ratio(
        None, "issue", DATE, REPOS)["issue_completion_ratio"] == 0.4
    assert im.issue_completion_ratio_year(
        None, "issue", DATE, REPOS)["issue_completion_ratio_year"] == 0.4


def test_completion_ratio_none_without_issues(monkeypatch):
    patch_close_counts(monkeypatch, 0, 0)
    assert im.issue_completion_ratio(
        None, "issue", DATE, REPOS)["issue_completion_ratio"] is None
    assert im.issue_completion_ratio_year(
        None, "issue", DATE, REPOS)["issue_completion_ratio_year"] is None
