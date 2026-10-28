#!/usr/bin/env python3
# /// script
# dependencies = ["jsonschema>=4.18,<5"]
# ///
"""驗證逐條判定 JSON，印出可直接發到 PR 的 Markdown。

證據檔從 JSON 所在的資料夾讀取；在該資料夾執行，`--attach` 的相對路徑才對得上。
圖片、影片以 `![檔名](./路徑)` 直接嵌在表格的證據欄，交給 `gh pr comment --attach` 上傳；其他證據在表格下方摺疊內嵌。
附件超過單則 comment 上限時，依條件把表格拆成多則，`--part K` 印第 K 則。
"""
import argparse
import json
import re
import sys
from pathlib import Path

from jsonschema import Draft7Validator, ValidationError

MEDIA_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".mp4", ".mov", ".webm"}
MAX_ATTACH_PER_COMMENT = 50
MAX_COMMENT_CHARS = 65536
TEXT_HEAD_LINES = 60
TEXT_TAIL_LINES = 60
TEXT_MAX_CHARS = 6000


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


def truncate(text):
    """保留頭尾，回傳 (內容, 截斷註記或 None)。"""
    lines = text.splitlines()
    notes = []
    if len(lines) > TEXT_HEAD_LINES + TEXT_TAIL_LINES:
        omitted = len(lines) - TEXT_HEAD_LINES - TEXT_TAIL_LINES
        notes.append(f"共 {len(lines)} 行，省略中間 {omitted} 行")
        lines = lines[:TEXT_HEAD_LINES] + [f"… 省略 {omitted} 行 …"] + lines[-TEXT_TAIL_LINES:]
    text = "\n".join(lines)
    if len(text) > TEXT_MAX_CHARS:
        half = TEXT_MAX_CHARS // 2
        notes.append(f"只留頭尾各 {half} 字")
        text = text[:half] + "\n… 省略 …\n" + text[-half:]
    return text, ("（截斷：" + "；".join(notes) + "）") if notes else None


def embed_text(name, base):
    try:
        raw = (base / name).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise ValueError(f"{name} 不是可上傳的圖片／影片，也不是 UTF-8 文字，無法發布")
    text, note = truncate(raw.rstrip("\n"))
    fence = "`" * max(3, max((len(run) for run in re.findall(r"`+", text)), default=0) + 1)
    summary = name + (" " + note if note else "")
    return [f"<details><summary>{cell(summary)}</summary>", "", fence, text, fence, "", "</details>", ""]


def is_media(name):
    return Path(name).suffix.lower() in MEDIA_SUFFIXES


def evidence_cell(item):
    """證據欄：圖片、影片直接以 `![檔名](./路徑)` 嵌在格子裡；文字證據只寫檔名，內容摺疊在表格下方。"""
    parts = []
    for name in dict.fromkeys(item["evidence"]):
        parts.append(f"![{cell(name)}](./{name})" if is_media(name) else f"{cell(name)}（見下方）")
    return " ".join(parts) or "—"


def split_rows(report):
    """依序把條件分到各則 comment：每則的不重複附件不超過 MAX_ATTACH_PER_COMMENT 個。"""
    parts = [([], [])]  # (該則的條件, 該則要 attach 的路徑)
    for item in report["criteria"]:
        media = [f"./{name}" for name in dict.fromkeys(item["evidence"]) if is_media(name)]
        if len(media) > MAX_ATTACH_PER_COMMENT:
            raise ValueError(f"「{item['criterion']}」有 {len(media)} 個圖片／影片，超過單則上限 {MAX_ATTACH_PER_COMMENT}，請拆成多條條件")
        rows, attach = parts[-1]
        new = [path for path in media if path not in attach]
        if rows and len(attach) + len(new) > MAX_ATTACH_PER_COMMENT:
            parts.append(([], []))
            rows, attach = parts[-1]
            new = media
        rows.append(item)
        attach.extend(new)
    return parts


def render_table(items, base):
    lines = ["| 條件 | 結果 | 帳號 | 看到什麼／原因 | 證據 |", "|---|---|---|---|---|"]
    texts = []
    for item in items:
        observed = item["observed"]
        if item["reason"]:
            observed += "／" + item["reason"]
        columns = [cell(item["criterion"]), cell(item["status"]), cell(item["account"] or "—"), cell(observed), evidence_cell(item)]
        lines.append("| " + " | ".join(columns) + " |")
        texts.extend(name for name in dict.fromkeys(item["evidence"]) if not is_media(name) and name not in texts)
    lines.append("")
    for name in texts:
        lines.extend(embed_text(name, base))
    return lines


def render_footer(report):
    lines = []
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
        lines.extend([f"在 staging 建了 {report['stagingRecords']} 筆資料", ""])
    if report["criteriaSource"] == "inferred":
        lines.extend(["issue 沒有 ## Acceptance criteria，以下條件由 agent 從內文推出", ""])
    return lines


def render(report, base, part):
    """回傳 (第 part 則的 Markdown, 該則要 --attach 的路徑, 總則數)。"""
    if report["status"] == "unverifiable":
        parts = [([], [])]
    else:
        parts = split_rows(report)
    total = len(parts)
    if not 1 <= part <= total:
        raise ValueError(f"--part 要在 1～{total} 之間")
    items, media = parts[part - 1]
    title = "## 瀏覽器驗收" + (f"（{part}/{total}）" if total > 1 else "")
    lines = [title, "", f"驗收 commit：`{report['sha']}`", ""]
    if report["status"] == "unverifiable":
        lines.extend([f"驗不了：{report['unverifiableReason']}", ""])
    else:
        lines.extend(render_table(items, base))
    if part == 1:
        lines.extend(render_footer(report))
    text = "\n".join(lines).rstrip() + "\n"
    # 內嵌文字與 observed 可能帶執行主機的路徑：證據資料夾換成 `.`，家目錄換成 `~`。
    for local, public in ((report["evidenceDir"].rstrip("/"), "."), (str(base), "."), (str(Path.home()), "~")):
        text = text.replace(local, public)
    return text, media, total


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("report", type=Path, help="逐條判定 JSON 檔，放在證據資料夾裡")
    parser.add_argument("--part", type=int, default=1, help=f"印第幾則 comment（附件超過 {MAX_ATTACH_PER_COMMENT} 個才有第 2 則以後）")
    parser.add_argument("--attach-list", action="store_true", help="改印該則要 --attach 的路徑，一行一個 ./路徑")
    args = parser.parse_args()
    try:
        report = json.loads(args.report.read_text())
        validate(report)
        text, media, total = render(report, args.report.resolve().parent, args.part)
    except ValidationError as error:
        parser.exit(1, f"驗收結果不合格：{error.message}\n")
    except (ValueError, OSError) as error:
        parser.exit(1, f"驗收結果不合格：{error}\n")
    if total > 1:
        print(f"共 {total} 則 comment，依序用 --part 1～{total} 產生", file=sys.stderr)
    if len(text) > MAX_COMMENT_CHARS:
        print(f"第 {args.part} 則 {len(text)} 字，超過 GitHub comment 上限 {MAX_COMMENT_CHARS}", file=sys.stderr)
    if args.attach_list:
        print("".join(path + "\n" for path in media), end="")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
