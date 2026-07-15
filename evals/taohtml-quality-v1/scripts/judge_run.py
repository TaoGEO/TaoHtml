#!/usr/bin/env python3
"""Run deterministic checks and write one TaoHtml benchmark result."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


BENCHMARK_ROOT = Path(__file__).resolve().parents[1]
SCENARIO_ROOT = BENCHMARK_ROOT / "controller" / "scenarios"
HUMAN_DIMENSIONS = (
    "story_progression",
    "page_role_clarity",
    "composition_hierarchy",
    "layout_repetition",
    "evidence_readability",
    "motion_support",
    "overall_finish",
)
ACTION_RE = re.compile(r"(?:https?://|mailto:|tel:)[^\s<>\"']+", re.IGNORECASE)
FACT_PATTERNS = (
    re.compile(r"(?<!\w)[$¥€£]\s?\d+(?:[.,]\d+)*(?:\s?[kKmM])?"),
    re.compile(r"\b\d+(?:\.\d+)?\s*(?:%|percent)(?!\w)", re.IGNORECASE),
    re.compile(r"\b\d+(?:\.\d+)?/\d+(?:\.\d+)?\b"),
    re.compile(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b"),
    re.compile(
        r"\b\d+(?:\.\d+)?\s*(?:months?|sites?|service deliveries|deliveries|minutes?|incidents?|hours?|responses?|respondents?|weeks?|signals?)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\d+(?:\.\d+)?\s*(?:\u4e2a\u6708|\u4e2a\u7ad9\u70b9|\u4e2a\u9879\u76ee|\u6bb5\u5bf9\u8bdd|\u4e2a\u7ebf\u7d22|\u6b21\u670d\u52a1|\u79d2|\u5206\u949f|\u5c0f\u65f6|\u5468|\u8d77\u4e8b\u4ef6|\u4efd\u54cd\u5e94|\u4e2a\u4fe1\u53f7|\u4f4d)"),
)
CREATIVE_STATUS_MARKERS = (
    "创作性补全",
    "推演",
    "示意",
    "模拟",
    "待核实",
    "creative supplement",
    "projected",
    "illustrative",
    "simulation",
    "pending verification",
)
VERIFIED_STATUS_MARKERS = (
    "用户已提供",
    "来源材料",
    "公开来源已核实",
    "真实数据",
    "已核实",
    "user-provided",
    "source material",
    "verified source",
)


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(value.split())


def normalize_token(value: str) -> str:
    return re.sub(r"\s+", "", normalize_text(value))


class DeckParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.section_depth = 0
        self.slide_start_depth: int | None = None
        self.current_slide: list[str] = []
        self.slides: list[str] = []
        self.skip_depth = 0
        self.deck_mode: str | None = None
        self.action_targets: set[str] = set()
        self.visible_action_targets: set[str] = set()
        self.source_buttons = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name: value or "" for name, value in attrs}
        classes = set(values.get("class", "").split())
        if tag in {"script", "style", "template"}:
            self.skip_depth += 1
        if tag == "main" and "deck" in classes:
            self.deck_mode = values.get("data-mode") or None
        if tag == "section":
            self.section_depth += 1
            if "slide" in classes and self.slide_start_depth is None:
                self.slide_start_depth = self.section_depth
                self.current_slide = []
        href = values.get("href", "")
        if href.lower().startswith(("http://", "https://", "mailto:", "tel:")):
            self.action_targets.add(href.rstrip(".,);。，；"))
        if "source-btn" in classes or "data-source" in values:
            self.source_buttons += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag in {"script", "style", "template"}:
            self.skip_depth = max(0, self.skip_depth - 1)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "template"}:
            self.skip_depth = max(0, self.skip_depth - 1)
        if tag == "section":
            if self.slide_start_depth == self.section_depth:
                self.slides.append(normalize_text(" ".join(self.current_slide)))
                self.slide_start_depth = None
                self.current_slide = []
            self.section_depth = max(0, self.section_depth - 1)

    def handle_data(self, data: str) -> None:
        if self.slide_start_depth is not None and self.skip_depth == 0 and data.strip():
            self.current_slide.append(data.strip())
            self.visible_action_targets.update(
                item.rstrip(".,);。，；") for item in ACTION_RE.findall(data)
            )


def load_scenario(scenario_id: str) -> dict[str, Any]:
    path = SCENARIO_ROOT / f"{scenario_id}.json"
    if not path.is_file():
        raise ValueError(f"Unknown scenario: {scenario_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def make_check(
    check_id: str,
    category: str,
    status: str,
    summary: str,
    evidence: Any,
    *,
    hard_failure: bool = True,
    scope: str = "artifact",
) -> dict[str, Any]:
    if status not in {"pass", "warning", "fail", "unavailable"}:
        raise ValueError(f"Unknown check status: {status}")
    if scope not in {"artifact", "workflow"}:
        raise ValueError(f"Unknown check scope: {scope}")
    return {
        "id": check_id,
        "category": category,
        "status": status,
        "hard_failure": hard_failure,
        "scope": scope,
        "summary": summary,
        "evidence": evidence,
    }


def inspect_content(html: Path, scenario: dict[str, Any]) -> tuple[DeckParser, list[dict[str, Any]]]:
    parser = DeckParser()
    parser.feed(html.read_text(encoding="utf-8", errors="replace"))
    full_text = normalize_text(" ".join(parser.slides))
    expected = scenario["expected_delivery"]
    content = scenario["content_checks"]
    checks: list[dict[str, Any]] = []

    minimum = expected.get("minimum_slides", 2)
    maximum = expected.get("maximum_slides")
    count_ok = len(parser.slides) >= minimum and (maximum is None or len(parser.slides) <= maximum)
    checks.append(
        make_check(
            "delivery.slide-count",
            "delivery_files",
            "pass" if count_ok else "fail",
            "Slide count stays within the scenario contract.",
            {"actual": len(parser.slides), "minimum": minimum, "maximum": maximum},
        )
    )

    expected_mode = expected.get("initial_mode")
    checks.append(
        make_check(
            "delivery.initial-mode",
            "delivery_files",
            "pass" if parser.deck_mode == expected_mode else "fail",
            "Initial runtime mode matches the use case.",
            {"actual": parser.deck_mode, "expected": expected_mode},
        )
    )

    missing_groups = []
    for group in content.get("required_text_groups", []):
        candidates = [normalize_text(candidate) for candidate in group["any"]]
        if not any(candidate in full_text for candidate in candidates):
            missing_groups.append(group["id"])
    checks.append(
        make_check(
            "content.core-viewpoints",
            "content_integrity",
            "pass" if not missing_groups else "fail",
            "Protected viewpoints and evidence remain visible.",
            {"missing_groups": missing_groups},
        )
    )

    forbidden_found = [
        phrase
        for phrase in content.get("forbidden_text", [])
        if normalize_text(phrase) in full_text
    ]
    checks.append(
        make_check(
            "content.forbidden-claims",
            "unsupported_claims",
            "pass" if not forbidden_found else "fail",
            "Known false or disallowed claims are absent.",
            {"matches": forbidden_found},
        )
    )

    exact_expected = content.get("exact_slide_text")
    exact_actual = parser.slides
    exact_ok = exact_expected is None or [normalize_text(item) for item in exact_expected] == exact_actual
    checks.append(
        make_check(
            "content.exact-page-copy",
            "content_integrity",
            "pass" if exact_ok else "fail",
            "Content-locked pages preserve exact visible copy and order.",
            {"expected": exact_expected, "actual": exact_actual} if not exact_ok else {"pages": len(exact_actual)},
        )
    )

    found_fact_tokens: set[str] = set()
    for pattern in FACT_PATTERNS:
        found_fact_tokens.update(match.group(0) for match in pattern.finditer(full_text))
    allowed_fact_tokens = {normalize_token(item) for item in content.get("allowed_fact_tokens", [])}
    unexpected_facts = sorted(
        token for token in found_fact_tokens if normalize_token(token) not in allowed_fact_tokens
    )
    fact_policy = content.get("fact_policy", "source_locked")
    if fact_policy not in {"source_locked", "creative_handoff"}:
        raise ValueError(f"Unknown fact_policy: {fact_policy}")
    fact_status = (
        "fail"
        if unexpected_facts and fact_policy == "source_locked"
        else "pass"
    )
    fact_summary = (
        "Detected numeric factual claims stay within the source allowlist."
        if fact_policy == "source_locked"
        else "Ordinary generated numeric claims are treated as creative supplements pending delivery-handoff coverage."
    )
    checks.append(
        make_check(
            "content.source-bounded-facts",
            "unsupported_claims",
            fact_status,
            fact_summary,
            {
                "policy": fact_policy,
                "unexpected": unexpected_facts,
                "detected": sorted(found_fact_tokens),
            },
        )
    )

    found_actions = parser.action_targets | parser.visible_action_targets
    allowed_actions = set(content.get("allowed_action_targets", []))
    unexpected_actions = sorted(found_actions - allowed_actions)
    missing_actions = sorted(allowed_actions - found_actions)
    actions_ok = not unexpected_actions and not missing_actions
    checks.append(
        make_check(
            "content.action-targets",
            "unsupported_actions",
            "pass" if actions_ok else "fail",
            "Action targets are present only when explicitly supplied.",
            {"unexpected": unexpected_actions, "missing": missing_actions},
        )
    )

    minimum_sources = expected.get("minimum_source_buttons", 0)
    checks.append(
        make_check(
            "content.source-access",
            "evidence_access",
            "pass" if parser.source_buttons >= minimum_sources else "fail",
            "The required source evidence access is present.",
            {"actual": parser.source_buttons, "minimum": minimum_sources},
        )
    )
    return parser, checks


def inspect_verification_handoff(
    handoff_text: str | None,
    scenario: dict[str, Any],
    creative_fact_tokens: list[str],
) -> list[dict[str, Any]]:
    config = scenario.get("expected_delivery", {}).get("verification_handoff")
    if not config:
        return []

    text = handoff_text or ""
    normalized = normalize_text(text)
    compact = normalize_token(text)
    title_candidates = config.get("title_any", ["待核实内容清单"])
    missing_fields = []
    for field in config.get("required_field_groups", []):
        if not any(normalize_text(candidate) in normalized for candidate in field["any"]):
            missing_fields.append(field["id"])
    has_title = any(normalize_text(candidate) in normalized for candidate in title_candidates)
    empty_markers = config.get(
        "empty_any",
        ["无；本报告未新增待客户核实的事实性内容", "no creative supplements added"],
    )
    declares_empty = any(normalize_text(candidate) in normalized for candidate in empty_markers)
    allow_empty = config.get("allow_empty", False)
    empty_accepted = declares_empty and allow_empty
    structured = (
        bool(text.strip())
        and has_title
        and (not missing_fields or empty_accepted)
        and not (declares_empty and not allow_empty)
    )
    checks = [
        make_check(
            "delivery.verification-handoff",
            "verification_handoff",
            "pass" if structured else "warning",
            "Delivery includes a structured pending-verification list with location, supplement type, source status, and suggested action.",
            {
                "provided": bool(text.strip()),
                "title_present": has_title,
                "declares_empty": declares_empty,
                "allow_empty": allow_empty,
                "empty_accepted": empty_accepted,
                "missing_fields": [] if empty_accepted else missing_fields,
            },
            hard_failure=False,
            scope="workflow",
        )
    ]

    missing_creative_facts = [
        token
        for token in creative_fact_tokens
        if normalize_token(token) not in compact
    ]
    checks.append(
        make_check(
            "handoff.creative-fact-coverage",
            "verification_handoff",
            "pass" if structured and not missing_creative_facts else "warning",
            "Generated numeric claims are locatable in the pending-verification list.",
            {
                "creative_fact_tokens": creative_fact_tokens,
                "missing": missing_creative_facts,
            },
            hard_failure=False,
            scope="workflow",
        )
    )

    protected_tokens = {
        *scenario.get("content_checks", {}).get("protected_handoff_tokens", []),
        *scenario.get("content_checks", {}).get("allowed_fact_tokens", []),
        *scenario.get("content_checks", {}).get("allowed_action_targets", []),
    }
    creative_markers = tuple(normalize_text(item) for item in CREATIVE_STATUS_MARKERS)
    verified_markers = tuple(normalize_text(item) for item in VERIFIED_STATUS_MARKERS)
    misclassified = []
    for line in text.splitlines():
        normalized_line = normalize_text(line)
        compact_line = normalize_token(line)
        if not any(marker in normalized_line for marker in creative_markers):
            continue
        if any(marker in normalized_line for marker in verified_markers):
            continue
        for token in protected_tokens:
            if normalize_token(token) in compact_line:
                misclassified.append({"token": token, "line": line.strip()})
    checks.append(
        make_check(
            "handoff.protected-source-classification",
            "source_integrity",
            "pass" if not misclassified else "fail",
            "Confirmed source data and action channels keep their real provenance in the delivery handoff.",
            {"misclassified": misclassified},
            scope="workflow",
        )
    )
    return checks


def classify_checks(checks: list[dict[str, Any]]) -> dict[str, Any]:
    hard_failure_count = sum(
        check["status"] == "fail" and check["hard_failure"] for check in checks
    )
    warning_count = sum(check["status"] == "warning" for check in checks)
    artifact_checks = [check for check in checks if check.get("scope", "artifact") == "artifact"]
    artifact_unavailable = any(
        check["status"] == "unavailable" and check["hard_failure"]
        for check in artifact_checks
    )
    artifact_failed = any(
        check["status"] == "fail" and check["hard_failure"]
        for check in artifact_checks
    )
    artifact_status = (
        "unavailable" if artifact_unavailable else ("fail" if artifact_failed else "pass")
    )
    hard_unavailable = any(
        check["status"] == "unavailable" and check["hard_failure"] for check in checks
    )
    workflow_status = (
        "unavailable"
        if hard_unavailable
        else (
            "fail"
            if hard_failure_count
            else ("conditional" if warning_count else "pass")
        )
    )
    return {
        "status": workflow_status,
        "artifact_status": artifact_status,
        "hard_failure_count": hard_failure_count,
        "warning_count": warning_count,
        "hard_unavailable": hard_unavailable,
    }


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True)


def asset_check(workspace: Path, html: Path) -> dict[str, Any]:
    script = workspace / "skill" / "taohtml" / "scripts" / "check_assets.py"
    if not script.is_file():
        return make_check(
            "assets.offline",
            "offline_assets",
            "unavailable",
            "The copied skill does not contain check_assets.py.",
            {"script": str(script)},
        )
    result = run_command([sys.executable, str(script), str(html), "--strict-offline"])
    return make_check(
        "assets.offline",
        "offline_assets",
        "pass" if result.returncode == 0 else "fail",
        "All visual, font, script, and stylesheet assets are local and present.",
        {"returncode": result.returncode, "output": (result.stdout + result.stderr)[-4000:]},
    )


def unavailable_browser_checks(
    reason: str, *, hard_failure: bool = True
) -> list[dict[str, Any]]:
    return [
        make_check(
            check_id,
            category,
            "unavailable",
            reason,
            {},
            hard_failure=hard_failure,
        )
        for check_id, category in (
            ("runtime.contract", "runtime_contract"),
            ("navigation.routes", "navigation"),
            ("runtime.state", "runtime_state"),
            ("assets.browser-load", "offline_assets"),
            ("layout.overflow", "overflow"),
            ("browser.console", "console"),
        )
    ]


def browser_checks(workspace: Path, html: Path, skip: bool) -> list[dict[str, Any]]:
    if skip:
        return unavailable_browser_checks("Browser QA was explicitly skipped.")
    script = workspace / "skill" / "taohtml" / "scripts" / "check_html_deck.py"
    if not script.is_file():
        return unavailable_browser_checks("The copied skill does not contain check_html_deck.py.")
    qa_dir = workspace / ".benchmark-qa"
    result = run_command(
        [
            sys.executable,
            str(script),
            str(html),
            str(qa_dir),
            "--width",
            "1600",
            "--height",
            "900",
        ]
    )
    report_path = qa_dir / "qa-report.json"
    if not report_path.is_file():
        output = result.stdout + result.stderr
        reason = "Browser QA did not produce a report: " + output[-1000:]
        infrastructure_markers = (
            "Playwright is required",
            "Executable doesn't exist",
            "BrowserType.launch",
            "playwright install",
        )
        if any(marker in output for marker in infrastructure_markers):
            return unavailable_browser_checks(reason)
        return [
            make_check(check_id, category, "fail", reason, {})
            for check_id, category in (
                ("runtime.contract", "runtime_contract"),
                ("navigation.routes", "navigation"),
                ("runtime.state", "runtime_state"),
                ("assets.browser-load", "offline_assets"),
                ("layout.overflow", "overflow"),
                ("browser.console", "console"),
            )
        ]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    pages = report.get("pages", [])
    runtime = report.get("runtime_contract", {})
    behavior = report.get("runtime_behavior", {})

    runtime_ok = bool(runtime.get("available")) and not runtime.get("missing")
    routes_ok = bool(pages) and all(page.get("route_ok") for page in pages)
    state_markers = (
        "ArrowRight",
        "ArrowLeft",
        "PageDown",
        "Returning to a page",
        "Reading mode",
        "Switching from reading",
        "Focused controls",
        "Fullscreen",
        "sharing one data-step",
        "fragments became visible",
        "fragments remained after rewind",
    )
    process_output = result.stdout + result.stderr
    state_failures = [line for line in process_output.splitlines() if any(marker in line for marker in state_markers)]
    state_ok = bool(behavior.get("tested")) and not state_failures
    overflow = [
        {"page": page.get("page"), "elements": page.get("offscreen_elements", [])}
        for page in pages
        if page.get("offscreen_elements")
    ]
    console = [
        {
            "page": page.get("page"),
            "console_errors": page.get("console_errors", []),
            "page_errors": page.get("page_errors", []),
        }
        for page in pages
        if page.get("console_errors") or page.get("page_errors")
    ]
    media_failures = [
        {
            "page": page.get("page"),
            "source_failures": page.get("source_failures", []),
            "image_failures": page.get("image_failures", []),
        }
        for page in pages
        if page.get("source_failures") or page.get("image_failures")
    ]
    return [
        make_check(
            "runtime.contract",
            "runtime_contract",
            "pass" if runtime_ok else "fail",
            "The public TaoHtml Runtime API is complete.",
            runtime,
        ),
        make_check(
            "navigation.routes",
            "navigation",
            "pass" if routes_ok else "fail",
            "Hash navigation activates exactly one expected page.",
            {"failed_pages": [page.get("page") for page in pages if not page.get("route_ok")]},
        ),
        make_check(
            "runtime.state",
            "runtime_state",
            "pass" if state_ok else "fail",
            "Modes, reveal steps, return state, controls, and fullscreen follow the contract.",
            {"tested": behavior.get("tested", False), "failures": state_failures},
        ),
        make_check(
            "assets.browser-load",
            "offline_assets",
            "pass" if not media_failures else "fail",
            "Local images and source evidence load successfully in the browser.",
            {"pages": media_failures},
        ),
        make_check(
            "layout.overflow",
            "overflow",
            "pass" if not overflow else "fail",
            "Visible content stays inside the 1600x900 slide bounds.",
            {"pages": overflow},
        ),
        make_check(
            "browser.console",
            "console",
            "pass" if not console else "fail",
            "No browser console or page errors occur during the full route pass.",
            {"pages": console},
        ),
    ]


def pending_human_review() -> dict[str, Any]:
    return {
        "status": "pending",
        "reviewer": "unavailable",
        "reviewed_at": None,
        "dimensions": {key: {"score": None, "note": ""} for key in HUMAN_DIMENSIONS},
        "manual_revision_count": None,
        "reference_floor": {"status": "unavailable", "note": ""},
        "notes": "",
        "failure_samples": [],
    }


def validate_metadata(metadata: dict[str, Any], scenario_id: str) -> None:
    required = {
        "id",
        "scenario_id",
        "client",
        "agent",
        "model",
        "skill",
        "started_at",
        "ended_at",
        "question_count",
        "token_usage",
        "billing_usage",
        "duration",
    }
    missing = sorted(required - metadata.keys())
    if missing:
        raise ValueError(f"Metadata is missing: {', '.join(missing)}")
    if metadata["scenario_id"] != scenario_id:
        raise ValueError("Metadata scenario_id does not match the selected scenario")
    if not isinstance(metadata["question_count"], int) or metadata["question_count"] < 0:
        raise ValueError("question_count must be a non-negative integer")
    for field in ("client", "agent", "model", "started_at", "ended_at"):
        if not isinstance(metadata[field], str) or not metadata[field].strip():
            raise ValueError(f"{field} must be a non-empty string")
    skill = metadata["skill"]
    if not isinstance(skill, dict) or not all(
        isinstance(skill.get(field), str) and skill[field].strip()
        for field in ("version", "commit")
    ):
        raise ValueError("skill.version and skill.commit must be non-empty strings")
    token_usage = metadata["token_usage"]
    if not isinstance(token_usage, dict):
        raise ValueError("token_usage must be an object")
    token_availability = token_usage.get("availability")
    token_source = token_usage.get("source")
    token_keys = ("input_tokens", "output_tokens", "cache_tokens", "total_tokens")
    token_values = [token_usage.get(key) for key in token_keys]
    if token_availability not in {"exact", "unavailable"}:
        raise ValueError("token_usage.availability must be exact or unavailable")
    if token_availability == "unavailable":
        if token_source != "unavailable" or any(value is not None for value in token_values):
            raise ValueError("unavailable token_usage must use source unavailable and null values")
    else:
        if token_source not in {"platform_task_usage", "manual"}:
            raise ValueError("exact token_usage source must be platform_task_usage or manual")
        if any(
            value is not None
            and (not isinstance(value, int) or isinstance(value, bool) or value < 0)
            for value in token_values
        ):
            raise ValueError("exact token values must be non-negative integers or null")
        if all(value is None for value in token_values):
            raise ValueError("exact token_usage must contain at least one platform value")

    billing_usage = metadata["billing_usage"]
    if not isinstance(billing_usage, dict):
        raise ValueError("billing_usage must be an object")
    billing_availability = billing_usage.get("availability")
    billing_source = billing_usage.get("source")
    billing_keys = ("workbuddy_points", "balance_before", "balance_after")
    billing_values = [billing_usage.get(key) for key in billing_keys]
    if billing_availability not in {"exact", "unavailable"}:
        raise ValueError("billing_usage.availability must be exact or unavailable")
    if billing_availability == "unavailable":
        if billing_source != "unavailable" or any(value is not None for value in billing_values):
            raise ValueError("unavailable billing_usage must use source unavailable and null values")
    else:
        if billing_source not in {"platform_task_usage", "balance_delta", "manual"}:
            raise ValueError("exact billing_usage source is invalid")
        points = billing_usage.get("workbuddy_points")
        if (
            not isinstance(points, (int, float))
            or isinstance(points, bool)
            or points < 0
        ):
            raise ValueError("exact billing_usage.workbuddy_points must be non-negative")
        before = billing_usage.get("balance_before")
        after = billing_usage.get("balance_after")
        if billing_source == "balance_delta":
            if any(
                not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0
                for value in (before, after)
            ):
                raise ValueError("balance_delta requires non-negative platform balances")
            if before < after or abs((before - after) - points) > 1e-9:
                raise ValueError("workbuddy_points must exactly equal balance_before - balance_after")
        elif before is not None or after is not None:
            raise ValueError("balances are recorded only when billing_usage.source is balance_delta")

    duration = metadata["duration"]
    if not isinstance(duration, dict) or duration.get("status") not in {
        "available",
        "unavailable",
    }:
        raise ValueError("duration.status must be available or unavailable")
    seconds = duration.get("seconds")
    if duration["status"] == "unavailable" and seconds is not None:
        raise ValueError("unavailable duration.seconds must be null")
    if duration["status"] == "available" and (
        not isinstance(seconds, (int, float)) or seconds < 0
    ):
        raise ValueError("available duration.seconds must be a non-negative number")


def validate_human_review(review: dict[str, Any]) -> None:
    if review.get("status") not in {"complete", "pending"}:
        raise ValueError("human review status must be complete or pending")
    dimensions = review.get("dimensions", {})
    if set(dimensions) != set(HUMAN_DIMENSIONS):
        raise ValueError("human review must contain exactly the seven benchmark dimensions")
    for key, value in dimensions.items():
        score = value.get("score") if isinstance(value, dict) else None
        if score is not None and (not isinstance(score, int) or not 1 <= score <= 5):
            raise ValueError(f"human dimension {key} score must be 1-5 or null")
    revisions = review.get("manual_revision_count")
    if revisions is not None and (not isinstance(revisions, int) or revisions < 0):
        raise ValueError("manual_revision_count must be a non-negative integer or null")
    reference_floor = review.get("reference_floor", {})
    if reference_floor.get("status") not in {"below", "matches", "exceeds", "unavailable"}:
        raise ValueError("reference_floor.status is invalid")


def judge(
    scenario_id: str,
    workspace: Path,
    metadata: dict[str, Any],
    human_review: dict[str, Any] | None,
    *,
    skip_browser: bool = False,
    handoff_text: str | None = None,
) -> dict[str, Any]:
    scenario = load_scenario(scenario_id)
    validate_metadata(metadata, scenario_id)
    expected_entrypoint = workspace / scenario["expected_delivery"]["entrypoint"]
    checks: list[dict[str, Any]] = []
    maximum_questions = scenario["expected_delivery"].get("maximum_questions", 6)
    checks.append(
        make_check(
            "intake.question-cap",
            "intake",
            "pass" if metadata["question_count"] <= maximum_questions else "fail",
            "Agent-initiated clarification questions stay within the scenario cap.",
            {"actual": metadata["question_count"], "maximum": maximum_questions},
            scope="workflow",
        )
    )
    if not expected_entrypoint.is_file():
        checks.append(
            make_check(
                "delivery.entrypoint",
                "delivery_files",
                "fail",
                "The required runnable entry point exists.",
                {"missing": str(expected_entrypoint)},
            )
        )
        checks.extend(
            make_check(
                check_id,
                category,
                "unavailable",
                "The entry point is missing, so this check cannot run.",
                {},
                hard_failure=False,
            )
            for check_id, category in (
                ("content.core-viewpoints", "content_integrity"),
                ("assets.offline", "offline_assets"),
            )
        )
        checks.extend(
            unavailable_browser_checks("The entry point is missing.", hard_failure=False)
        )
    else:
        checks.append(
            make_check(
                "delivery.entrypoint",
                "delivery_files",
                "pass",
                "The required runnable entry point exists.",
                {"path": str(expected_entrypoint)},
            )
        )
        _, content_checks = inspect_content(expected_entrypoint, scenario)
        checks.extend(content_checks)
        creative_fact_tokens: list[str] = []
        for check in content_checks:
            if check["id"] == "content.source-bounded-facts" and check["evidence"].get(
                "policy"
            ) == "creative_handoff":
                creative_fact_tokens = check["evidence"].get("unexpected", [])
                break
        checks.extend(
            inspect_verification_handoff(
                handoff_text,
                scenario,
                creative_fact_tokens,
            )
        )
        checks.append(asset_check(workspace, expected_entrypoint))
        checks.extend(browser_checks(workspace, expected_entrypoint, skip_browser))

    classification = classify_checks(checks)
    review = human_review or pending_human_review()
    validate_human_review(review)
    failure_samples = [
        {
            "source": "objective",
            "check_id": check["id"],
            "summary": check["summary"],
            "evidence": check["evidence"],
        }
        for check in checks
        if check["status"] in {"warning", "fail", "unavailable"}
    ]
    failure_samples.extend(review.get("failure_samples", []))
    return {
        "schema_version": "1.0",
        "run": metadata,
        "objective": {
            "status": classification["status"],
            "artifact_status": classification["artifact_status"],
            "hard_failure_count": classification["hard_failure_count"],
            "warning_count": classification["warning_count"],
            "checks": checks,
        },
        "human": review,
        "failure_samples": failure_samples,
        "comparison": {
            "comparable": not classification["hard_unavailable"],
            "benchmark_success": classification["status"] == "pass",
            "artifact_usable": classification["artifact_status"] == "pass",
            "workflow_status": classification["status"],
            "note": "Artifact usability and full-workflow disclosure are reported separately. Human dimension scores do not override hard failures or grant production permission.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Judge one completed TaoHtml benchmark run.")
    parser.add_argument("scenario")
    parser.add_argument("workspace", type=Path)
    parser.add_argument("metadata", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--human-review", type=Path)
    parser.add_argument(
        "--handoff",
        type=Path,
        help="UTF-8 file containing the Agent's final delivery message, including 《待核实内容清单》.",
    )
    parser.add_argument(
        "--skip-browser",
        action="store_true",
        help="Development only: records browser checks as unavailable, making the run non-comparable.",
    )
    args = parser.parse_args()
    try:
        metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
        review = (
            json.loads(args.human_review.read_text(encoding="utf-8"))
            if args.human_review
            else None
        )
        handoff_text = args.handoff.read_text(encoding="utf-8") if args.handoff else None
        result = judge(
            args.scenario,
            args.workspace.resolve(),
            metadata,
            review,
            skip_browser=args.skip_browser,
            handoff_text=handoff_text,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"JUDGE_FAILED: {exc}", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"JUDGE_{result['objective']['status'].upper()} {args.output}")
    return {"pass": 0, "conditional": 0, "fail": 1, "unavailable": 2}[
        result["objective"]["status"]
    ]


if __name__ == "__main__":
    sys.exit(main())
