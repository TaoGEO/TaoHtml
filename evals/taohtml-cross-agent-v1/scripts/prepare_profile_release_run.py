#!/usr/bin/env python3
"""Create one isolated, answer-free Workflow Profile release run."""

from __future__ import annotations

import argparse
import hashlib
import secrets
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from blackbox_contract import (
    ContractError,
    deterministic_zip_tree,
    file_hashes,
    parse_utc,
    safe_identifier,
    safe_nonce,
    sha256_file,
    tree_sha256,
    utc_now,
    write_json,
)
from profile_release_contract import (
    EVIDENCE_CONTRACT_VERSION,
    RECEIPT_VERSION,
    REQUIRED_OUTPUTS,
    RUN_CONTRACT_VERSION,
    SUBMISSION_CONTRACT_VERSION,
    answer_sha256,
    assert_answer_free_package,
    release_toolchain_sha256,
    scenario_by_id,
    scenario_request_path,
)


def generated_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dt%H%M%sz").lower()
    return f"profile-{stamp}-{secrets.token_hex(4)}"


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


def instructions(run_id: str, nonce: str, output_directory: str) -> str:
    return f"""# TaoHtml 九路径轻量发布验收说明

这是一次全新、隔离、无答案包的 Workflow Profile Golden Path 运行。只读取本包中的 `request.md`、`run.json`、本说明和当前平台已安装的 TaoHtml Skill；不得读取父目录、仓库、控制端矩阵、答案、评分规则、旧产物或网络。若无法遵守，立即停止。

先核对 `run.json` 的输入哈希和唯一输出目录。不得覆盖、清理或复用任何输出。根据原始业务目标选择恰好一个 primary Profile；目标确实歧义时才显示完整九项并只问一个业务目标问题。复用用户已经明确的入口、使用模式、篇幅、视觉和动效，不要重复询问。

本矩阵走 TaoHtml 默认 Direct HTML 路线。不要创建 Report IR、Compiler Manifest、normalized IR 或 source map；Profile 选择不构成 Report IR 工程授权。Report IR/Compiler 即使随安装包可见，在 v0.5.0 本矩阵中仍是 experimental/pilot-only。

把 Profile 要求的场景特有决策写进同一份完整 Report Design Brief。每项决策使用三级 Markdown 小节，并分别写明非占位的“实际决策”“事实依据”“状态边界”；标签由所选 Profile 的现行定义决定，不要从测试包猜答案。完整简报确认只是用户确认，不是 Production Authorization。

使用现行 `gates/production-state.json` v1.3 合同，并让 `design_brief` 绑定当前简报、确认引用和 checker 生成的 `design_decisions_sha256`。不得创建 `production-authorization.json`。保存第一个正式 `build/index.html` 前暂停，由控制端运行 `check_production_authorization.py --action formal-html` 并记录 HTML 尚不存在；生成后，在浏览器 QA 前再次暂停并由控制端运行 `--action browser-qa`。只有控制端三视口浏览器记录 PASS 后，才在 Handoff 交付前运行 `--action deliver-formal-html`。不要用参与者自报时间、引用或 gate sequence 代替这些控制端记录。

控制端另行保存真实 conversation turn trace、三视口浏览器原始报告与截图、人工视觉验收；`profile-evidence.json` 只是参与者补充说明，不能证明实际提问、目录展示、用户答复或门禁顺序。参与者不得宣称任何控制端层已经 PASS。

唯一输出目录为 `{output_directory}`。至少交付：

{chr(10).join(f'- `{item}`' for item in REQUIRED_OUTPUTS)}

`profile-evidence.json` 使用合同 `{EVIDENCE_CONTRACT_VERSION}`，只记录：运行身份；所选 primary Profile 的三字段对象与非空选择依据；当前设计简报路径/哈希；证据边界 id/status；以及 `direct_html`、`taohtml-runtime-1` 和 Handoff 路径/哈希。不要把问题、目录展示、用户答复、确认时间或 checker 执行顺序自报成控制端证据。

`submission.json` 使用下面的最小绑定；`artifacts` 必须列出输出目录内除 `submission.json` 自身外的每个文件及 SHA-256：

```json
{{
  "submission_contract_version": "{SUBMISSION_CONTRACT_VERSION}",
  "run_id": "{run_id}",
  "nonce": "{nonce}",
  "case_id": "与 run.json 一致的不透明 case id",
  "participant_claimed_status": "PASS | FAIL | PENDING（仅审计，控制端不会据此判 PASS）",
  "artifacts": {{"design-brief.md": "sha256", "...": "sha256"}}
}}
```

完成后返回整个包根目录，保留原始输入、`run.json` 和唯一输出目录。缺少浏览器结果或人工结果时，发布验收必须保持 PENDING。
"""


