"""承認ゲート（M3/M4）.

ドラフト表示後、ユーザーが approve / edit / reject を選択する。
非対話 (stdin プロトコル / 環境変数) と対話の両方をサポートする。
キルスイッチ（フラグファイル / STOP コマンド）対応。
空入力・EOF・タイムアウトは soft reject（クラッシュしない）。

stdin プロトコル (--stdin):
  1行目: approve / edit / reject / STOP
  edit の場合: 2行目以降に編集文、空行または END で確定

環境変数 (HEARING_APPROVE_MODE=auto):
  HEARING_DECISION = approve / edit / reject
  HEARING_EDIT_TEXT = 編集文（edit時）
  HEARING_EDIT_FILE = 編集文ファイルパス（edit時、TEXTより優先）
"""

import os
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, TextIO

from .killswitch import is_stop_requested, request_stop, resolve_project_root


@dataclass
class GateResult:
    decision: str
    final_text: Optional[str]
    edited: bool
    original_draft: str
    edited_text: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


def _normalize_decision(raw: str) -> str:
    r = raw.strip().lower()
    mapping = {
        "approve": "approve",
        "a": "approve",
        "yes": "approve",
        "y": "approve",
        "ok": "approve",
        "edit": "edit",
        "e": "edit",
        "reject": "reject",
        "r": "reject",
        "no": "reject",
        "n": "reject",
        "skip": "reject",
        "s": "reject",
    }
    if r == "stop":
        return "killed"
    if r not in mapping:
        raise ValueError(f"未知の決定: {raw!r}")
    return mapping[r]


def _killed_result(draft: str) -> GateResult:
    return GateResult(decision="killed", final_text=None, edited=False, original_draft=draft)


def gate_from_stdin(draft: str, stream: Optional[TextIO] = None, project_root=None) -> GateResult:
    root = resolve_project_root(project_root)
    if is_stop_requested(root):
        return _killed_result(draft)

    if stream is None:
        stream = sys.stdin
    lines = stream.read().splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    if idx >= len(lines):
        return GateResult(decision="reject_empty", final_text=None, edited=False, original_draft=draft)
    decision_raw = lines[idx].strip()
    idx += 1
    try:
        norm = _normalize_decision(decision_raw)
    except ValueError:
        return GateResult(decision="reject_empty", final_text=None, edited=False, original_draft=draft)

    if norm == "killed":
        request_stop(root)
        return _killed_result(draft)
    if norm == "approve":
        return GateResult(decision="approve", final_text=draft, edited=False, original_draft=draft)
    if norm == "reject":
        return GateResult(decision="reject", final_text=None, edited=False, original_draft=draft)
    collected = []
    while idx < len(lines):
        if lines[idx].strip() == "" or lines[idx].strip().upper() == "END":
            break
        collected.append(lines[idx])
        idx += 1
    edited = "\n".join(collected).strip()
    if not edited:
        return GateResult(decision="reject_empty", final_text=None, edited=False, original_draft=draft)
    return GateResult(
        decision="edit_approve",
        final_text=edited,
        edited=True,
        original_draft=draft,
        edited_text=edited,
    )


def gate_from_env(draft: str, project_root=None) -> GateResult:
    root = resolve_project_root(project_root)
    if is_stop_requested(root):
        return _killed_result(draft)

    decision_raw = os.environ.get("HEARING_DECISION", "").strip()
    if not decision_raw:
        return GateResult(decision="reject_empty", final_text=None, edited=False, original_draft=draft)
    try:
        norm = _normalize_decision(decision_raw)
    except ValueError:
        return GateResult(decision="reject_empty", final_text=None, edited=False, original_draft=draft)

    if norm == "killed":
        request_stop(root)
        return _killed_result(draft)
    if norm == "approve":
        return GateResult(decision="approve", final_text=draft, edited=False, original_draft=draft)
    if norm == "reject":
        return GateResult(decision="reject", final_text=None, edited=False, original_draft=draft)
    edited = None
    edit_file = os.environ.get("HEARING_EDIT_FILE", "").strip()
    if edit_file:
        try:
            edited = Path(edit_file).read_text(encoding="utf-8").strip()
        except Exception:
            edited = ""
    else:
        edited = os.environ.get("HEARING_EDIT_TEXT", "").strip()
    if not edited:
        return GateResult(decision="reject_empty", final_text=None, edited=False, original_draft=draft)
    return GateResult(
        decision="edit_approve",
        final_text=edited,
        edited=True,
        original_draft=draft,
        edited_text=edited,
    )


def gate_interactive(draft: str, input_func=input, print_func=print, project_root=None, timeout_sec=None) -> GateResult:
    root = resolve_project_root(project_root)
    if is_stop_requested(root):
        return _killed_result(draft)

    print_func("===== ドラフト（承認ゲート） =====")
    print_func(draft)
    print_func("================================")
    print_func("[a]pprove / [e]dit / [r]reject / STOP を入力してください。")

    while True:
        try:
            if timeout_sec is not None and input_func is input:
                import select

                sys.stdout.write("decision> ")
                sys.stdout.flush()
                ready, _, _ = select.select([sys.stdin], [], [], timeout_sec)
                if not ready:
                    return GateResult(decision="reject_timeout", final_text=None, edited=False, original_draft=draft)
                choice_raw = sys.stdin.readline()
                if choice_raw == "":
                    return GateResult(decision="reject_empty", final_text=None, edited=False, original_draft=draft)
                choice = choice_raw.strip()
            else:
                choice = input_func("decision> ").strip()
        except EOFError:
            return GateResult(decision="reject_empty", final_text=None, edited=False, original_draft=draft)

        if choice == "":
            return GateResult(decision="reject_empty", final_text=None, edited=False, original_draft=draft)
        try:
            norm = _normalize_decision(choice)
        except ValueError:
            print_func("a / e / r / STOP のいずれかを入力してください。")
            continue
        if norm == "killed":
            request_stop(root)
            return _killed_result(draft)
        if norm == "approve":
            return GateResult(decision="approve", final_text=draft, edited=False, original_draft=draft)
        if norm == "reject":
            return GateResult(decision="reject", final_text=None, edited=False, original_draft=draft)
        print_func("編集文を入力してください（空行または END で確定）:")
        lines = []
        while True:
            try:
                line = input_func()
            except EOFError:
                break
            if line.strip() == "" or line.strip().upper() == "END":
                break
            lines.append(line)
        edited = "\n".join(lines).strip()
        if not edited:
            print_func("編集文が空です。再度選択してください。")
            continue
        return GateResult(
            decision="edit_approve",
            final_text=edited,
            edited=True,
            original_draft=draft,
            edited_text=edited,
        )


def run_gate(draft: str, mode: Optional[str] = None, project_root=None, timeout_sec=None) -> GateResult:
    root = resolve_project_root(project_root)
    if is_stop_requested(root):
        return _killed_result(draft)

    if mode is None:
        if os.environ.get("HEARING_APPROVE_MODE", "").strip().lower() == "auto":
            mode = "auto"
        elif not sys.stdin.isatty():
            mode = "stdin"
        else:
            mode = "interactive"

    if mode == "stdin":
        return gate_from_stdin(draft, project_root=root)
    if mode == "auto":
        return gate_from_env(draft, project_root=root)
    if mode == "interactive":
        return gate_interactive(draft, project_root=root, timeout_sec=timeout_sec)
    raise ValueError(f"未知の mode: {mode}")
