"""Regression tests for the activity_quarterly_contribution metric.

These tests patch the network call (GitHub release lookup) and the
contributor search so no Elasticsearch instance or network access is
required, and check that the four quarterly windows are the natural
calendar quarters: each calendar day is counted in exactly one quarter.
"""
import compass_metrics.activity as activity
import compass_metrics.git_metrics as git_metrics

NON_BOT_CONTRIBUTOR = {
    "is_bot": False,
    "code_author_date_list": ["2025-12-31", "2026-03-31", "2026-04-01"],
}
BOT_CONTRIBUTOR = {
    "is_bot": True,
    "code_author_date_list": ["2026-07-01"],
}


def test_quarter_windows_are_natural_calendar_quarters(monkeypatch):
    monkeypatch.setattr(
        activity, "get_github_versionPublishAt",
        lambda *args, **kwargs: "2026-09-05T00:00:00Z")
    monkeypatch.setattr(
        git_metrics, "get_contributor_list",
        lambda *args, **kwargs: [dict(NON_BOT_CONTRIBUTOR), dict(BOT_CONTRIBUTOR)])

    result = activity.activity_quarterly_contribution(
        None, "contributors_index", ["https://github.com/o/r"], "v1.0")

    # The four windows must be Q3'26, Q2'26, Q1'26, Q4'25 as natural
    # calendar quarters: [Jul 1-Sep 30], [Apr 1-Jun 30], [Jan 1-Mar 31],
    # [Oct 1-Dec 31]. Every commit day belongs to exactly one window.
    assert result["activity_quarterly_contribution"] == [1, 1, 1, 1]
    assert result["activity_quarterly_contribution_bot"] == [1, 0, 0, 0]
    assert result["activity_quarterly_contribution_without_bot"] == [0, 1, 1, 1]
    assert result["activity_quarterly_contribution_info"] == "success"


def test_quarter_windows_align_when_publish_date_is_quarter_start(monkeypatch):
    monkeypatch.setattr(
        activity, "get_github_versionPublishAt",
        lambda *args, **kwargs: "2026-10-01T00:00:00Z")
    quarter_start_day_contributor = {
        "is_bot": False,
        "code_author_date_list": ["2025-12-31", "2026-03-31", "2026-04-01", "2026-10-01"],
    }
    monkeypatch.setattr(
        git_metrics, "get_contributor_list",
        lambda *args, **kwargs: [quarter_start_day_contributor])

    result = activity.activity_quarterly_contribution(
        None, "contributors_index", ["https://github.com/o/r"], "v1.0")

    # Publish date in Q4'26: windows are Q4'26, Q3'26, Q2'26, Q1'26. The
    # publish day itself belongs to Q4'26, Mar 31 to Q1'26, Apr 1 to Q2'26,
    # and Dec 31 2025 falls outside the four windows.
    assert result["activity_quarterly_contribution"] == [1, 0, 1, 1]


def test_returns_failure_info_when_release_not_found(monkeypatch):
    monkeypatch.setattr(
        activity, "get_github_versionPublishAt", lambda *args, **kwargs: None)

    result = activity.activity_quarterly_contribution(
        None, "contributors_index", ["https://github.com/o/r"], "v9.9.9")

    assert result["activity_quarterly_contribution"] == []
    assert "Failed" in result["activity_quarterly_contribution_info"]
