"""Regression tests for the version time range in organizational_contribution.

get_github_versions/get_gitee_versions locate the requested version in the
chronologically sorted release list and use the previous release's date as
the range start. When the requested version is the OLDEST one (index 0),
versions[i-1] wraps around to versions[-1], the NEWEST release, producing an
inverted range (start > end). The downstream OpenSearch query in
organizational_contribution then matches nothing and org_contribution is
always 0 for the earliest release. The start time must stay at its
2020-01-01 default when there is no earlier release.

These tests patch HTTP access and the JSON cache directory, so no network
or API token is required.
"""
import sys

# The package __init__ rebinds the name `organizational_contribution` to the
# function, so import the module and fetch it from sys.modules.
import compass_metrics.document_metric.organizational_contribution  # noqa: F401

oc = sys.modules["compass_metrics.document_metric.organizational_contribution"]


class FakeResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json = json_data if json_data is not None else []
        self.links = {}

    def json(self):
        return self._json


def releases_response():
    return FakeResponse(json_data=[
        {"tag_name": "v1.0.0", "published_at": "2021-01-10T00:00:00Z"},
        {"tag_name": "v2.0.0", "published_at": "2022-02-20T00:00:00Z"},
        {"tag_name": "v3.0.0", "published_at": "2023-03-30T00:00:00Z"},
    ])


def test_oldest_release_range_keeps_default_start(tmp_path, monkeypatch):
    monkeypatch.setattr(oc, "JSON_REPOPATH", str(tmp_path))
    monkeypatch.setattr(oc.requests, "get", lambda url, headers=None: releases_response())
    start, end = oc.get_github_versions("https://github.com/org/demo", "v1.0.0")
    assert end == "2021-01-10T00:00:00Z"
    assert start == "2020-01-01T00:00:00Z"


def test_middle_release_range_spans_previous_release(tmp_path, monkeypatch):
    monkeypatch.setattr(oc, "JSON_REPOPATH", str(tmp_path))
    monkeypatch.setattr(oc.requests, "get", lambda url, headers=None: releases_response())
    start, end = oc.get_github_versions("https://github.com/org/demo", "v2.0.0")
    assert (start, end) == ("2021-01-10T00:00:00Z", "2022-02-20T00:00:00Z")


def test_gitee_oldest_release_range_keeps_default_start(tmp_path, monkeypatch):
    monkeypatch.setattr(oc, "JSON_REPOPATH", str(tmp_path))
    monkeypatch.setattr(oc.requests, "get", lambda url, headers=None: releases_response())
    start, end = oc.get_gitee_versions("https://gitee.com/org/demo", "v1.0.0")
    assert end == "2021-01-10T00:00:00Z"
    assert start == "2020-01-01T00:00:00Z"


def test_oldest_tag_range_keeps_default_start(tmp_path, monkeypatch):
    # Empty /releases response forces the /tags fallback path.
    def fake_get(url, headers=None):
        if url.endswith("/tags"):
            return FakeResponse(json_data=[
                {"name": "v1.0.0",
                 "commit": {"url": "https://api.github.com/repos/org/demo/commits/aaa"}},
                {"name": "v2.0.0",
                 "commit": {"url": "https://api.github.com/repos/org/demo/commits/bbb"}},
            ])
        if "/commits/" in url:
            date = "2021-01-10T00:00:00Z" if url.endswith("aaa") else "2022-02-20T00:00:00Z"
            return FakeResponse(json_data={"commit": {"committer": {"date": date}}})
        return FakeResponse(json_data=[])

    monkeypatch.setattr(oc, "JSON_REPOPATH", str(tmp_path))
    monkeypatch.setattr(oc.requests, "get", fake_get)
    start, end = oc.get_github_versions("https://github.com/org/demo", "v1.0.0")
    assert end == "2021-01-10T00:00:00Z"
    assert start == "2020-01-01T00:00:00Z"
