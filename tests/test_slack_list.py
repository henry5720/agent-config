import importlib.machinery
import importlib.util
import io
import json
import os
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch


SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "slack-list" / "scripts" / "slack-list"
loader = importlib.machinery.SourceFileLoader("slack_list", str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
slack_list = importlib.util.module_from_spec(spec)
loader.exec_module(slack_list)

# setUp 會把這兩支換成假的（見裡面的說明），要測它們本身得先留一份真的。
REAL_COLUMN_INDEX = slack_list.column_index
REAL_TEXT_COLUMNS = slack_list.text_columns


class SlackListTest(unittest.TestCase):
    def setUp(self):
        # 這兩支會打 files.info 拿欄位定義。不擋掉的話整份測試會依賴網路和一份
        # 真的 .env —— 實測 cmd_todo 一次就送出兩個 request。
        # 回傳值跟「拿不到 schema」的退路一致：欄位名退回內部 key，不截斷。
        for name, value in (("column_index", ({}, {})), ("text_columns", set())):
            patcher = patch.object(slack_list, name, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)
        slack_list._COLUMN_INDEX = None
        slack_list._TEXT_COLUMNS = None

    def add_schema(self):
        return {
            slack_list.COL_TITLE: {"id": "title-col"},
            slack_list.COL_DESCRIPTION: {"id": "description-col"},
            slack_list.COL_ASSIGNEE: {"id": "assignee-col"},
            slack_list.COL_DUE: {"id": "due-col"},
            slack_list.COL_COMPLETED: {"id": "completed-col"},
            slack_list.COL_STATUS: {
                "id": "status-col",
                "options": {"choices": [{
                    "label": slack_list.STATUS_READY,
                    "value": "ready-opt",
                }]},
            },
        }

    @patch.object(slack_list, "fetch_all")
    def test_assigned_matches_exact_user_id_and_keyword(self, fetch_all):
        fetch_all.return_value = [
            {"id": "RecA", "fields": [
                {"key": "todo_assignee", "user": ["U123", "U999"]},
                {"key": "name", "text": "庫存修正"},
            ]},
            {"id": "RecB", "fields": [
                {"key": "todo_assignee", "user": ["U1234"]},
                {"key": "name", "text": "庫存盤點"},
            ]},
            {"id": "RecC", "fields": [
                {"key": "todo_assignee", "user": ["U123"]},
                {"key": "name", "text": "帳務修正"},
            ]},
        ]

        output = io.StringIO()
        errors = io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            slack_list.cmd_assigned(["U123", "庫存"])

        self.assertIn("[RecA]", output.getvalue())
        self.assertNotIn("RecB", output.getvalue())
        self.assertNotIn("RecC", output.getvalue())
        self.assertIn("1 列未完成（全表 3 列", errors.getvalue())

    def test_assigned_rejects_non_slack_user_id(self):
        with self.assertRaises(SystemExit), patch.object(
            slack_list, "die", side_effect=SystemExit
        ):
            slack_list.cmd_assigned(["henry"])

    @patch.object(slack_list, "print_assigned")
    @patch.object(slack_list, "my_user_id", return_value="U123")
    def test_mine_uses_local_user_id(self, my_user_id, print_assigned):
        slack_list.cmd_mine(["庫存"])

        my_user_id.assert_called_once_with()
        print_assigned.assert_called_once_with("U123", "庫存", False, False)

    @patch.object(slack_list, "print_assigned")
    @patch.object(slack_list, "my_user_id", return_value="U123")
    def test_mine_reads_all_as_a_flag_not_as_the_keyword(self, my_user_id, print_assigned):
        # 舊版直接拿 sys.argv[2] 當關鍵字，`mine --all 庫存` 會去比對「--all」這個字
        slack_list.cmd_mine(["--all", "庫存"])
        print_assigned.assert_called_once_with("U123", "庫存", True, False)

    def test_issue_mode_accepts_manual_and_rejects_other_values(self):
        with patch.object(slack_list, "load_env"), patch.dict(
            os.environ, {"WORK_HELPER_ISSUE_MODE": "manual"}
        ):
            self.assertEqual(slack_list.issue_mode(), "manual")

        with patch.object(slack_list, "load_env"), patch.dict(
            os.environ, {"WORK_HELPER_ISSUE_MODE": "automatic"}
        ), self.assertRaises(SystemExit), patch.object(
            slack_list, "die", side_effect=SystemExit
        ):
            slack_list.issue_mode()

    def test_load_env_reads_the_user_config_dir(self):
        # skill 會被 sync 到好幾個 target，.env 不能跟著 script 放，固定在 ~/.config。
        with tempfile.TemporaryDirectory() as home:
            env_file = Path(home) / ".config" / "slack-list" / ".env"
            env_file.parent.mkdir(parents=True)
            env_file.write_text("SLACK_LIST_ID=F123\n", encoding="utf-8")
            with patch.dict(os.environ, {"HOME": home}, clear=False):
                os.environ.pop("SLACK_LIST_ID", None)
                slack_list.load_env()
                self.assertEqual(os.environ["SLACK_LIST_ID"], "F123")

    def test_deep_link_takes_workspace_and_team_from_env(self):
        with patch.object(slack_list, "load_env"), patch.dict(os.environ, {
            "SLACK_WORKSPACE_URL": "https://example.slack.com/",
            "SLACK_TEAM_ID": "T123",
        }):
            self.assertEqual(
                slack_list.deep_link("F1", "Rec1"),
                "https://example.slack.com/lists/T123/F1?record_id=Rec1",
            )

    def test_deep_link_dies_without_workspace_config(self):
        with patch.object(slack_list, "load_env"), patch.dict(os.environ, {"SLACK_TEAM_ID": "T123"}), \
                self.assertRaises(SystemExit), patch.object(slack_list, "die", side_effect=SystemExit):
            os.environ.pop("SLACK_WORKSPACE_URL", None)
            slack_list.deep_link("F1", "Rec1")

    def test_record_id_for_thread_rejects_other_channel(self):
        with self.assertRaises(SystemExit), patch.object(slack_list, "die", side_effect=SystemExit):
            slack_list.record_id_for_thread("token", "F123", "C999", "1.2")

    @patch.object(slack_list, "item_threads")
    def test_record_id_for_thread_matches_parent_timestamp(self, item_threads):
        item_threads.return_value = {
            "RecA": {"ts": "1.1"},
            "RecB": {"ts": "2.2"},
        }
        self.assertEqual(
            slack_list.record_id_for_thread("token", "F123", "C123", "2.2"),
            "RecB",
        )

    @patch.object(slack_list, "thread_messages")
    @patch.object(slack_list, "fetch_all")
    @patch.object(slack_list, "record_id_for_thread")
    @patch.object(slack_list, "config")
    def test_context_outputs_record_and_non_parent_messages(
        self, config, record_id_for_thread, fetch_all, thread_messages
    ):
        config.return_value = ("token", "F123")
        record_id_for_thread.return_value = "RecA"
        fetch_all.return_value = [{
            "id": "RecA",
            "fields": [{"key": "name", "text": "測試需求"}],
        }]
        thread_messages.return_value = [
            {"subtype": "list_record_comment", "ts": "1.1"},
            {"ts": "1.2", "user": "U1", "text": "為什麼？"},
        ]

        output = io.StringIO()
        with redirect_stdout(output):
            slack_list.cmd_context(["--channel", "C123", "--thread-ts", "1.1"])

        body = json.loads(output.getvalue())
        self.assertEqual(body["record_id"], "RecA")
        self.assertEqual(body["record"]["name"], "測試需求")
        self.assertEqual(body["messages"], [{
            "ts": "1.2", "user": "U1", "bot_id": "", "text": "為什麼？", "files": []
        }])

    @patch.object(slack_list, "post_record_note", return_value=True)
    @patch.object(slack_list, "api")
    @patch.object(slack_list, "fetch_all", return_value=[])
    @patch.object(slack_list, "schema")
    @patch.object(slack_list, "config", return_value=("token", "F123"))
    def test_add_creates_title_description_due_and_self_assignment_atomically(
        self, config, schema, fetch_all, api, post_record_note
    ):
        schema.return_value = self.add_schema()
        api.return_value = {"item": {"id": "RecNew"}}

        output = io.StringIO()
        with patch.object(slack_list, "source_permalink", return_value="https://source"), \
                redirect_stdout(output):
            slack_list.cmd_add([
                "--title", "庫存匯出缺少批號",
                "--description", "匯出的 Excel 沒有批號欄",
                "--due", "2026-08-21",
                "--assignee", "U123",
                "--requested-by", "U123",
                "--report-to", "U999",
                "--source-channel", "C999",
                "--source-thread", "1.2",
            ])

        method, payload, token = api.call_args.args
        self.assertEqual(method, "slackLists.items.create")
        self.assertEqual(token, "token")
        self.assertEqual(payload["list_id"], "F123")
        by_column = {f["column_id"]: f for f in payload["initial_fields"]}
        self.assertEqual(by_column["assignee-col"]["user"], ["U123"])
        self.assertEqual(by_column["due-col"]["date"], ["2026-08-21"])
        self.assertEqual(
            by_column["title-col"]["rich_text"][0]["elements"][0]["elements"][0]["text"],
            "庫存匯出缺少批號",
        )
        self.assertEqual(
            by_column["description-col"]["rich_text"][0]["elements"][0]["elements"][0]["text"],
            "匯出的 Excel 沒有批號欄",
        )
        post_record_note.assert_called_once_with(
            "token", "F123", "RecNew", "U123", "U999", "https://source"
        )
        self.assertIn("已新增：庫存匯出缺少批號", output.getvalue())

    @patch.object(slack_list, "post_duplicate_note", return_value=True)
    @patch.object(slack_list, "api")
    @patch.object(slack_list, "fetch_all")
    @patch.object(slack_list, "schema")
    @patch.object(slack_list, "config", return_value=("token", "F123"))
    def test_add_appends_sender_to_active_exact_duplicate(
        self, config, schema, fetch_all, api, post_duplicate_note
    ):
        schema.return_value = self.add_schema()
        fetch_all.return_value = [{
            "id": "RecOld",
            "fields": [
                {"column_id": "title-col", "text": "  庫存  匯出缺少批號  "},
                {"column_id": "assignee-col", "user": ["U999"]},
                {"column_id": "completed-col", "checkbox": False},
                {"column_id": "status-col", "select": ["doing-opt"]},
            ],
        }]

        output = io.StringIO()
        with patch.object(slack_list, "source_permalink", return_value="https://source"), \
                redirect_stdout(output):
            slack_list.cmd_add([
                "--title", "庫存 匯出缺少批號",
                "--assignee", "U123",
                "--requested-by", "U123",
                "--report-to", "U456",
                "--source-channel", "C999",
                "--source-thread", "1.2",
            ])

        api.assert_called_once_with("slackLists.items.update", {
            "list_id": "F123",
            "id": "RecOld",
            "cells": [{
                "row_id": "RecOld",
                "column_id": "assignee-col",
                "user": ["U999", "U123"],
            }],
        }, "token")
        post_duplicate_note.assert_called_once_with(
            "token", "F123", "RecOld", "U123", "https://source"
        )
        self.assertIn("已加入既有待辦", output.getvalue())
        self.assertIn("未變更原回報對象", output.getvalue())

    @patch.object(slack_list, "post_duplicate_note")
    @patch.object(slack_list, "api")
    @patch.object(slack_list, "fetch_all")
    @patch.object(slack_list, "schema")
    @patch.object(slack_list, "config", return_value=("token", "F123"))
    def test_add_does_not_assign_duplicate_awaiting_pm_review(
        self, config, schema, fetch_all, api, post_duplicate_note
    ):
        schema.return_value = self.add_schema()
        fetch_all.return_value = [{
            "id": "RecReady",
            "fields": [
                {"column_id": "title-col", "text": "匯出缺欄位"},
                {"column_id": "assignee-col", "user": ["U999"]},
                {"column_id": "completed-col", "checkbox": False},
                {"column_id": "status-col", "select": ["ready-opt"]},
            ],
        }]

        output = io.StringIO()
        with patch.object(slack_list, "source_permalink", return_value="https://source"), \
                redirect_stdout(output):
            slack_list.cmd_add([
                "--title", "匯出缺欄位",
                "--assignee", "U123",
                "--requested-by", "U123",
                "--source-channel", "C999",
                "--source-thread", "1.2",
            ])

        api.assert_not_called()
        post_duplicate_note.assert_not_called()
        self.assertIn("正在 PM確認中", output.getvalue())
        self.assertIn("--force", output.getvalue())

    @patch.object(slack_list, "api")
    @patch.object(slack_list, "fetch_all", return_value=[])
    @patch.object(slack_list, "schema")
    @patch.object(slack_list, "config", return_value=("token", "F123"))
    def test_add_keeps_created_row_when_origin_note_fails(
        self, config, schema, fetch_all, api
    ):
        schema.return_value = self.add_schema()
        api.return_value = {"item": {"id": "RecNew"}}

        output = io.StringIO()
        with patch.object(slack_list, "source_permalink", return_value="https://source"), \
                patch.object(slack_list, "post_record_note", return_value=False), \
                redirect_stdout(output):
            slack_list.cmd_add([
                "--title", "匯出缺欄位",
                "--assignee", "U123",
                "--requested-by", "U123",
                "--source-channel", "C999",
                "--source-thread", "1.2",
            ])

        self.assertIn("待辦已建立", output.getvalue())
        self.assertIn("來源／回報設定失敗", output.getvalue())

    def test_add_rejects_invalid_date(self):
        with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()) as err:
            slack_list.cmd_add([
                "--title", "匯出缺欄位",
                "--due", "明天",
                "--assignee", "U123",
                "--requested-by", "U123",
                "--source-channel", "C999",
                "--source-thread", "1.2",
            ])
        self.assertIn("YYYY-MM-DD", err.getvalue())

    @patch.object(slack_list, "api")
    @patch.object(slack_list, "fetch_all")
    @patch.object(slack_list, "item_threads", return_value={"RecA": {"ts": "1.2"}})
    @patch.object(slack_list, "schema")
    @patch.object(slack_list, "config", return_value=("token", "F123"))
    def test_add_from_item_thread_requires_explicit_force(
        self, config, schema, item_threads, fetch_all, api
    ):
        schema.return_value = self.add_schema()
        output = io.StringIO()
        with redirect_stdout(output):
            slack_list.cmd_add([
                "--title", "另一個匯出問題",
                "--assignee", "U123",
                "--requested-by", "U123",
                "--source-channel", "C123",
                "--source-thread", "1.2",
            ])

        fetch_all.assert_not_called()
        api.assert_not_called()
        self.assertIn("既有待辦列", output.getvalue())
        self.assertIn("--force", output.getvalue())

    def test_reporter_resolution_uses_latest_own_setting(self):
        rec = {"created_by": "UBOT"}
        messages = [
            {"user": "UBOT", "bot_id": "B1", "text":
             "[work-helper:origin:v1 sender=U123]\n"
             "[work-helper:reporter:v1 user=U123]", "blocks": [
                 {"block_id": "work_helper_origin_v1_U123"},
                 {"block_id": "work_helper_reporter_v1_user_U123"},
             ]},
            {"user": "U999", "text": "[work-helper:reporter:v1 user=U999]",
             "blocks": [{"block_id": "work_helper_reporter_v1_user_U999"}]},
            {"user": "UBOT", "bot_id": "B1", "text":
             "[work-helper:reporter:v1 user=U456]", "blocks": [
                 {"block_id": "work_helper_reporter_v1_user_U456"},
             ]},
        ]

        self.assertEqual(
            slack_list.record_reporter(rec, messages, "UBOT"), ("U456", True)
        )

    def test_reporter_resolution_can_disable_notifications(self):
        rec = {"created_by": "U123"}
        messages = [{
            "user": "UBOT", "bot_id": "B1",
            "text": "[work-helper:reporter:v1 none]",
            "blocks": [{"block_id": "work_helper_reporter_v1_none"}],
        }]
        self.assertEqual(
            slack_list.record_reporter(rec, messages, "UBOT"), ("", True)
        )

    def test_reporter_default_restores_bot_origin(self):
        rec = {"created_by": "UBOT"}
        messages = [
            {"user": "UBOT", "bot_id": "B1", "text":
             "[work-helper:origin:v1 sender=U123]\n"
             "[work-helper:reporter:v1 user=U123]", "blocks": [
                 {"block_id": "work_helper_origin_v1_U123"},
                 {"block_id": "work_helper_reporter_v1_user_U123"},
             ]},
            {"user": "UBOT", "bot_id": "B1", "text":
             "[work-helper:reporter:v1 user=U456]", "blocks": [
                 {"block_id": "work_helper_reporter_v1_user_U456"},
             ]},
            {"user": "UBOT", "bot_id": "B1", "text":
             "[work-helper:reporter:v1 default]", "blocks": [
                 {"block_id": "work_helper_reporter_v1_default"},
             ]},
        ]
        self.assertEqual(
            slack_list.record_reporter(rec, messages, "UBOT"), ("U123", True)
        )

    def test_reporter_resolution_falls_back_by_creator_kind(self):
        self.assertEqual(
            slack_list.record_reporter({"created_by": "U123"}, [], "UBOT"),
            ("U123", True),
        )
        self.assertEqual(
            slack_list.record_reporter({"created_by": "UBOT"}, [], "UBOT"),
            ("", False),
        )

    def test_reporter_resolution_ignores_marker_text_relayed_by_bot(self):
        rec = {"created_by": "U123"}
        messages = [{
            "user": "UBOT", "bot_id": "B1",
            "text": "進度：[work-helper:reporter:v1 none]",
        }]
        self.assertEqual(
            slack_list.record_reporter(rec, messages, "UBOT"), ("U123", True)
        )

    @patch.object(slack_list, "api")
    @patch.object(slack_list, "item_thread_ts", return_value="1.2")
    @patch.object(slack_list, "config", return_value=("token", "F123"))
    def test_reporter_command_posts_canonical_visible_setting(
        self, config, item_thread_ts, api
    ):
        slack_list.cmd_reporter(["RecA", "--user", "U456"])

        method, payload, token = api.call_args.args
        self.assertEqual(method, "chat.postMessage")
        self.assertEqual(token, "token")
        self.assertIn("[work-helper:reporter:v1 user=U456]", payload["text"])
        self.assertIn("<@U456>", payload["text"])
        self.assertEqual(
            payload["blocks"][0]["block_id"],
            "work_helper_reporter_v1_user_U456",
        )

    @patch.object(slack_list, "api")
    @patch.object(slack_list, "bot_user_id", return_value="UBOT")
    @patch.object(slack_list, "thread_messages", return_value=[])
    @patch.object(slack_list, "item_thread_ts", return_value="1.2")
    @patch.object(slack_list, "record")
    @patch.object(slack_list, "schema")
    @patch.object(slack_list, "config", return_value=("token", "F123"))
    def test_ready_quiet_does_not_include_reporter_mention(
        self, config, schema, record, item_thread_ts, thread_messages,
        bot_user_id, api
    ):
        schema.return_value = {
            slack_list.COL_TITLE: {"id": "title-col"},
            slack_list.COL_STATUS: {
                "id": "status-col",
                "options": {"choices": [{
                    "label": slack_list.STATUS_READY,
                    "value": "ready-opt",
                }]},
            },
            slack_list.COL_FILE: {"id": "file-col"},
        }
        record.return_value = {
            "created_by": "U123",
            "fields": [{"column_id": "title-col", "text": "庫存修正"}],
        }

        slack_list.cmd_ready([
            "RecA", "--changed", "修正匯出欄位",
            "--verify", "匯出後確認批號存在", "--no-url", "--quiet",
        ])

        post_payload = api.call_args_list[0].args[1]
        self.assertNotIn("<@U123>", json.dumps(post_payload, ensure_ascii=False))

    @patch.object(slack_list.urllib.request, "urlopen")
    def test_create_transport_failure_warns_not_to_retry(self, urlopen):
        urlopen.side_effect = slack_list.urllib.error.URLError("timeout")
        with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()) as err:
            slack_list.api("slackLists.items.create", {"list_id": "F123"}, "token")
        self.assertIn("建立結果不明", err.getvalue())
        self.assertIn("勿直接重試", err.getvalue())

    @patch.object(slack_list.urllib.request, "urlopen")
    def test_create_truncated_response_warns_not_to_retry(self, urlopen):
        urlopen.return_value.__enter__.return_value.read.return_value = b"{"
        with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()) as err:
            slack_list.api("slackLists.items.create", {"list_id": "F123"}, "token")
        self.assertIn("建立結果不明", err.getvalue())
        self.assertIn("勿直接重試", err.getvalue())

    @patch.object(slack_list.urllib.request, "urlopen")
    def test_api_get_truncated_response_fails_cleanly(self, urlopen):
        urlopen.return_value.__enter__.return_value.read.return_value = b"{"
        with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()) as err:
            slack_list.api_get("conversations.history", {"channel": "C123"}, "token")
        self.assertIn("Slack 回應無法讀取", err.getvalue())

    @patch.object(slack_list, "item_threads", side_effect=SystemExit)
    def test_post_note_turns_thread_lookup_failure_into_partial_success(self, item_threads):
        self.assertFalse(slack_list.post_note_with_retry(
            "token", "F123", "RecA", "來源註記"
        ))

    def test_github_issue_urls_include_fingerprint_and_title(self):
        search, create = slack_list.github_issue_urls(
            "ShuChenAI/teamsync-frontend", "Rec0ABC", "庫存修正"
        )
        self.assertIn("Rec0ABC", search)
        self.assertIn("title=", create)
        self.assertIn("ShuChenAI/teamsync-frontend", create)

    def test_github_issue_urls_reject_invalid_repo(self):
        with self.assertRaises(SystemExit), patch.object(slack_list, "die", side_effect=SystemExit):
            slack_list.github_issue_urls("https://github.com/x/y", "RecA", "title")

    @patch.object(slack_list, "api")
    @patch.object(slack_list, "upload_md")
    @patch.object(slack_list, "github_issue_urls")
    @patch.object(slack_list, "item_thread_ts")
    @patch.object(slack_list, "record")
    @patch.object(slack_list, "schema")
    @patch.object(slack_list, "config")
    def test_draft_uploads_markdown_and_posts_manual_issue_links(
        self, config, schema, record, item_thread_ts, github_issue_urls,
        upload_md, api
    ):
        config.return_value = ("token", "F123")
        schema.return_value = {slack_list.COL_TITLE: {"id": "title-col"}}
        record.return_value = {
            "fields": [{"column_id": "title-col", "text": "庫存修正"}]
        }
        item_thread_ts.return_value = "1.2"
        github_issue_urls.return_value = ("https://search", "https://create")

        slack_list.cmd_draft([
            "RecA", "--md", "/tmp/draft.md",
            "--repo", "ShuChenAI/teamsync-frontend",
            "--summary", "已釐清重現步驟",
            "--requested-by", "U123",
        ])

        upload_md.assert_called_once_with(
            "token", slack_list.comment_channel("F123"), "1.2", "/tmp/draft.md"
        )
        api.assert_called_once()
        method, payload, token = api.call_args.args
        self.assertEqual(method, "chat.postMessage")
        self.assertEqual(token, "token")
        self.assertEqual(payload["thread_ts"], "1.2")
        self.assertIn("<@U123>", payload["text"])
        self.assertIn("https://search", payload["text"])
        self.assertIn("https://create", payload["text"])
        self.assertIn("不會建立 GitHub issue", payload["text"])

    def artifact_path(self, name="prototype.html", content=b"<p>demo</p>"):
        path = Path(self.tmp.name) / name
        path.write_bytes(content)
        return path

    def assert_artifact_rejected(self, path, expected):
        with patch.object(slack_list, "ARTIFACT_DRAFTS_ROOT", Path(self.tmp.name)), \
                patch.object(slack_list, "config") as config, \
                redirect_stderr(io.StringIO()) as errors:
            with self.assertRaises(SystemExit):
                slack_list.cmd_artifact([
                    "RecA", "--file", str(path), "--kind", "artifact",
                    "--summary", "測試交付",
                ])
        self.assertIn(expected, errors.getvalue())
        config.assert_not_called()

    @patch.object(slack_list, "api")
    @patch.object(slack_list, "api_get")
    @patch.object(slack_list.urllib.request, "urlopen")
    @patch.object(slack_list, "item_thread_ts", return_value="1.2")
    @patch.object(slack_list, "config", return_value=("token", "F123"))
    @patch.object(slack_list, "upload_md")
    def test_artifact_uploads_then_posts_to_the_record_item_thread(
        self, upload_md, config, item_thread_ts, urlopen, api_get, api
    ):
        path = self.artifact_path()
        artifact_size = path.stat().st_size
        api_get.return_value = {
            "upload_url": "https://uploads.example.test/file",
            "file_id": "F123FILE",
        }
        upload_response = MagicMock()
        upload_response.__enter__.return_value.read.return_value = b""
        urlopen.return_value = upload_response
        api.side_effect = [{}, {}]

        output = io.StringIO()
        with patch.object(slack_list, "ARTIFACT_DRAFTS_ROOT", Path(self.tmp.name)), \
                patch.object(Path, "read_bytes", side_effect=AssertionError("artifact must not reread path")), \
                redirect_stdout(output):
            slack_list.cmd_artifact([
                "RecA", "--file", str(path), "--kind", "prototype",
                "--summary", "可操作 prototype",
            ])

        config.assert_called_once_with()
        item_thread_ts.assert_called_once_with("token", "F123", "RecA")
        upload_md.assert_not_called()
        api_get.assert_called_once_with(
            "files.getUploadURLExternal",
            {"filename": "prototype.html", "length": str(artifact_size)},
            "token",
        )
        upload_request = urlopen.call_args.args[0]
        self.assertEqual(upload_request.full_url, "https://uploads.example.test/file")
        self.assertEqual(api.call_args_list[0].args, (
            "files.completeUploadExternal",
            {
                "files": [{"id": "F123FILE", "title": "prototype"}],
                "channel_id": "C123",
                "thread_ts": "1.2",
            },
            "token",
        ))
        method, payload, token = api.call_args_list[1].args
        self.assertEqual(method, "chat.postMessage")
        self.assertEqual(token, "token")
        self.assertEqual(payload["channel"], "C123")
        self.assertEqual(payload["thread_ts"], "1.2")
        self.assertIn("prototype", payload["text"])
        self.assertIn("prototype.html", payload["text"])
        self.assertIn("可操作 prototype", payload["text"])
        self.assertIn("附件已附上", payload["text"])
        self.assertNotIn("<@", payload["text"])
        self.assertIn("artifact 已交付", output.getvalue())
        self.assertFalse(path.exists())

    def test_artifact_rejects_file_outside_drafts(self):
        with tempfile.TemporaryDirectory() as outside:
            path = Path(outside) / "outside.html"
            path.write_text("outside", encoding="utf-8")
            self.assert_artifact_rejected(path, str(Path(self.tmp.name)))

    def test_artifact_rejects_symlink(self):
        target = self.artifact_path("target.html")
        link = Path(self.tmp.name) / "link.html"
        link.symlink_to(target)
        self.assert_artifact_rejected(link, "symlink")

    def test_artifact_rejects_directory(self):
        path = Path(self.tmp.name) / "directory.html"
        path.mkdir()
        self.assert_artifact_rejected(path, "regular file")

    def test_artifact_rejects_unknown_extension(self):
        path = self.artifact_path("prototype.exe")
        self.assert_artifact_rejected(path, "副檔名")

    def test_artifact_rejects_over_limit_before_loading_config(self):
        path = self.artifact_path(
            "large.html", b"x" * (slack_list.ARTIFACT_MAX_BYTES + 1))
        self.assert_artifact_rejected(path, "單檔上限")

    def assert_remote_artifact_rejected(self, path, expected):
        with patch.object(slack_list, "ARTIFACT_DRAFTS_ROOT", Path(self.tmp.name)), \
                patch.object(slack_list, "config") as config, \
                redirect_stderr(io.StringIO()) as errors:
            with self.assertRaises(SystemExit):
                slack_list.cmd_artifact([
                    "RecA", "--file", str(path), "--kind", "artifact",
                    "--summary", "remote 測試", "--remote",
                ])
        self.assertIn(expected, errors.getvalue())
        self.assertTrue(path.exists())
        config.assert_not_called()

    def test_remote_artifact_rejects_zip_and_js_but_local_extensions_remain_compatible(self):
        for suffix in (".zip", ".js"):
            with self.subTest(suffix=suffix):
                path = self.artifact_path(f"local{suffix}", b"local")
                self.assert_remote_artifact_rejected(path, "remote artifact")
                with patch.object(slack_list, "ARTIFACT_DRAFTS_ROOT", Path(self.tmp.name)):
                    resolved, data = slack_list.artifact_file(path)
                self.assertEqual(resolved, path.resolve())
                self.assertEqual(data, b"local")

    def test_remote_html_requires_explicit_html_flag(self):
        path = self.artifact_path("remote.html")
        self.assert_remote_artifact_rejected(path, "明確加上 --html")

    def test_local_artifact_command_keeps_zip_and_js_compatibility(self):
        for suffix in (".zip", ".js"):
            with self.subTest(suffix=suffix):
                path = self.artifact_path(f"local{suffix}", b"local")
                upload_response = MagicMock()
                upload_response.__enter__.return_value.read.return_value = b""
                with patch.object(slack_list, "ARTIFACT_DRAFTS_ROOT", Path(self.tmp.name)), \
                        patch.object(slack_list, "config", return_value=("token", "F123")), \
                        patch.object(slack_list, "item_thread_ts", return_value="1.2"), \
                        patch.object(slack_list, "api_get", return_value={
                            "upload_url": "https://uploads.example.test/file", "file_id": "F1"}), \
                        patch.object(slack_list.urllib.request, "urlopen", return_value=upload_response), \
                        patch.object(slack_list, "api", side_effect=[{}, {}]), \
                        redirect_stdout(io.StringIO()):
                    slack_list.cmd_artifact([
                        "RecA", "--file", str(path), "--kind", "artifact",
                        "--summary", "local 測試",
                    ])
                self.assertFalse(path.exists())

    def test_cleanup_keeps_symlink_and_outside_file(self):
        root = Path(self.tmp.name) / "drafts"
        root.mkdir()
        outside = Path(self.tmp.name) / "outside.png"
        outside.write_bytes(b"outside")
        link = root / "link.png"
        link.symlink_to(outside)
        now = 1_700_000_000.0
        os.utime(outside, (now - slack_list.ARTIFACT_RETENTION_SECONDS - 1,) * 2)

        with patch.object(slack_list, "ARTIFACT_DRAFTS_ROOT", root):
            removed = slack_list.cleanup_artifacts(now=now)

        self.assertEqual(removed, [])
        self.assertTrue(link.is_symlink())
        self.assertTrue(outside.exists())

    def test_cleanup_keeps_23_59_and_deletes_at_24_00(self):
        root = Path(self.tmp.name) / "drafts"
        root.mkdir()
        keep = root / "keep.png"
        delete = root / "delete.png"
        keep.write_bytes(b"keep")
        delete.write_bytes(b"delete")
        now = 1_700_000_000.0
        os.utime(keep, (now - (24 * 60 * 60 - 59),) * 2)
        os.utime(delete, (now - slack_list.ARTIFACT_RETENTION_SECONDS,) * 2)

        with patch.object(slack_list, "ARTIFACT_DRAFTS_ROOT", root):
            removed = slack_list.cleanup_artifacts(now=now)

        self.assertTrue(keep.exists())
        self.assertFalse(delete.exists())
        self.assertEqual(removed, ["delete.png"])

    @patch.object(slack_list, "item_threads")
    def test_item_thread_rejects_cross_channel_parent(self, item_threads):
        item_threads.return_value = {"RecA": {"ts": "1.2", "channel": "C999"}}
        with patch.object(slack_list, "die", side_effect=SystemExit) as die:
            with self.assertRaises(SystemExit):
                slack_list.item_thread_ts("token", "F123", "RecA")
        self.assertIn("錯誤 channel", die.call_args.args[0])

    def test_artifact_walks_directories_with_nofollow_flags_and_closes_fds(self):
        root = Path(self.tmp.name) / "drafts"
        nested = root / "nested" / "deep"
        nested.mkdir(parents=True)
        path = nested / "prototype.html"
        path.write_bytes(b"safe")
        calls = []
        opened_fds = []
        real_open = slack_list.os.open

        def capture_open(path_arg, flags, *args, **kwargs):
            fd = real_open(path_arg, flags, *args, **kwargs)
            calls.append((path_arg, flags, kwargs.get("dir_fd")))
            opened_fds.append(fd)
            return fd

        with patch.object(slack_list, "ARTIFACT_DRAFTS_ROOT", root), \
                patch.object(slack_list.os, "open", side_effect=capture_open):
            resolved, data = slack_list.artifact_file(path)

        self.assertEqual(resolved, path.resolve())
        self.assertEqual(data, b"safe")
        self.assertEqual(len(calls), 4)
        root_flags = slack_list.os.O_RDONLY | slack_list.os.O_DIRECTORY | slack_list.os.O_NOFOLLOW
        self.assertEqual(calls[0], (root.resolve(), root_flags, None))
        for path_arg, flags, dir_fd in calls[1:3]:
            self.assertIn(path_arg, ("nested", "deep"))
            self.assertEqual(flags, root_flags)
            self.assertIsNotNone(dir_fd)
        self.assertEqual(calls[3][0], "prototype.html")
        self.assertEqual(calls[3][1], slack_list.os.O_RDONLY | slack_list.os.O_NOFOLLOW)
        self.assertIsNotNone(calls[3][2])
        for fd in opened_fds:
            with self.assertRaises(OSError):
                os.fstat(fd)

    def test_artifact_fails_closed_without_required_open_flags(self):
        path = self.artifact_path()
        for flag_name in ("O_NOFOLLOW", "O_DIRECTORY"):
            with self.subTest(flag_name=flag_name), \
                    patch.object(slack_list, "ARTIFACT_DRAFTS_ROOT", Path(self.tmp.name)), \
                    patch.object(slack_list.os, flag_name, 0), \
                    patch.object(slack_list.os, "open") as open_call, \
                    redirect_stderr(io.StringIO()) as errors:
                with self.assertRaises(SystemExit):
                    slack_list.artifact_file(path)
            open_call.assert_not_called()
            self.assertIn("O_NOFOLLOW 或 O_DIRECTORY", errors.getvalue())

    @patch.object(slack_list, "api")
    @patch.object(slack_list, "api_get")
    @patch.object(slack_list.urllib.request, "urlopen")
    @patch.object(slack_list, "item_thread_ts", return_value="1.2")
    @patch.object(slack_list, "config", return_value=("token", "F123"))
    def test_artifact_upload_failure_does_not_post(
        self, config, item_thread_ts, urlopen, api_get, api
    ):
        path = self.artifact_path()
        api_get.return_value = {"upload_url": "https://uploads.example.test/file", "file_id": "F1"}
        urlopen.side_effect = slack_list.urllib.error.URLError("upload timeout")

        with patch.object(slack_list, "ARTIFACT_DRAFTS_ROOT", Path(self.tmp.name)), \
                redirect_stderr(io.StringIO()) as errors:
            with self.assertRaises(SystemExit):
                slack_list.cmd_artifact([
                    "RecA", "--file", str(path), "--kind", "artifact", "--summary", "失敗測試",
                ])

        api.assert_not_called()
        self.assertIn("檔案上傳失敗", errors.getvalue())
        self.assertTrue(path.exists())

    @patch.object(slack_list, "api")
    @patch.object(slack_list, "api_get")
    @patch.object(slack_list.urllib.request, "urlopen")
    @patch.object(slack_list, "item_thread_ts", return_value="1.2")
    @patch.object(slack_list, "config", return_value=("token", "F123"))
    def test_artifact_complete_failure_does_not_post(
        self, config, item_thread_ts, urlopen, api_get, api
    ):
        path = self.artifact_path()
        api_get.return_value = {"upload_url": "https://uploads.example.test/file", "file_id": "F1"}
        upload_response = MagicMock()
        upload_response.__enter__.return_value.read.return_value = b""
        urlopen.return_value = upload_response
        api.side_effect = SystemExit(1)

        with patch.object(slack_list, "ARTIFACT_DRAFTS_ROOT", Path(self.tmp.name)), \
                redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                slack_list.cmd_artifact([
                    "RecA", "--file", str(path), "--kind", "artifact", "--summary", "失敗測試",
                ])

        api.assert_called_once()
        self.assertEqual(api.call_args.args[0], "files.completeUploadExternal")
        self.assertTrue(path.exists())

    @patch.object(slack_list, "api")
    @patch.object(slack_list, "api_get")
    @patch.object(slack_list.urllib.request, "urlopen")
    @patch.object(slack_list, "item_thread_ts", return_value="1.2")
    @patch.object(slack_list, "config", return_value=("token", "F123"))
    def test_artifact_post_failure_warns_attachment_may_exist_and_not_to_retry(
        self, config, item_thread_ts, urlopen, api_get, api
    ):
        path = self.artifact_path()
        api_get.return_value = {"upload_url": "https://uploads.example.test/file", "file_id": "F1"}
        upload_response = MagicMock()
        upload_response.__enter__.return_value.read.return_value = b""
        urlopen.return_value = upload_response
        api.side_effect = [{}, SystemExit(1)]

        with patch.object(slack_list, "ARTIFACT_DRAFTS_ROOT", Path(self.tmp.name)), \
                redirect_stderr(io.StringIO()) as errors:
            with self.assertRaises(SystemExit):
                slack_list.cmd_artifact([
                    "RecA", "--file", str(path), "--kind", "artifact", "--summary", "失敗測試",
                ])

        self.assertEqual(api.call_count, 2)
        message = errors.getvalue()
        self.assertIn("附件可能已上傳", message)
        self.assertIn("先檢查 item 留言串", message)
        self.assertIn("勿直接重試", message)
        self.assertTrue(path.exists())

    def test_check_url_rejects_non_http_scheme(self):
        with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()) as err:
            slack_list.check_url("ftp://example.com")
        self.assertIn("http", err.getvalue())

    @patch.object(slack_list.urllib.request, "urlopen")
    def test_check_url_rejects_error_status(self, urlopen):
        # HEAD 跟 GET 都 4xx 才算死的。只有 HEAD 被擋的情況見下一個測試。
        urlopen.side_effect = slack_list.urllib.error.HTTPError(
            "https://gone.pages.dev", 403, "Forbidden", {}, None)
        with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()) as err:
            slack_list.check_url("https://gone.pages.dev")
        self.assertIn("403", err.getvalue())
        self.assertIn("--no-url", err.getvalue())

    @patch.object(slack_list.urllib.request, "urlopen")
    def test_check_url_passes_on_200(self, urlopen):
        urlopen.return_value.__enter__.return_value.status = 200
        slack_list.check_url("https://fix-spc-update.example.pages.dev")

    @patch.object(slack_list.urllib.request, "urlopen")
    def test_check_url_does_not_send_the_blocked_default_user_agent(self, urlopen):
        # urllib 預設送 Python-urllib/3.x，Cloudflare 的 bot 規則直接回 403，
        # 而分支預覽就掛在 Cloudflare Pages 上 —— 活著的網址會被判成死的。
        urlopen.return_value.__enter__.return_value.status = 200
        slack_list.check_url("https://fix-spc-update.example.pages.dev")
        request = urlopen.call_args.args[0]
        self.assertNotIn("Python-urllib", request.get_header("User-agent"))

    @patch.object(slack_list.urllib.request, "urlopen")
    def test_check_url_retries_with_get_when_head_is_rejected(self, urlopen):
        def answer(request, timeout=None):
            if request.method == "HEAD":
                raise slack_list.urllib.error.HTTPError(
                    request.full_url, 403, "Forbidden", {}, None)
            response = MagicMock()
            response.__enter__.return_value.status = 200
            return response

        urlopen.side_effect = answer
        slack_list.check_url("https://fix-spc-update.example.pages.dev")
        self.assertEqual(
            [c.args[0].method for c in urlopen.call_args_list], ["HEAD", "GET"])

    def write_report(self, body):
        path = Path(self.tmp.name) / "report.md"
        path.write_text(body, encoding="utf-8")
        return str(path)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        # deep_link 沒有預設 workspace（repo 是 public），測試給一組假的。
        env = patch.dict(os.environ, {
            "SLACK_WORKSPACE_URL": "https://example.slack.com",
            "SLACK_TEAM_ID": "T000",
        })
        env.start()
        self.addCleanup(env.stop)

    FULL_REPORT = (
        "# V01 庫存異常狀態顯示 — 驗收說明\n\n"
        "測試網址：https://fix-inventory.example.pages.dev\n\n"
        "## 改了什麼\n\n- 判定基準改成可用數\n\n"
        "## 怎麼驗收\n\n1. 開庫存列表看 PMV 低庫存示範品\n\n"
        "## QA case（✅ = 程式自動測試已覆蓋）\n\n"
        "| 情境 | 自動測試 |\n|---|---|\n| 可用數低於門檻就是低庫存 | ✅ |\n"
    )

    def test_report_body_requires_every_fixed_section(self):
        path = self.write_report("## 改了什麼\n\n- a\n\n## 怎麼驗收\n\n1. b\n")
        with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()) as err:
            slack_list.report_body(path)
        self.assertIn("## QA case", err.getvalue())

    def test_report_body_rejects_manual_mark_without_a_reason(self):
        # ⬜ 沒寫原因，PM 分不出那是漏測還是刻意不測
        path = self.write_report(
            self.FULL_REPORT + "| 列表四種顏色 | ⬜ |\n")
        with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()) as err:
            slack_list.report_body(path)
        self.assertIn("⬜", err.getvalue())

    def test_report_body_accepts_manual_mark_with_a_reason(self):
        path = self.write_report(
            self.FULL_REPORT + "| 列表四種顏色 | ⬜ 純顏色，要人工看 |\n")
        self.assertIn("⬜ 純顏色，要人工看", slack_list.report_body(path))

    def test_report_body_drops_title_and_url_already_in_the_message(self):
        body = slack_list.report_body(self.write_report(self.FULL_REPORT))
        self.assertTrue(body.startswith("## 改了什麼"))
        self.assertNotIn("測試網址", body)
        self.assertNotIn("驗收說明", body)

    def test_report_body_warns_when_its_url_differs_from_the_flag(self):
        path = self.write_report(self.FULL_REPORT)
        with redirect_stderr(io.StringIO()) as err:
            slack_list.report_body(path, "https://other.example.pages.dev")
        self.assertIn("測試網址", err.getvalue())

    @patch.object(slack_list, "api")
    @patch.object(slack_list, "bot_user_id", return_value="UBOT")
    @patch.object(slack_list, "thread_messages", return_value=[])
    @patch.object(slack_list, "item_thread_ts", return_value="1.2")
    @patch.object(slack_list, "record")
    @patch.object(slack_list, "schema")
    @patch.object(slack_list, "config", return_value=("token", "F123"))
    @patch.object(slack_list, "check_url")
    def test_ready_report_goes_out_as_one_markdown_block(
        self, check_url, config, schema, record, item_thread_ts,
        thread_messages, bot_user_id, api
    ):
        schema.return_value = self.add_schema() | {
            slack_list.COL_FILE: {"id": "file-col"}}
        record.return_value = {
            "created_by": "U123",
            "fields": [{"column_id": "title-col", "text": "庫存異常狀態顯示"}],
        }

        slack_list.cmd_ready([
            "RecA", "--report", self.write_report(self.FULL_REPORT),
            "--url", "https://fix-inventory.example.pages.dev",
        ])

        blocks = api.call_args_list[0].args[1]["blocks"]
        # section 的 mrkdwn 不吃 pipe table，QA case 那張表得靠 markdown block
        markdown = [b for b in blocks if b["type"] == "markdown"]
        self.assertEqual(len(markdown), 1)
        self.assertIn("| 情境 | 自動測試 |", markdown[0]["text"])
        self.assertIn("<@U123>", blocks[0]["text"]["text"])

    def test_ready_refuses_report_and_flags_together(self):
        with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()) as err:
            slack_list.cmd_ready([
                "RecA", "--report", self.write_report(self.FULL_REPORT),
                "--changed", "改了東西", "--no-url",
            ])
        self.assertIn("--changed", err.getvalue())

    def test_ready_refuses_when_neither_report_nor_flags_given(self):
        with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()) as err:
            slack_list.cmd_ready(["RecA", "--no-url"])
        self.assertIn("--report", err.getvalue())

    def completed_rows(self):
        return [
            {"id": "RecOpen", "fields": [
                {"key": "todo_completed", "checkbox": False},
                {"key": "name", "text": "還沒做完"},
            ]},
            {"id": "RecDone", "fields": [
                {"key": "todo_completed", "checkbox": True},
                {"key": "name", "text": "已經做完"},
            ]},
            {"id": "RecArchived", "archived": True, "fields": [
                {"key": "todo_completed", "checkbox": False},
                {"key": "name", "text": "被封存"},
            ]},
        ]

    def test_active_rows_drops_completed_and_archived(self):
        kept = slack_list.active_rows(self.completed_rows())
        self.assertEqual([r["id"] for r in kept], ["RecOpen"])

    @patch.object(slack_list, "fetch_all")
    def test_todo_defaults_to_open_rows_and_says_the_view_is_filtered(self, fetch_all):
        fetch_all.return_value = self.completed_rows()
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            slack_list.cmd_todo([])

        self.assertIn("還沒做完", output.getvalue())
        self.assertNotIn("已經做完", output.getvalue())
        # 沒有這句，agent 會把過濾後的結果當成整張表，回「PM 沒有這件事」
        self.assertIn("--all", errors.getvalue())
        self.assertIn("1 列未完成（全表 3 列", errors.getvalue())

    @patch.object(slack_list, "fetch_all")
    def test_todo_all_includes_completed_rows(self, fetch_all):
        fetch_all.return_value = self.completed_rows()
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            slack_list.cmd_todo(["--all"])

        self.assertIn("已經做完", output.getvalue())
        self.assertIn("被封存", output.getvalue())
        # 只報總數的話，狀態欄還留著舊值的已結案列會被當成待辦
        self.assertIn("其中 1 列已完成", errors.getvalue())

    @patch.object(slack_list, "fetch_all")
    def test_json_defaults_to_open_rows(self, fetch_all):
        fetch_all.return_value = self.completed_rows()
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(io.StringIO()):
            slack_list.cmd_json([])

        self.assertEqual([r["_id"] for r in json.loads(output.getvalue())], ["RecOpen"])

    def test_one_line_collapses_newlines_and_truncates(self):
        self.assertEqual(slack_list.one_line("a\nb  c"), "a b c")
        self.assertEqual(slack_list.one_line("x" * 10, 4), "xxxx…")
        self.assertEqual(slack_list.one_line("x" * 4, 4), "xxxx")

    @patch.object(slack_list, "text_columns", return_value={slack_list.COL_DESCRIPTION})
    def test_format_row_truncates_text_columns_only(self, text_columns):
        assignees = " ".join(["U0123456789"] * 12)
        line = slack_list.format_row({
            "_id": "RecA",
            slack_list.COL_DESCRIPTION: "規格\n第二行" + "字" * 300,
            slack_list.COL_ASSIGNEE: assignees,
        })

        self.assertTrue(line.startswith("[RecA] "))
        self.assertIn("規格 第二行", line)   # 換行壓成空格，一列才真的是一行
        self.assertNotIn("\n", line)
        self.assertIn("…", line)
        # user 欄不能截 —— 截一半的 U… 沒辦法拿去 --assignee，也沒辦法用眼睛比對
        self.assertIn(assignees, line)

    @patch.object(slack_list, "text_columns", return_value={slack_list.COL_DESCRIPTION})
    def test_format_row_full_keeps_the_original_text(self, text_columns):
        line = slack_list.format_row(
            {"_id": "RecA", slack_list.COL_DESCRIPTION: "規格\n第二行"}, full=True)
        self.assertIn("規格\n第二行", line)

    @patch.object(slack_list, "text_columns", return_value=set())
    def test_print_rows_columns_filter_keeps_the_record_id(self, text_columns):
        output = io.StringIO()
        with redirect_stdout(output):
            slack_list.print_rows(
                [{"_id": "RecA", slack_list.COL_TITLE: "甲",
                  slack_list.COL_DESCRIPTION: "乙"}],
                columns=[slack_list.COL_TITLE])

        self.assertEqual(output.getvalue().strip(), f"[RecA] {slack_list.COL_TITLE}: 甲")

    def test_resolve_column_rejects_an_unknown_name(self):
        with self.assertRaises(SystemExit), patch.object(
            slack_list, "die", side_effect=SystemExit
        ):
            slack_list.resolve_column("不存在", [slack_list.COL_TITLE])

    @patch.object(slack_list, "fetch_all", return_value=[])
    @patch.object(slack_list, "column_index", return_value=({}, {}))
    @patch.object(slack_list, "config", return_value=("xoxb-token", "F123"))
    def test_fields_lists_the_choices_of_select_columns(
        self, config, column_index, fetch_all
    ):
        # 不列出選項的話 --where 等於沒用：agent 不知道「狀態」能填什麼，
        # 只好先撈整張表再自己 grep 統計。
        cols = {
            slack_list.COL_STATUS: {
                "id": "status-col",
                "type": "select",
                "options": {"choices": [
                    {"label": slack_list.STATUS_READY, "value": "o1"},
                    {"label": "已完成", "value": "o2"},
                ]},
            },
            slack_list.COL_TITLE: {"id": "title-col", "type": "text"},
        }
        output = io.StringIO()
        with patch.object(slack_list, "schema", return_value=cols), \
                redirect_stdout(output), redirect_stderr(io.StringIO()):
            slack_list.cmd_fields()

        got = {e["欄位"]: e for e in json.loads(output.getvalue())}
        self.assertEqual(got[slack_list.COL_STATUS]["可填的值"],
                         [slack_list.STATUS_READY, "已完成"])
        self.assertNotIn("可填的值", got[slack_list.COL_TITLE])

    @patch.object(slack_list, "config", return_value=("xoxb-token", "F123"))
    @patch.object(slack_list, "api_get")
    def test_users_resolves_a_slack_id_back_to_a_name(self, api_get, config):
        # 表上只存 ID，列出「指派對象」之後一定會需要反查是誰。
        api_get.return_value = {
            "members": [
                {"id": "U123", "name": "henry", "profile": {"display_name": "henry"}},
                {"id": "U456", "name": "whales", "profile": {"display_name": "Whales"}},
            ],
            "response_metadata": {"next_cursor": ""},
        }
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(io.StringIO()):
            slack_list.cmd_users(["U456"])

        self.assertEqual(output.getvalue().strip().split("\t")[0], "U456")
        self.assertNotIn("U123", output.getvalue())

    @patch.object(slack_list, "config", return_value=("xoxb-token", "F123"))
    @patch.object(slack_list, "api_get")
    def test_users_id_match_is_exact_not_substring(self, api_get, config):
        api_get.return_value = {
            "members": [{"id": "U1234", "name": "henry", "profile": {}}],
            "response_metadata": {"next_cursor": ""},
        }
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            slack_list.cmd_users(["U123"])

        self.assertEqual(output.getvalue(), "")
        self.assertIn("已停用的帳號或 bot", errors.getvalue())

    # --- rows：唯一的查詢入口，條件都疊在 flag 上 ---

    def query_rows(self):
        """一份夠小、但每個 flag 都咬得到的表。"""
        return [
            {"id": "RecA", "created_by": "U_PM", "fields": [
                {"key": "todo_completed", "checkbox": False},
                {"key": "todo_assignee", "user": ["U_HENRY", "U_WHALES"]},
                {"key": "name", "text": "庫存模組"},
                {"key": "status", "text": "PM確認中"},
                {"key": "kind", "text": "bug"},
            ]},
            {"id": "RecB", "created_by": "U_PM", "fields": [
                {"key": "todo_completed", "checkbox": True},
                {"key": "todo_assignee", "user": ["U_HENRY"]},
                {"key": "name", "text": "舊的庫存問題"},
                {"key": "status", "text": "PM確認中"},
                {"key": "kind", "text": "bug"},
            ]},
            {"id": "RecC", "created_by": "U_OTHER", "fields": [
                {"key": "todo_completed", "checkbox": False},
                {"key": "todo_assignee", "user": ["U_HENRY2"]},
                {"key": "name", "text": "報表匯出"},
                {"key": "status", "text": "前端完成"},
                {"key": "kind", "text": "request"},
            ]},
        ]

    def run_rows(self, argv):
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(slack_list, "fetch_all", return_value=self.query_rows()), \
                redirect_stdout(output), redirect_stderr(errors):
            slack_list.cmd_rows(argv)
        ids = re.findall(r"\[(Rec\w+)\]", output.getvalue())
        return ids, output.getvalue(), errors.getvalue()

    def test_rows_defaults_to_open_rows(self):
        ids, _, errors = self.run_rows([])

        self.assertEqual(ids, ["RecA", "RecC"])   # RecB 已完成
        self.assertIn("2 列未完成", errors)

    def test_rows_stacks_conditions_with_and_not_or(self):
        ids, _, _ = self.run_rows(["--created-by", "U_PM", "--where", "status=PM確認中"])

        self.assertEqual(ids, ["RecA"])

    def test_rows_where_is_a_case_insensitive_substring_match(self):
        # 欄位值是 PM 在 UI 上維護的，要求完全相符等於每次改字都壞掉
        ids, _, _ = self.run_rows(["--where", "kind=BU"])

        self.assertEqual(ids, ["RecA"])

    def test_rows_where_accepts_a_partial_column_name(self):
        ids, _, _ = self.run_rows(["--where", "stat=前端"])

        self.assertEqual(ids, ["RecC"])

    def test_rows_assignee_matches_a_whole_user_id(self):
        # U_HENRY 不該撈出 U_HENRY2 —— 子字串比對會把別人的事算到你頭上
        ids, _, _ = self.run_rows(["--assignee", "U_HENRY"])

        self.assertEqual(ids, ["RecA"])

    def test_rows_created_by_reads_the_item_not_a_column(self):
        # 建立者不在 fields 裡，在 item 上
        ids, _, _ = self.run_rows(["--created-by", "U_OTHER"])

        self.assertEqual(ids, ["RecC"])

    def test_rows_keyword_matches_anywhere_in_the_row(self):
        ids, _, _ = self.run_rows(["匯出"])

        self.assertEqual(ids, ["RecC"])

    def test_rows_columns_prints_only_the_named_columns(self):
        ids, output, _ = self.run_rows(["--columns", "name", "--assignee", "U_HENRY"])

        self.assertEqual(ids, ["RecA"])
        self.assertEqual(output.strip(), "[RecA] name: 庫存模組")

    def test_rows_all_reports_how_many_of_them_are_done(self):
        # --columns 常常把「已完成」欄擋掉，這個數字是 agent 唯一的線索。
        # 實際發生過：加了 --all 從 6 件變 26 件，多的 20 件全已結案，回覆只說「共 26 件」。
        ids, _, errors = self.run_rows(["--where", "status=PM確認中", "--all"])

        self.assertEqual(ids, ["RecA", "RecB"])
        self.assertIn("其中 1 列已完成", errors)

    def test_rows_without_all_never_mentions_a_done_count(self):
        _, _, errors = self.run_rows(["--where", "status=PM確認中"])

        self.assertNotIn("其中", errors)
        self.assertIn("要看加 --all", errors)

    def test_rows_empty_result_lists_the_values_that_column_actually_has(self):
        # 值打錯和「真的沒有」長得一模一樣，不列出來就分不出
        _, output, errors = self.run_rows(["--where", "status=不存在"])

        self.assertEqual(output, "")
        self.assertIn("0 列未完成", errors)
        self.assertIn("PM確認中×1", errors)
        self.assertIn("前端完成×1", errors)

    def test_rows_empty_result_summarises_a_high_cardinality_column(self):
        # 幾百種值全列出來又是一份雜訊
        many = [{"id": f"Rec{i}", "created_by": "U_PM", "fields": [
            {"key": "todo_completed", "checkbox": False},
            {"key": "name", "text": f"事項 {i}"},
        ]} for i in range(30)]
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(slack_list, "fetch_all", return_value=many), \
                redirect_stdout(output), redirect_stderr(errors):
            slack_list.cmd_rows(["--where", "name=不存在"])

        self.assertIn("有 30 種值", errors.getvalue())
        self.assertNotIn("事項 29×1、事項 28×1", errors.getvalue())

    def test_rows_rejects_an_unknown_where_column(self):
        with self.assertRaises(SystemExit), patch.object(
            slack_list, "die", side_effect=SystemExit
        ):
            self.run_rows(["--where", "不存在的欄位=x"])

    def test_rows_rejects_a_where_without_an_equals_sign(self):
        with self.assertRaises(SystemExit), patch.object(
            slack_list, "die", side_effect=SystemExit
        ):
            self.run_rows(["--where", "status"])

    def test_schema_lookups_survive_a_missing_env(self):
        # config() 走的是 die()，而 die() 是 sys.exit()，不是 Exception。
        # 沒接住的話「沒有 .env 就退回內部 id」這條退路根本走不到，整支直接掛掉。
        slack_list._COLUMN_INDEX = None
        slack_list._TEXT_COLUMNS = None
        with patch.object(slack_list, "config", side_effect=SystemExit(1)), \
                redirect_stderr(io.StringIO()):
            self.assertEqual(REAL_COLUMN_INDEX(), ({}, {}))
            self.assertEqual(REAL_TEXT_COLUMNS(), set())


if __name__ == "__main__":
    unittest.main()
