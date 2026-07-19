#!/usr/bin/env python3
"""Create one isolated, answer-free participant package and controller receipt."""

from __future__ import annotations

import argparse
import secrets
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from blackbox_contract import (
    ANSWER_ROOT,
    RECEIPT_VERSION,
    REQUIRED_OUTPUTS,
    RUN_CONTRACT_VERSION,
    ContractError,
    acceptance_toolchain_sha256,
    assert_no_answer_leakage,
    build_material,
    deterministic_zip_tree,
    file_hashes,
    load_answer_key,
    load_scenario,
    parse_utc,
    safe_identifier,
    safe_nonce,
    sha256_file,
    tree_sha256,
    utc_now,
    write_json,
)


def generated_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dt%H%M%sz").lower()
    return f"{stamp}-{secrets.token_hex(4)}"


def instructions(run_id: str, nonce: str, output_directory: str) -> str:
    return f"""# TaoHtml 跨 Agent 黑盒运行说明

本包是一场全新、隔离的工程回归。`request.md` 是原始用户请求；`materials/` 中列出的文件是本次唯一用户材料。运行身份为 `{run_id}`，nonce 为 `{nonce}`。先读取并核对 `run.json`，再开始工作。

## 读取边界

- 只允许读取本包中的 `request.md`、`materials/`、`run.json`、本说明，以及当前平台已安装的 TaoHtml Skill。
- 不得读取父目录、兄弟目录、仓库、其他测试案例、历史 build、旧结构化源、旧 HTML、答案、评分规则或以往运行产物。
- 不得联网，不得调用模型 API 充当评估器，不得复用、搜索或改写任何既有结果。
- 如果平台不能遵守这个读取边界，停止并报告，不能继续生成看似有效的产物。

## 开始条件

1. 逐项核对 `run.json` 中的输入文件哈希；任何缺失或不一致都必须停止。
2. 输出目录必须是 `{output_directory}`。如果它已经存在，必须停止；不得覆盖、清理、合并或续写。
3. 从原始业务目标独立选择唯一最合适的 TaoHtml 工作路径，不要让文件名替代语义判断。
4. 本回归明确要求走 TaoHtml 当前的可重新编译工程路线：在材料理解、完整设计简报及其确认成立后，生成结构化报告源并使用当前无模型 Compiler 生成 HTML。这个测试要求不替代任何精确到当前文件的正式制作、浏览器 QA 或交付确认；需要该确认时，展示当前记录并向主控提问，不得自造确认。

## 交付合同

在唯一的新输出目录中保留一个自包含工程；所有被使用的原始材料应复制到该目录的 `materials/` 并保持字节不变。至少交付：

- `design-brief.md`
- `report-ir.json`
- `build/index.html`
- `build/build-manifest.json`
- `build/source-map.json`
- `build/report.ir.normalized.json`
- `project-handoff.json`
- `handoff.md`
- `submission.json`

需要企业视觉重构时，把当前编译实际使用的 project-theme bundle 一并放在 `project-theme/`。QA 记录和授权记录按 TaoHtml 当前便携交接合同放入输出目录，并由 `project-handoff.json` 绑定；文件存在不等于浏览器 QA 已执行。

`submission.json` 只用于绑定本次运行，格式如下；`artifacts` 必须列出输出目录中除 `submission.json` 自身之外的每个文件及其当前 SHA-256：

```json
{{
  "submission_contract_version": "taohtml-cross-agent-submission-1",
  "run_id": "{run_id}",
  "nonce": "{nonce}",
  "scenario_id": "与 run.json 一致",
  "input_tree_sha256": "与 run.json 一致",
  "audit": {{
    "platform": "实际平台",
    "agent": "实际 Agent",
    "model": "实际模型；平台未显示则写 unknown",
    "started_at": "UTC ISO-8601 时间",
    "ended_at": "UTC ISO-8601 时间",
    "tokens": {{"availability": "exact 或 unknown", "source": "platform_task_usage、manual 或 unknown", "input": null, "output": null, "cache": null, "total": null}},
    "points": {{"availability": "exact 或 unknown", "source": "platform_task_usage、balance_delta、manual 或 unknown", "value": null, "balance_before": null, "balance_after": null}}
  }},
  "isolation_attestation": {{
    "package_root_only": true,
    "installed_taohtml_only_external_input": true,
    "no_prior_artifacts_used": true
  }},
  "artifacts": {{"design-brief.md": "sha256", "...": "sha256"}}
}}
```

Token 或积分只有平台提供本次任务的精确数值时才能写 `exact`；未知时保留 `unknown` 和 `null`，不得估算。积分使用 `balance_delta` 时，必须同时记录无其他消费窗口内的前后官方余额，且差值与 `value` 完全一致。平台、Agent、模型和用量只供审计，不决定技术 PASS。

完成后返回整个包根目录（包含原始输入、`run.json` 和唯一输出目录）的 ZIP。不要只返回 HTML，也不要删除输入来缩小包。
"""


