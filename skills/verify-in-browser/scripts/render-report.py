#!/usr/bin/env python3
# /// script
# dependencies = ["jsonschema>=4.18,<5"]
# ///
"""驗證逐條判定 JSON，印出與 runner 同欄位的 Markdown。"""
import argparse
import json
from pathlib import Path

from jsonschema import Draft7Validator, ValidationError


def validate(report):
    schema = json.loads((Path(__file__).resolve().parents[1] / "result.schema.json").read_text())
    Draft7Validator(schema).validate(report)
    if report["status"] == "unverifiable":
        if report["criteria"] or not report["unverifiableReason"]:
            raise ValueError("unverifiable 必須寫原因且 criteria 為空")
    elif report["unverifiableReason"] is not None or not report["criteria"]:
        raise ValueError("verified 必須有 criteria，unverifiableReason 為 null")
    if report["status"] == "verified" and report["criteriaSource"] == "inferred" and not 1 <= len(report["criteria"]) <= 3:
        raise ValueError("inferred 必須有 1～3 條條件")
    for item in report["criteria"]:
        if item["status"] == "passed" and (not item["evidence"] or item["reason"] is not None):
            raise ValueError("passed 必須有證據，reason 為 null")
        if item["status"] in ("failed", "skipped") and not item["reason"]:
            raise ValueError("failed、skipped 必須寫 reason")


def cell(value):
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("|", "&#124;").replace("\r\n", "<br>").replace("\n", "<br>").replace("\r", "<br>")


def render(report):
    lines = ["## 瀏覽器驗收", "", f"證據：{report['evidenceDir']}（runner 主機本機，不在 git）", ""]
    if report["status"] == "unverifiable":
        lines.extend([f"驗不了：{report['unverifiableReason']}", ""])
    else:
        lines.extend(["| 條件 | 結果 | 帳號 | 看到什麼／原因 | 證據 |", "|---|---|---|---|---|"])
        for item in report["criteria"]:
            observed = item["observed"]
            if item["reason"]:
                observed += "／" + item["reason"]
            columns = [item["criterion"], item["status"], item["account"] or "—", observed, "、".join(item["evidence"]) or "—"]
            lines.append("| " + " | ".join(cell(column) for column in columns) + " |")
        lines.append("")
    related = [error for error in report["consoleErrors"] if error["related"] != "no"]
    unrelated = len(report["consoleErrors"]) - len(related)
    if related:
        lines.append("console error：")
        lines.extend("- " + cell(error["text"]) for error in related)
    if unrelated:
        lines.append(f"另有 {unrelated} 則判定與本次 diff 無關")
    if related or unrelated:
        lines.append("")
    model = "判定 model：" + report["verifier"]["model"]
    if report["verifier"]["same_model"]:
        model += "（與實作同一個 model）"
    lines.extend([model, ""])
    if report["stagingRecords"]:
        lines.extend([f"在 staging 建了 {report['stagingRecords']} 筆資料，清單在 {report['evidenceDir']}/state.json", ""])
    if report["criteriaSource"] == "inferred":
        lines.extend(["issue 沒有 ## Acceptance criteria，以下條件由 agent 從內文推出", ""])
    return "\n".join(lines).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="逐條判定 JSON 檔")
    args = parser.parse_args()
    try:
        report = json.loads(args.report.read_text())
        validate(report)
        print(render(report), end="")
    except ValidationError as error:
        parser.exit(1, f"驗收結果不合格：{error.message}\n")
    except (ValueError, OSError) as error:
        parser.exit(1, f"驗收結果不合格：{error}\n")


if __name__ == "__main__":
    main()
