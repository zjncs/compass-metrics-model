"""Regression tests for the weekly activity counting in contributor_detail_list.

The enriched index holds one document per (contributor, repo, week), and
contributor_detail_list records the number of weekly documents per contributor
in contribution_weeks. get_regular_contributor promotes contributors who were
active in at least 3/4 of the weeks to "regular" even when they are outside
the cumulative 80% contribution group.

These tests patch the Elasticsearch access so no instance or network access
is required.
"""
import datetime

import pytest

import compass_metrics.contributor_metrics as contributor_metrics_v1
import compass_metrics_v2.contributor_metrics_v2 as contributor_metrics_v2

FROM_DATE = datetime.date(2026, 1, 5)   # a Monday
TO_DATE = datetime.date(2026, 4, 6)     # 14 Mondays later


def weekly_doc(contributor, contribution, repo="https://github.com/o/r"):
    return {
        "contributor": contributor,
        "contribution": contribution,
        "contribution_without_observe": contribution,
        "ecological_type": "individual participant",
        "organization": None,
        "contribution_type_list": [
            {"contribution_type": "code_author", "contribution": contribution}
        ],
        "is_bot": False,
        "repo_name": repo,
    }


def fake_docs():
    # "steady" is active in 11 of the 14 weeks with 1 contribution each;
    # "bursty" has a single weekly doc with 100 contributions.
    steady = [weekly_doc("steady", 1) for _ in range(11)]
    bursty = [weekly_doc("bursty", 100)]
    return [{"_source": doc} for doc in steady + bursty]


@pytest.mark.parametrize("module", [contributor_metrics_v1, contributor_metrics_v2])
def test_contribution_weeks_counts_weekly_docs(module, monkeypatch):
    monkeypatch.setattr(
        module, "get_all_index_data",
        lambda *args, **kwargs: fake_docs())

    detail = module.contributor_detail_list(
        None, "contributors_enriched_index", TO_DATE, ["https://github.com/o/r"],
        from_date=FROM_DATE)

    steady = next(item for item in detail["contributor_detail_list"]
                  if item["contributor"] == "steady")
    assert steady["contribution_weeks"] == 11


@pytest.mark.parametrize("module", [contributor_metrics_v1, contributor_metrics_v2])
def test_three_quarters_active_contributor_is_regular(module, monkeypatch):
    monkeypatch.setattr(
        module, "get_all_index_data",
        lambda *args, **kwargs: fake_docs())

    detail = module.contributor_detail_list(
        None, "contributors_enriched_index", TO_DATE, ["https://github.com/o/r"],
        from_date=FROM_DATE)

    # "bursty" alone reaches the 50% core threshold; "steady", active in
    # 11 >= 14 * 3/4 weeks, must be classified as regular, not casual.
    assert detail["core_count"] == 1
    assert detail["regular_count"] == 1
    assert detail["casual_count"] == 0

    steady = next(item for item in detail["contributor_detail_list"]
                  if item["contributor"] == "steady")
    assert steady["mileage_type"] == "regular"
