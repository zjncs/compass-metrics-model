"""Regression tests for signature file matching in signed_releases.

The release-checker producer (openchecker) collects signature files as
plain asset filenames whose lowercase name ends with one of
".minisig", ".asc", ".sig", ".sign", ".sigstore", ".intoto.jsonl".
The signed_releases consumer however matched the suffixes
".asc (pgp)" and "*.sig" as substrings - neither can ever occur in a
filename - so PGP .asc signatures and plain .sig signatures were never
counted as signed, while substring matching also let non-signature
files containing ".sign" (e.g. "banner.signoff.png") pass as signatures.

These tests patch the OpenSearch access, so no instance or network
access is required.
"""
from compass_metrics.opencheck_metrics import signed_releases


def openchecker_doc(releases):
    return {
        "_source": {
            "command_result": {
                "signed-release-checker": {
                    "signed_files": releases
                }
            }
        }
    }


def run_signed_releases(monkeypatch, releases):
    doc = openchecker_doc(releases)
    monkeypatch.setattr("compass_metrics.opencheck_metrics.get_openchecker_data",
                        lambda client, index, repo, command: doc)
    return signed_releases(None, "openchecker", ["https://github.com/org/repo"])


def test_asc_pgp_signature_is_counted(monkeypatch):
    result = run_signed_releases(monkeypatch, [
        {"release_name": "v1.0.0", "signature_files": ["release.tar.gz.asc"]},
    ])
    assert result["signed_releases"] == 10
    assert result["signed_releases_detail"]["signed_release_list"] == ["v1.0.0"]


def test_plain_sig_signature_is_counted(monkeypatch):
    result = run_signed_releases(monkeypatch, [
        {"release_name": "v1.0.0", "signature_files": ["checksums.sig"]},
    ])
    assert result["signed_releases"] == 10


def test_mixed_case_signature_is_counted(monkeypatch):
    result = run_signed_releases(monkeypatch, [
        {"release_name": "v1.0.0", "signature_files": ["ARTIFACT.TAR.GZ.ASC"]},
    ])
    assert result["signed_releases"] == 10


def test_minisig_signature_still_counted(monkeypatch):
    result = run_signed_releases(monkeypatch, [
        {"release_name": "v1.0.0", "signature_files": ["release.tar.xz.minisig"]},
    ])
    assert result["signed_releases"] == 10


def test_file_containing_sign_text_is_not_a_signature(monkeypatch):
    # "banner.signoff.png" merely contains the substring ".sign"; it must
    # not be treated as a signature file.
    result = run_signed_releases(monkeypatch, [
        {"release_name": "v1.0.0", "signature_files": ["banner.signoff.png"]},
    ])
    assert result["signed_releases"] == 0
    assert result["signed_releases_detail"]["signed_release_list"] == []


def test_half_signed_releases_score(monkeypatch):
    result = run_signed_releases(monkeypatch, [
        {"release_name": "v1.0.0", "signature_files": ["release.tar.gz.asc"]},
        {"release_name": "v2.0.0", "signature_files": []},
    ])
    assert result["signed_releases"] == 5


def test_no_release_data_returns_none(monkeypatch):
    monkeypatch.setattr("compass_metrics.opencheck_metrics.get_openchecker_data",
                        lambda client, index, repo, command: None)
    result = signed_releases(None, "openchecker", ["https://github.com/org/repo"])
    assert result["signed_releases"] is None
