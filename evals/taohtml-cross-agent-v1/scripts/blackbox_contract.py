#!/usr/bin/env python3
"""Shared deterministic primitives for the cross-Agent black-box contract."""

from __future__ import annotations

import copy
import hashlib
import hmac
import json
import re
import shutil
import struct
import zipfile
import zlib
from datetime import datetime, timezone
from html import escape as xml_escape
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


EVAL_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = EVAL_ROOT.parents[1]
PARTICIPANT_ROOT = EVAL_ROOT / "participant"
SCENARIO_ROOT = PARTICIPANT_ROOT / "scenarios"
CONTROLLER_ROOT = EVAL_ROOT / "controller"
ANSWER_ROOT = CONTROLLER_ROOT / "scenarios"
RUN_CONTRACT_VERSION = "taohtml-cross-agent-run-1"
RECEIPT_VERSION = "taohtml-cross-agent-receipt-2"
SUBMISSION_CONTRACT_VERSION = "taohtml-cross-agent-submission-1"
RESULT_CONTRACT_VERSION = "taohtml-cross-agent-result-2"
SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$")
NONCE = re.compile(r"^[a-f0-9]{32,128}$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
PACKAGE_FORBIDDEN_COMPONENTS = {
    "answer",
    "answers",
    "answer-key",
    "answer_key",
    "controller",
    "expected",
    "rubric",
    "score",
    "scoring",
}
INTERNAL_FIELD_MARKERS = {
    "primary_profile_id",
    "workflow_profile",
    "report_ir_version",
    "schema_valid",
    "references_valid",
    "semantics_valid",
    "compiler_ready",
    "bindings_valid",
    "continuation_ready",
    "delivery_ready",
    "qa_execution_claim",
}
REQUIRED_OUTPUTS = (
    "design-brief.md",
    "report-ir.json",
    "build/index.html",
    "build/build-manifest.json",
    "build/source-map.json",
    "build/report.ir.normalized.json",
    "project-handoff.json",
    "handoff.md",
    "submission.json",
)
ACCEPTANCE_TOOLCHAIN_FILES = (
    "controller/matrix.json",
    "schemas/run-result.schema.json",
    "scripts/accept_run.py",
    "scripts/blackbox_contract.py",
    "scripts/evaluate_matrix.py",
    "scripts/prepare_run.py",
)
RESULT_PROVENANCE_KEYS = {
    "controller_receipt_sha256",
    "run_manifest_sha256",
    "answer_key_sha256",
    "participant_zip_sha256",
    "returned_artifact",
    "acceptance_toolchain_sha256",
    "result_hmac_sha256",
}


class ContractError(ValueError):
    """Raised when a portable run violates a fail-closed contract."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_pairs
    )
    if not isinstance(value, dict):
        raise ContractError(f"JSON root must be an object: {path}")
    return value


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def safe_identifier(value: str, label: str) -> str:
    if not SAFE_ID.fullmatch(value):
        raise ContractError(
            f"{label} must use 3-64 lowercase letters, numbers, or dashes"
        )
    return value


def safe_nonce(value: str) -> str:
    if not NONCE.fullmatch(value):
        raise ContractError("nonce must be 32-128 lowercase hexadecimal characters")
    return value


def safe_relative_path(value: str, label: str) -> PurePosixPath:
    if not value or "\\" in value or value.startswith("/") or "//" in value:
        raise ContractError(f"{label} must be a normalized relative POSIX path")
    path = PurePosixPath(value)
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ContractError(f"{label} contains an unsafe path segment")
    if re.match(r"^[A-Za-z]:", value):
        raise ContractError(f"{label} cannot use a drive path")
    return path


def resolve_regular_file(root: Path, value: str, label: str) -> Path:
    relative = safe_relative_path(value, label)
    candidate = root.joinpath(*relative.parts)
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ContractError(f"{label} cannot traverse a symlink")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise ContractError(f"{label} is missing or escapes its root") from exc
    if not resolved.is_file():
        raise ContractError(f"{label} must resolve to a regular file")
    return resolved


def file_hashes(root: Path, relative_paths: Iterable[str] | None = None) -> dict[str, str]:
    if relative_paths is None:
        paths = [
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file()
        ]
    else:
        paths = list(relative_paths)
    result: dict[str, str] = {}
    for value in sorted(paths):
        path = resolve_regular_file(root, value, f"input file {value}")
        result[value] = sha256_file(path)
    return result


def tree_sha256(hashes: dict[str, str]) -> str:
    return sha256_bytes(canonical_json_bytes(hashes))


def acceptance_toolchain_hashes() -> dict[str, str]:
    return {
        value: sha256_file(resolve_regular_file(EVAL_ROOT, value, "acceptance toolchain file"))
        for value in ACCEPTANCE_TOOLCHAIN_FILES
    }


def acceptance_toolchain_sha256() -> str:
    return tree_sha256(acceptance_toolchain_hashes())


def directory_tree_sha256(root: Path) -> str:
    return tree_sha256(file_hashes(root))


def result_hmac_payload(result: dict[str, Any]) -> bytes:
    authenticated = copy.deepcopy(result)
    provenance = authenticated.get("provenance")
    if not isinstance(provenance, dict):
        raise ContractError("result provenance must be an object")
    provenance.pop("result_hmac_sha256", None)
    return canonical_json_bytes(authenticated)


def result_hmac_sha256(result: dict[str, Any], hexadecimal_key: str) -> str:
    if not isinstance(hexadecimal_key, str) or not re.fullmatch(
        r"[a-f0-9]{64}", hexadecimal_key
    ):
        raise ContractError("controller matrix HMAC key is invalid")
    return hmac.new(
        bytes.fromhex(hexadecimal_key),
        result_hmac_payload(result),
        hashlib.sha256,
    ).hexdigest()


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    return info


def deterministic_zip_tree(root: Path, output: Path) -> Path:
    if output.exists():
        raise ContractError(f"archive already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            if path.is_symlink():
                raise ContractError(f"archive input cannot contain symlinks: {path}")
            relative = path.relative_to(root).as_posix()
            archive.writestr(_zip_info(relative), path.read_bytes(), compresslevel=9)
    return output


def deterministic_zip_entries(entries: dict[str, bytes], output: Path) -> None:
    with zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for name, data in sorted(entries.items()):
            safe_relative_path(name, "generated archive entry")
            archive.writestr(_zip_info(name), data, compresslevel=9)


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_text_pdf(source: Path, output: Path) -> None:
    """Create a small deterministic, ASCII-only PDF without hidden metadata."""

    raw = source.read_text(encoding="utf-8")
    try:
        raw.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ContractError("text_to_pdf fixtures must remain ASCII") from exc
    sections = raw.split("\n---PAGE---\n")
    page_lines: list[list[str]] = []
    for section in sections:
        lines: list[str] = []
        for line in section.splitlines():
            if not line:
                lines.append("")
                continue
            while len(line) > 88:
                split_at = line.rfind(" ", 0, 89)
                split_at = split_at if split_at > 0 else 88
                lines.append(line[:split_at])
                line = line[split_at:].lstrip()
            lines.append(line)
        page_lines.append(lines)

    font_object = 3 + 2 * len(page_lines)
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        (
            f"<< /Type /Pages /Count {len(page_lines)} /Kids ["
            + " ".join(f"{3 + index * 2} 0 R" for index in range(len(page_lines)))
            + "] >>"
        ).encode("ascii"),
    ]
    for index, lines in enumerate(page_lines):
        page_object = 3 + index * 2
        content_object = page_object + 1
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                f"/Resources << /Font << /F1 {font_object} 0 R >> >> "
                f"/Contents {content_object} 0 R >>"
            ).encode("ascii")
        )
        commands = ["BT", "/F1 10 Tf", "54 788 Td", "14 TL"]
        for line in lines[:50]:
            commands.append(f"({_pdf_escape(line)}) Tj")
            commands.append("T*")
        commands.append("ET")
        stream = ("\n".join(commands) + "\n").encode("ascii")
        objects.append(
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"endstream"
        )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    content = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(content))
        content.extend(f"{number} 0 obj\n".encode("ascii"))
        content.extend(body)
        content.extend(b"\nendobj\n")
    xref = len(content)
    content.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    content.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        content.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    content.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n"
        ).encode("ascii")
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(bytes(content))


def build_text_docx(source: Path, output: Path) -> None:
    paragraphs = []
    for line in source.read_text(encoding="utf-8").splitlines():
        if line:
            paragraphs.append(
                "<w:p><w:r><w:t xml:space=\"preserve\">"
                + xml_escape(line, quote=True)
                + "</w:t></w:r></w:p>"
            )
        else:
            paragraphs.append("<w:p/>")
    entries = {
        "[Content_Types].xml": (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
            "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
            "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>"
            "<Default Extension=\"xml\" ContentType=\"application/xml\"/>"
            "<Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/>"
            "</Types>"
        ).encode("utf-8"),
        "_rels/.rels": (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
            "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
            "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"word/document.xml\"/>"
            "</Relationships>"
        ).encode("utf-8"),
        "word/document.xml": (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
            "<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">"
            "<w:body>"
            + "".join(paragraphs)
            + "<w:sectPr><w:pgSz w:w=\"12240\" w:h=\"15840\"/></w:sectPr>"
            "</w:body></w:document>"
        ).encode("utf-8"),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    deterministic_zip_entries(entries, output)


def _hex_color(value: str) -> tuple[int, int, int]:
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
        raise ContractError(f"invalid screenshot color: {value!r}")
    return tuple(int(value[index : index + 2], 16) for index in (1, 3, 5))


def build_screenshot(spec_path: Path, output: Path) -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:  # pragma: no cover - dependency failure path
        raise ContractError("Pillow is required to build screenshot fixtures") from exc
    spec = load_json(spec_path)
    width = spec.get("width")
    height = spec.get("height")
    if not isinstance(width, int) or not isinstance(height, int) or width < 400 or height < 225:
        raise ContractError("screenshot fixture dimensions are invalid")
    image = Image.new("RGB", (width, height), _hex_color(spec["background"]))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=24)
    small = ImageFont.load_default(size=18)
    header = spec["header"]
    draw.rectangle((0, 0, width, header["height"]), fill=_hex_color(header["background"]))
    draw.text((92, 27), header["label"], fill=(255, 255, 255), font=small)
    accent = spec["accent"]
    draw.rectangle(
        (
            accent["x"],
            accent["y"],
            accent["x"] + accent["width"],
            accent["y"] + accent["height"],
        ),
        fill=_hex_color(accent["color"]),
    )
    content = spec["content"]
    ink = _hex_color(content["ink"])
    muted = _hex_color(content["muted"])
    draw.text((content["x"], content["y"]), content["title"], fill=ink, font=font)
    draw.rectangle(
        (content["x"], content["y"] + 78, content["x"] + 920, content["y"] + 112),
        fill=ink,
    )
    for row, ratio in enumerate((0.92, 0.76, 0.84)):
        y = content["y"] + 172 + row * 76
        draw.rectangle(
            (content["x"], y, content["x"] + int(content["width"] * ratio), y + 20),
            fill=muted,
        )
    card_y = content["y"] + 430
    for column in range(3):
        x = content["x"] + column * 410
        draw.rounded_rectangle((x, card_y, x + 350, card_y + 110), radius=8, outline=ink, width=3)
    footer = spec["footer"]
    draw.line((92, footer["y"], width - 92, footer["y"]), fill=_hex_color(footer["rule"]), width=2)
    draw.text((92, footer["y"] + 28), footer["label"], fill=muted, font=small)
    draw.text((width - 210, footer["y"] + 28), footer["page"], fill=ink, font=small)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="PNG", optimize=False, compress_level=9)


def load_scenario(scenario_id: str) -> tuple[dict[str, Any], Path]:
    safe_identifier(scenario_id, "scenario_id")
    root = SCENARIO_ROOT / scenario_id
    spec_path = root / "scenario.json"
    if not spec_path.is_file():
        raise ContractError(f"unknown scenario: {scenario_id}")
    spec = load_json(spec_path)
    if set(spec) != {"scenario_contract_version", "scenario_id", "request", "materials"}:
        raise ContractError(f"scenario manifest fields drifted: {scenario_id}")
    if spec["scenario_contract_version"] != "1.0" or spec["scenario_id"] != scenario_id:
        raise ContractError(f"scenario identity mismatch: {scenario_id}")
    resolve_regular_file(root, spec["request"], "scenario request")
    if not isinstance(spec["materials"], list):
        raise ContractError("scenario materials must be an array")
    seen_outputs: set[str] = set()
    for item in spec["materials"]:
        if not isinstance(item, dict) or set(item) != {"source", "output", "transform"}:
            raise ContractError("scenario material record fields drifted")
        resolve_regular_file(root, item["source"], "scenario material source")
        safe_relative_path(item["output"], "scenario material output")
        if item["output"] in seen_outputs:
            raise ContractError("scenario material output is duplicated")
        seen_outputs.add(item["output"])
        if item["transform"] not in {
            "copy",
            "text_to_pdf",
            "text_to_docx",
            "screenshot_spec_to_png",
        }:
            raise ContractError(f"unsupported material transform: {item['transform']}")
    return spec, root


def build_material(source: Path, output: Path, transform: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ContractError(f"material output already exists: {output}")
    if transform == "copy":
        shutil.copyfile(source, output)
    elif transform == "text_to_pdf":
        build_text_pdf(source, output)
    elif transform == "text_to_docx":
        build_text_docx(source, output)
    elif transform == "screenshot_spec_to_png":
        build_screenshot(source, output)
    else:  # pragma: no cover - guarded by load_scenario
        raise ContractError(f"unsupported material transform: {transform}")


def load_answer_key(scenario_id: str) -> dict[str, Any]:
    key_path = ANSWER_ROOT / f"{safe_identifier(scenario_id, 'scenario_id')}.json"
    if not key_path.is_file():
        raise ContractError(f"missing controller answer key: {scenario_id}")
    value = load_json(key_path)
    required = {
        "answer_key_version",
        "scenario_id",
        "expected_profile",
        "hard_assertions",
        "leakage_markers",
        "follow_up_policy",
        "human_review_dimensions",
    }
    if set(value) != required or value["answer_key_version"] != "1.0":
        raise ContractError(f"answer key fields drifted: {scenario_id}")
    if value["scenario_id"] != scenario_id:
        raise ContractError(f"answer key scenario mismatch: {scenario_id}")
    return value


def leakage_markers() -> set[str]:
    markers = set(INTERNAL_FIELD_MARKERS)
    for key_path in sorted(ANSWER_ROOT.glob("*.json")):
        key = load_json(key_path)
        raw = key.get("leakage_markers")
        if not isinstance(raw, list) or not all(isinstance(item, str) and item for item in raw):
            raise ContractError(f"invalid leakage markers: {key_path}")
        markers.update(raw)
    return markers


def assert_no_answer_leakage(
    root: Path, *, exclude_prefixes: Iterable[str] = ()
) -> None:
    markers = {marker.casefold() for marker in leakage_markers()}
    excluded = [safe_relative_path(value, "leakage exclusion") for value in exclude_prefixes]
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ContractError(f"participant package cannot contain symlinks: {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        pure_relative = PurePosixPath(relative.as_posix())
        if any(
            pure_relative == prefix or prefix in pure_relative.parents
            for prefix in excluded
        ):
            continue
        for component in relative.parts:
            normalized = component.casefold()
            stem = Path(normalized).stem
            if normalized in PACKAGE_FORBIDDEN_COMPONENTS or stem in PACKAGE_FORBIDDEN_COMPONENTS:
                raise ContractError(f"controller-only filename leaked into package: {relative}")
        text = path.read_bytes().decode("utf-8", errors="ignore").casefold()
        leaked = sorted(marker for marker in markers if marker in text)
        if leaked:
            raise ContractError(
                f"controller answer marker leaked into participant file {relative}: {leaked}"
            )


def dotted_get(value: object, path: str) -> object:
    current = value
    for component in path.split("."):
        if not isinstance(current, dict) or component not in current:
            raise ContractError(f"assertion path is missing: {path}")
        current = current[component]
    return current


def evaluate_assertions(value: object, assertions: object) -> list[dict[str, Any]]:
    if not isinstance(assertions, list):
        raise ContractError("hard assertions must be an array")
    results: list[dict[str, Any]] = []
    for assertion in assertions:
        if not isinstance(assertion, dict) or set(assertion) != {"path", "equals"}:
            raise ContractError("hard assertion fields drifted")
        try:
            actual = dotted_get(value, assertion["path"])
            passed = actual == assertion["equals"]
            error = None
        except ContractError as exc:
            actual = None
            passed = False
            error = str(exc)
        results.append(
            {
                "path": assertion["path"],
                "expected": assertion["equals"],
                "actual": actual,
                "status": "PASS" if passed else "FAIL",
                "error": error,
            }
        )
    return results


def parse_utc(value: object, label: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ContractError(f"{label} must be an ISO-8601 UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ContractError(f"{label} is not a valid timestamp") from exc
    return parsed


def safe_extract_zip(archive_path: Path, destination: Path) -> Path:
    with zipfile.ZipFile(archive_path) as archive:
        infos = [info for info in archive.infolist() if not info.is_dir()]
        if len(infos) > 50_000:
            raise ContractError("returned archive contains too many files")
        if sum(info.file_size for info in infos) > 500 * 1024 * 1024:
            raise ContractError("returned archive exceeds the 500 MiB safety limit")
        seen: set[str] = set()
        for info in infos:
            if info.flag_bits & 0x1:
                raise ContractError("returned archive cannot contain encrypted entries")
            relative = safe_relative_path(info.filename, "returned archive entry")
            normalized = relative.as_posix()
            if normalized in seen:
                raise ContractError(f"duplicate returned archive entry: {normalized}")
            seen.add(normalized)
            mode = (info.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                raise ContractError(f"returned archive cannot contain symlinks: {normalized}")
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(info))
    return normalize_returned_root(destination)


def normalize_returned_root(root: Path) -> Path:
    if (root / "run.json").is_file():
        return root
    children = [item for item in root.iterdir() if item.name != ".DS_Store"]
    if len(children) == 1 and children[0].is_dir() and (children[0] / "run.json").is_file():
        return children[0]
    raise ContractError("returned package root must contain run.json")


def png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ContractError("generated screenshot is not a PNG")
    return struct.unpack(">II", data[16:24])


def crc32(path: Path) -> str:
    """Small fixture helper used only for human-readable diagnostics."""

    return f"{zlib.crc32(path.read_bytes()) & 0xFFFFFFFF:08x}"
