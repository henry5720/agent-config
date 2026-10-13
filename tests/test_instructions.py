"""instructions/ 裡的 Instructions：source 檔在不在、彼此引用的路徑對不對。

要連到哪些路徑由 dotfiles 的 chezmoi symlink 模板決定，那邊的 tests 驗；這裡只驗 source 內容。
"""
import unittest
from pathlib import Path


INSTRUCTIONS = Path(__file__).resolve().parents[1] / "instructions"
AGENTS = INSTRUCTIONS / "agents-md" / "AGENTS.md"
AGENT_COMMIT = INSTRUCTIONS / "agent-commit" / "instructions.md"
OPENCODE_COMMIT = INSTRUCTIONS / "opencode-commit" / "commit-instructions.md"
AGENT_COMMIT_PATH = "~/.config/agent-commit/instructions.md"


class InstructionsTest(unittest.TestCase):
    def test_sources_exist(self):
        for path in (AGENTS, AGENT_COMMIT, OPENCODE_COMMIT):
            with self.subTest(path=path.relative_to(INSTRUCTIONS)):
                self.assertTrue(path.is_file())
                self.assertTrue(path.read_text(encoding="utf-8").strip())

    def test_commit_guides_point_to_shared_agent_commit_instructions(self):
        # Claude、Codex、OpenCode 讀的都是 AGENTS.md（Claude 那邊的 symlink 叫 CLAUDE.md），
        # OpenCode 另外經 opencode.json 載入 commit-instructions.md。
        for path in (AGENTS, OPENCODE_COMMIT):
            with self.subTest(path=path.relative_to(INSTRUCTIONS)):
                self.assertIn(AGENT_COMMIT_PATH, path.read_text(encoding="utf-8"))

    def test_agent_commit_lists_each_agent_identity(self):
        text = AGENT_COMMIT.read_text(encoding="utf-8")
        for marker in (
            "Co-authored-by: Claude Code <noreply@anthropic.com>",
            "Co-authored-by: Codex <noreply@openai.com>",
            "Generated with OpenCode.",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_opencode_commit_guide_marks_opencode(self):
        self.assertIn("Generated with OpenCode.", OPENCODE_COMMIT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
