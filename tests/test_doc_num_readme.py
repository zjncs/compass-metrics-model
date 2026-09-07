"""Regression tests for README detection in the doc_number metric.

search_readme_in_folder checked os.path.isfile() against the process
working directory instead of the target folder, so a README inside the
cloned repository was never detected and its document links were never
counted by get_documentation_links_from_repo. Additionally, the
documented ValueError for a failed clone was constructed but never
raised, letting the function continue with a missing repository path
and crash later with FileNotFoundError.

These tests run on temporary directories; no clone or network access is
required.
"""
import pytest

import compass_metrics.document_metric.doc_num as doc_num


def test_search_readme_finds_readme_in_target_folder(tmp_path, monkeypatch):
    repo = tmp_path / "repo-1.0"
    repo.mkdir()
    (repo / "README.md").write_text("# Title\n\nSee https://example.com/docs\n",
                                    encoding="utf-8")
    # The process working directory must not contain any README file,
    # otherwise the isfile() check against the CWD would mask the bug.
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    flag, content = doc_num.search_readme_in_folder(str(repo))
    assert flag is True
    assert content.startswith("# Title")


def test_search_readme_returns_false_without_readme(tmp_path, monkeypatch):
    repo = tmp_path / "repo-1.0"
    repo.mkdir()
    (repo / "main.go").write_text("package main\n", encoding="utf-8")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    flag, content = doc_num.search_readme_in_folder(str(repo))
    assert flag is False
    assert content == ""


def test_get_documentation_links_counts_readme_links(tmp_path, monkeypatch):
    repo = tmp_path / "demo-1.0.0"
    repo.mkdir()
    (repo / "README.md").write_text("# Demo\n\nDocs: https://example.com/docs\n",
                                    encoding="utf-8")
    (repo / "docs.md").write_text("docs\n", encoding="utf-8")
    monkeypatch.setattr(doc_num, "TMP_PATH", str(tmp_path))
    monkeypatch.setattr(doc_num, "JSON_REPOPATH", str(tmp_path))
    # Keep the CWD free of README files so the isfile() check against the
    # CWD cannot mask the bug.
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    result = doc_num.get_documentation_links_from_repo(
        "https://github.com/org/demo", "1.0.0")
    # 2 folder documents (README.md, docs.md) + 1 link from the README.
    assert result["doc_number"] == 3
    assert result["links_document_details"][0]["path"] == "https://example.com/docs"


def test_clone_failure_raises_value_error(tmp_path, monkeypatch):
    monkeypatch.setattr(doc_num, "TMP_PATH", str(tmp_path))
    monkeypatch.setattr(doc_num, "clone_repo", lambda url, version: (False, None))

    with pytest.raises(ValueError, match="Repository clone failed"):
        doc_num.get_documentation_links_from_repo(
            "https://github.com/org/demo", "1.0.0")
