from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any


METADATA_URL = "https://archive.org/metadata/{identifier}"
DOWNLOAD_URL = "https://archive.org/download/{identifier}/{filename}"


class ArchiveError(RuntimeError):
    """Raised when a public archive derivative cannot be fetched or validated."""


@dataclass(frozen=True)
class CachedVolume:
    identifier: str
    metadata_path: Path
    djvu_xml_path: Path


class InternetArchiveClient:
    """Small, read-only client with conservative caching and retry behavior."""

    def __init__(
        self,
        cache_root: Path,
        *,
        user_agent: str = "public-record-versioned/0.1 (+https://github.com/siiddhantt)",
        timeout_seconds: float = 30.0,
        minimum_interval_seconds: float = 0.4,
        maximum_file_bytes: int = 25_000_000,
    ) -> None:
        self.cache_root = cache_root
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        self.minimum_interval_seconds = minimum_interval_seconds
        self.maximum_file_bytes = maximum_file_bytes
        self._last_request_at = 0.0
        self._metadata_gateway_unavailable = False

    def fetch_volume(
        self,
        identifier: str,
        *,
        storage_base_url: str | None = None,
    ) -> CachedVolume:
        volume_dir = self.cache_root / identifier
        volume_dir.mkdir(parents=True, exist_ok=True)

        metadata_path = volume_dir / "metadata.json"
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        else:
            if self._metadata_gateway_unavailable and storage_base_url is not None:
                metadata = self._get_storage_metadata(
                    identifier,
                    storage_base_url,
                    primary_error=ArchiveError(
                        "Metadata gateway skipped after an earlier failure in this run"
                    ),
                )
            else:
                try:
                    metadata = self._get_json(METADATA_URL.format(identifier=identifier))
                except ArchiveError as primary_error:
                    if storage_base_url is None:
                        raise
                    self._metadata_gateway_unavailable = True
                    metadata = self._get_storage_metadata(
                        identifier,
                        storage_base_url,
                        primary_error=primary_error,
                    )
            self._write_json_atomic(metadata_path, metadata)

        item_identifier = metadata.get("metadata", {}).get("identifier")
        if item_identifier != identifier:
            raise ArchiveError(
                f"Metadata identifier mismatch: expected {identifier!r}, got {item_identifier!r}"
            )

        derivative = find_derivative(metadata, "_djvu.xml")
        filename = derivative["name"]
        destination = volume_dir / filename
        expected_size = _optional_int(derivative.get("size"))
        expected_md5 = derivative.get("md5")

        if destination.exists() and self._is_valid_cached_file(
            destination, expected_size=expected_size, expected_md5=expected_md5
        ):
            return CachedVolume(identifier, metadata_path, destination)

        url = derivative.get("download_url") or DOWNLOAD_URL.format(
            identifier=identifier,
            filename=urllib.parse.quote(filename, safe=""),
        )
        self._download_atomic(
            url,
            destination,
            expected_size=expected_size,
            expected_md5=expected_md5,
        )
        return CachedVolume(identifier, metadata_path, destination)

    def _get_storage_metadata(
        self,
        identifier: str,
        storage_base_url: str,
        *,
        primary_error: ArchiveError,
    ) -> dict[str, Any]:
        base_url = validate_storage_base_url(storage_base_url, identifier)
        files_url = f"{base_url}/{identifier}_files.xml"
        meta_url = f"{base_url}/{identifier}_meta.xml"
        files_payload = self._request_bytes(files_url, maximum_bytes=5_000_000)
        meta_payload = self._request_bytes(meta_url, maximum_bytes=1_000_000)
        return storage_metadata_from_xml(
            identifier,
            files_payload=files_payload,
            meta_payload=meta_payload,
            storage_base_url=base_url,
            fallback_reason=str(primary_error),
        )

    def require_cached_volume(self, identifier: str) -> CachedVolume:
        volume_dir = self.cache_root / identifier
        metadata_path = volume_dir / "metadata.json"
        if not metadata_path.exists():
            raise ArchiveError(f"Missing cached metadata for {identifier}")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        derivative = find_derivative(metadata, "_djvu.xml")
        djvu_xml_path = volume_dir / derivative["name"]
        if not djvu_xml_path.exists():
            raise ArchiveError(f"Missing cached DjVu XML for {identifier}")
        if not self._is_valid_cached_file(
            djvu_xml_path,
            expected_size=_optional_int(derivative.get("size")),
            expected_md5=derivative.get("md5"),
        ):
            raise ArchiveError(f"Cached DjVu XML failed validation for {identifier}")
        return CachedVolume(identifier, metadata_path, djvu_xml_path)

    def _get_json(self, url: str) -> dict[str, Any]:
        payload = self._request_bytes(url, maximum_bytes=5_000_000)
        try:
            value = json.loads(payload)
        except json.JSONDecodeError as error:
            raise ArchiveError(f"Invalid JSON returned by {url}") from error
        if not isinstance(value, dict):
            raise ArchiveError(f"Expected a JSON object from {url}")
        return value

    def _download_atomic(
        self,
        url: str,
        destination: Path,
        *,
        expected_size: int | None,
        expected_md5: str | None,
    ) -> None:
        maximum = self.maximum_file_bytes
        if expected_size is not None and expected_size > maximum:
            raise ArchiveError(
                f"Refusing {expected_size} byte derivative; configured maximum is {maximum}"
            )
        payload = self._request_bytes(url, maximum_bytes=maximum)
        if expected_size is not None and len(payload) != expected_size:
            raise ArchiveError(
                f"Size mismatch for {destination.name}: expected {expected_size}, got {len(payload)}"
            )
        if expected_md5 and _md5_bytes(payload) != expected_md5.lower():
            raise ArchiveError(f"Checksum mismatch for {destination.name}")
        _write_bytes_atomic(destination, payload)

    def _request_bytes(self, url: str, *, maximum_bytes: int) -> bytes:
        transient_statuses = {408, 425, 429, 500, 502, 503, 504}
        last_error: Exception | None = None
        for attempt in range(3):
            self._respect_interval()
            request = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    content_length = _optional_int(response.headers.get("Content-Length"))
                    if content_length is not None and content_length > maximum_bytes:
                        raise ArchiveError(
                            f"Refusing {content_length} byte response from {url}; "
                            f"maximum is {maximum_bytes}"
                        )
                    payload = response.read(maximum_bytes + 1)
                    if len(payload) > maximum_bytes:
                        raise ArchiveError(f"Response from {url} exceeded {maximum_bytes} bytes")
                    return payload
            except urllib.error.HTTPError as error:
                last_error = error
                if error.code not in transient_statuses:
                    raise ArchiveError(f"HTTP {error.code} while reading {url}") from error
            except urllib.error.URLError as error:
                last_error = error
            if attempt < 2:
                time.sleep(2**attempt)
        raise ArchiveError(f"Unable to read {url} after three attempts") from last_error

    def _respect_interval(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.minimum_interval_seconds:
            time.sleep(self.minimum_interval_seconds - elapsed)
        self._last_request_at = time.monotonic()

    @staticmethod
    def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(value, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
        _write_bytes_atomic(path, payload)

    @staticmethod
    def _is_valid_cached_file(
        path: Path, *, expected_size: int | None, expected_md5: str | None
    ) -> bool:
        if expected_size is not None and path.stat().st_size != expected_size:
            return False
        if expected_md5 and _md5_path(path) != expected_md5.lower():
            return False
        return path.stat().st_size > 0


def find_derivative(metadata: dict[str, Any], suffix: str) -> dict[str, Any]:
    matches = [
        item
        for item in metadata.get("files", [])
        if isinstance(item, dict)
        and isinstance(item.get("name"), str)
        and item["name"].endswith(suffix)
    ]
    if len(matches) != 1:
        raise ArchiveError(
            f"Expected exactly one {suffix!r} derivative, found {len(matches)}"
        )
    return matches[0]


def validate_storage_base_url(value: str, identifier: str) -> str:
    parsed = urllib.parse.urlsplit(value.rstrip("/"))
    expected_path = f"/items/{identifier}"
    if (
        parsed.scheme != "https"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
        or not parsed.hostname
        or not parsed.hostname.endswith(".us.archive.org")
        or not parsed.path.endswith(expected_path)
        or parsed.query
        or parsed.fragment
    ):
        raise ArchiveError(f"Invalid Internet Archive storage URL for {identifier}")
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", "")
    )


def storage_metadata_from_xml(
    identifier: str,
    *,
    files_payload: bytes,
    meta_payload: bytes,
    storage_base_url: str,
    fallback_reason: str,
) -> dict[str, Any]:
    """Convert official storage-node manifests into the public API shape we use."""

    try:
        files_root = ET.fromstring(files_payload)
        meta_root = ET.fromstring(meta_payload)
    except ET.ParseError as error:
        raise ArchiveError("Invalid XML returned by Internet Archive storage") from error

    item_identifier = (meta_root.findtext("identifier") or "").strip()
    if item_identifier != identifier:
        raise ArchiveError(
            f"Storage metadata identifier mismatch: expected {identifier!r}, "
            f"got {item_identifier!r}"
        )

    files: list[dict[str, str]] = []
    for element in files_root.findall("file"):
        name = element.get("name")
        if not name:
            continue
        file_record = {"name": name}
        for child in element:
            if child.text:
                file_record[child.tag] = child.text.strip()
        if name.endswith("_djvu.xml"):
            file_record["download_url"] = (
                f"{storage_base_url}/{urllib.parse.quote(name, safe='')}"
            )
        files.append(file_record)

    if not any(item["name"].endswith("_djvu.xml") for item in files):
        raise ArchiveError("Storage inventory does not contain a DjVu XML derivative")

    metadata = {
        key: value.strip()
        for key in ("identifier", "date", "title", "volume", "language")
        if (value := meta_root.findtext(key))
    }
    return {
        "metadata": metadata,
        "files": files,
        "_fetch": {
            "mode": "official_storage_fallback",
            "storage_base_url": storage_base_url,
            "fallback_reason": fallback_reason,
        },
    }


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ArchiveError(f"Invalid integer metadata value: {value!r}") from error


def _write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_bytes(payload)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _md5_bytes(payload: bytes) -> str:
    try:
        digest = hashlib.md5(usedforsecurity=False)
    except TypeError:
        digest = hashlib.md5()
    digest.update(payload)
    return digest.hexdigest()


def _md5_path(path: Path) -> str:
    try:
        digest = hashlib.md5(usedforsecurity=False)
    except TypeError:
        digest = hashlib.md5()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