def prepare(
    scenario_id: str,
    runs_root: Path,
    *,
    runner_label: str = "unspecified",
    run_id: str | None = None,
    nonce: str | None = None,
    created_at: str | None = None,
) -> dict[str, Path | str]:
    scenario = scenario_by_id(scenario_id)
    run_id = safe_identifier(run_id or generated_run_id(), "run_id")
    nonce = safe_nonce(nonce or secrets.token_hex(16))
    case_id = "case-" + hashlib.sha256(f"{run_id}:{nonce}".encode()).hexdigest()[:20]
    created_at = created_at or utc_now()
    parse_utc(created_at, "created_at")
    if not isinstance(runner_label, str) or not runner_label.strip():
        raise ContractError("runner_label must be non-empty")

    runs_root.mkdir(parents=True, exist_ok=True)
    run_root = runs_root / run_id
    if run_root.exists():
        raise ContractError(f"run directory already exists: {run_root}")
    participant_tree = run_root / "participant-tree"
    controller_dir = run_root / "controller"
    participant_tree.mkdir(parents=True)
    controller_dir.mkdir()

    (participant_tree / "request.md").write_bytes(
        scenario_request_path(scenario).read_bytes()
    )
    output_directory = f"submission/{run_id}"
    (participant_tree / "RUN_INSTRUCTIONS.md").write_text(
        instructions(run_id, nonce, output_directory), encoding="utf-8"
    )
    inputs = file_hashes(participant_tree)
    input_tree = tree_sha256(inputs)
    manifest = {
        "run_contract_version": RUN_CONTRACT_VERSION,
        "run_id": run_id,
        "nonce": nonce,
        "case_id": case_id,
        "runner_label": runner_label,
        "created_at": created_at,
        "request": "request.md",
        "allowed_external_input": "installed TaoHtml Skill only",
        "output_directory": output_directory,
        "required_outputs": list(REQUIRED_OUTPUTS),
        "input_files": inputs,
        "input_tree_sha256": input_tree,
    }
    write_json(participant_tree / "run.json", manifest)
    assert_answer_free_package(participant_tree, scenario)

    archive = run_root / f"profile-release-{run_id}.zip"
    deterministic_zip_tree(participant_tree, archive)
    from profile_release_contract import REPOSITORY_ROOT

    receipt = {
        "receipt_version": RECEIPT_VERSION,
        "run_id": run_id,
        "nonce": nonce,
        "scenario_id": scenario_id,
        "case_id": case_id,
        "runner_label": runner_label,
        "created_at": created_at,
        "output_directory": output_directory,
        "required_outputs": list(REQUIRED_OUTPUTS),
        "input_files": inputs,
        "input_tree_sha256": input_tree,
        "run_manifest_sha256": sha256_file(participant_tree / "run.json"),
        "participant_zip_sha256": sha256_file(archive),
        "controller_answer_sha256": answer_sha256(scenario),
        "release_toolchain_sha256": release_toolchain_sha256(),
        "result_hmac_key": secrets.token_hex(32),
        "source_commit": repository_commit(REPOSITORY_ROOT),
        "participant_contents": sorted([*inputs, "run.json"]),
        "controller_answer_embedded": False,
        "expected_profile_embedded": False,
    }
    receipt_path = controller_dir / "receipt.json"
    write_json(receipt_path, receipt)
    return {
        "run_id": run_id,
        "run_root": run_root,
        "archive": archive,
        "receipt": receipt_path,
        "participant_tree": participant_tree,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario")
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=Path(".artifacts/taohtml-cross-agent-v1/profile-release-runs"),
    )
    parser.add_argument("--runner-label", default="unspecified")
    parser.add_argument("--run-id")
    parser.add_argument("--nonce")
    parser.add_argument("--created-at", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        result = prepare(
            args.scenario,
            args.runs_root.resolve(),
            runner_label=args.runner_label,
            run_id=args.run_id,
            nonce=args.nonce,
            created_at=args.created_at,
        )
    except (ContractError, OSError, ValueError) as exc:
        print(f"PROFILE_RELEASE_PREPARE_FAILED {exc}", file=sys.stderr)
        return 1
    print(f"PROFILE_RELEASE_PREPARE_OK run_id={result['run_id']}")
    print(f"PARTICIPANT_ZIP {result['archive']}")
    print(f"CONTROLLER_RECEIPT {result['receipt']}")
    print("SEND_ONLY participant ZIP; never send controller/receipt.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
