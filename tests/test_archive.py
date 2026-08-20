from __future__ import annotations

import unittest

from public_record_versioned.archive import (
    ArchiveError,
    find_derivative,
    storage_metadata_from_xml,
    validate_storage_base_url,
)


class FindDerivativeTests(unittest.TestCase):
    def test_finds_the_single_requested_derivative(self) -> None:
        metadata = {
            "files": [
                {"name": "sample_djvu.txt"},
                {"name": "sample_djvu.xml", "size": "42"},
            ]
        }
        self.assertEqual(find_derivative(metadata, "_djvu.xml")["size"], "42")

    def test_rejects_ambiguous_derivatives(self) -> None:
        metadata = {"files": [{"name": "a_djvu.xml"}, {"name": "b_djvu.xml"}]}
        with self.assertRaises(ArchiveError):
            find_derivative(metadata, "_djvu.xml")


class StorageFallbackTests(unittest.TestCase):
    def test_converts_official_manifests_and_preserves_validation_fields(self) -> None:
        result = storage_metadata_from_xml(
            "sample",
            files_payload=b"""<files>
                <file name="sample_djvu.xml" source="derivative">
                    <size>42</size><md5>abc123</md5>
                </file>
            </files>""",
            meta_payload=b"""<metadata>
                <identifier>sample</identifier><date>1996</date>
            </metadata>""",
            storage_base_url="https://ia600001.us.archive.org/1/items/sample",
            fallback_reason="gateway unavailable",
        )

        derivative = find_derivative(result, "_djvu.xml")
        self.assertEqual(result["metadata"]["identifier"], "sample")
        self.assertEqual(derivative["size"], "42")
        self.assertEqual(derivative["md5"], "abc123")
        self.assertEqual(
            derivative["download_url"],
            "https://ia600001.us.archive.org/1/items/sample/sample_djvu.xml",
        )

    def test_rejects_non_archive_storage_hosts(self) -> None:
        with self.assertRaises(ArchiveError):
            validate_storage_base_url("https://example.com/items/sample", "sample")

    def test_rejects_identifier_mismatch(self) -> None:
        with self.assertRaises(ArchiveError):
            storage_metadata_from_xml(
                "expected",
                files_payload=b'<files><file name="expected_djvu.xml" /></files>',
                meta_payload=b"<metadata><identifier>other</identifier></metadata>",
                storage_base_url=(
                    "https://ia600001.us.archive.org/1/items/expected"
                ),
                fallback_reason="gateway unavailable",
            )


if __name__ == "__main__":
    unittest.main()
