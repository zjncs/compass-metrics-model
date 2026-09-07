"""Regression tests for the weekly divisor of LOC_frequency_year.

LOC_frequency_year sums ``lines_changed`` over the past 3 years (from Jan 1 of
the calendar year 3 years back up to ``date``) and reports the average number
of lines touched per week. The 90-day sibling LOC_frequency divides its sum by
12.85 (90/7 weeks); the 3-year window must instead be divided by 156.43
(3*365/7 weeks), the same fixed-divisor convention used by
commit_frequency_last_year (52.14 = 365/7 for a 1-year window).

These tests patch the Elasticsearch access so no instance or network access
is required.
"""
import datetime

import pytest

import compass_metrics.git_metrics as git_metrics_v1
import compass_metrics_v2.git_metrics_v2 as git_metrics_v2

DATE = datetime.date(2026, 9, 6)
WEEKS_IN_3_YEARS = 3 * 365 / 7  # 156.4285... -> codebase uses 156.43
REPOS = ["https://github.com/oss-compass/compass-metrics-model"]
TOTAL_LINES = 1564.3  # so the true weekly average is 10.0


class FakeSearchClient:
    def __init__(self, value):
        self.value = value
        self.queries = []

    def search(self, index=None, body=None):
        self.queries.append(body)
        return {"aggregations": {"count_of_uuid": {"value": self.value}}}


@pytest.mark.parametrize("module", [git_metrics_v1, git_metrics_v2])
def test_loc_frequency_year_divides_by_weeks_in_3_years(module):
    client = FakeSearchClient(TOTAL_LINES)
    result = module.LOC_frequency_year(client, "git", DATE, REPOS)
    assert result == pytest.approx(TOTAL_LINES / 156.43)


@pytest.mark.parametrize("module", [git_metrics_v1, git_metrics_v2])
def test_loc_frequency_year_queries_a_3_year_window(module):
    client = FakeSearchClient(TOTAL_LINES)
    module.LOC_frequency_year(client, "git", DATE, REPOS)
    date_range = client.queries[0]["query"]["bool"]["filter"][0]["range"][
        "grimoire_creation_date"
    ]
    # The window starts on Jan 1 of the calendar year 3 years back.
    assert date_range["gte"] == "2023-01-01"
    assert date_range["lt"] == "2026-09-06"