def repository_commit(repository_root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unavailable"


def prepare(
    scenario_id: str,
    platform: str,
    runs_root: Path,
    *,
    run_id: str | None = None,
    nonce: str | None = None,
    created_at: str | None = None,
) -> dict[str, Path | str]:
    scenario_id = safe_identifier(scenario_id, "scenario_id")
    if platform not in {"codex", "workbuddy"}:
        raise ContractError("platform must be codex or workbuddy")
    run_id = safe_identifier(run_id or generated_run_id(), "run_id")
    nonce = safe_nonce(nonce or secrets.token_hex(16))
    created_at = created_at or utc_now()
    parse_utc(created_at, "created_at")
    spec, scenario_root = load_scenario(scenario_id)
    answer_key = load_answer_key(scenario_id)

    runs_root.mkdir(parents=True, exist_ok=True)
    run_root = runs_root / run_id
    if run_root.exists():
        raise ContractError(f"run directory already exists: {run_root}")
    run_root.mkdir()
    participant_tree = run_root / "participant-tree"
    controller_dir = run_root / "controller"
    participant_tree.mkdir()
    controller_dir.mkdir()

    request_source = scenario_root / spec["request"]
    (participant_tree / "request.md").write_bytes(request_source.read_bytes())
    material_outputs: list[str] = []
    for material in spec["materials"]:
        source = scenario_root / material["source"]
        output = participant_tree / material["output"]
        build_material(source, output, material["transform"])
        material_outputs.append(material["output"])

    output_directory = f"submission/{run_id}"
    (participant_tree / "RUN_INSTRUCTIONS.md").write_text(
        instructions(run_id, nonce, output_directory), encoding="utf-8"
    )
    inputs = file_hashes(participant_tree)
    input_tree = tree_sha256(inputs)
    run_manifest = {
        "run_contract_version": RUN_CONTRACT_VERSION,
        "run_id": run_id,
        "nonce": nonce,
        "scenario_id": scenario_id,
        "target_platform": platform,
        "created_at": created_at,
        "request": "request.md",
        "materials": sorted(material_outputs),
        "allowed_external_input": "installed TaoHtml Skill only",
        "output_directory": output_directory,
        "required_outputs": list(REQUIRED_OUTPUTS),
        "input_files": inputs,
        "input_tree_sha256": input_tree,
    }
    write_json(participant_tree / "run.json", run_manifest)
    assert_no_answer_leakage(participant_tree)

    archive_path = run_root / f"{platform}-participant-{run_id}.zip"
    deterministic_zip_tree(participant_tree, archive_path)
    key_path = ANSWER_ROOT / f"{scenario_id}.json"
    from blackbox_contract import REPOSITORY_ROOT  # local import keeps constants central

    receipt = {
        "receipt_version": RECEIPT_VERSION,
        "run_id": run_id,
        "nonce": nonce,
        "scenario_id": scenario_id,
        "target_platform": platform,
        "created_at": created_at,
        "output_directory": output_directory,
        "required_outputs": list(REQUIRED_OUTPUTS),
        "input_files": inputs,
        "input_tree_sha256": input_tree,
        "run_manifest_sha256": sha256_file(participant_tree / "run.json"),
        "participant_zip_sha256": sha256_file(archive_path),
        "answer_key_sha256": sha256_file(key_path),
        "acceptance_toolchain_sha256": acceptance_toolchain_sha256(),
        "matrix_hmac_key": secrets.token_hex(32),
        "source_commit": repository_commit(REPOSITORY_ROOT),
        "participant_contents": sorted([*inputs, "run.json"]),
        "controller_answer_embedded": False,
        "expected_profile_embedded": False,
    }
    receipt_path = controller_dir / "receipt.json"
    write_json(receipt_path, receipt)
    return {
        "run_id": run_id,
        "nonce": nonce,
        "run_root": run_root,
        "archive": archive_path,
        "receipt": receipt_path,
        "participant_tree": participant_tree,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario")
    parser.add_argument("--platform", choices=("codex", "workbuddy"), required=True)
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=Path(".artifacts/taohtml-cross-agent-v1/runs"),
    )
    parser.add_argument("--run-id")
    parser.add_argument("--nonce")
    parser.add_argument("--created-at", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        result = prepare(
            args.scenario,
            args.platform,
            args.runs_root.resolve(),
            run_id=args.run_id,
            nonce=args.nonce,
            created_at=args.created_at,
        )
    except (ContractError, OSError, ValueError) as exc:
        print(f"PREPARE_FAILED {exc}", file=sys.stderr)
        return 1
    print(f"PREPARE_OK run_id={result['run_id']} nonce={result['nonce']}")
    print(f"PARTICIPANT_ZIP {result['archive']}")
    print(f"CONTROLLER_RECEIPT {result['receipt']}")
    print("SEND_ONLY participant ZIP; never send controller/receipt.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
