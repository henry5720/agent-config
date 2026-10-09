---
name: pr-review-and-verify
description: >-
  Use when the user asks to review a pull request, address its review feedback,
  or complete a PR author round with verification and thread replies.
---

# PR review and verification

Handle a PR author round from a pinned head through fixes, verification, and replies. Keep one agent responsible for every publication in the round.

## Choose the skill for the requested work

- For reviewing code changes or review feedback against standards and the originating spec, follow `code-review`.
- For writing or revising a PR body, follow `pr`.
- For browser-based verification, follow `verify-in-browser` and its referenced browser tooling skill.
- Use this skill to coordinate the author round: establish the reviewed head, address the complete feedback set, verify the resulting commit, and reply in the original threads. When the user explicitly requests only one of the tasks above, follow that task's skill rather than running a full author round.

## Author round

1. **Pin the round.** Identify the PR and record its current head commit. Gather every review thread and review comment that needs an author response, including already-resolved threads when the user asks for a complete round. Keep the original thread identifiers and reviewer requests together. If the review scope or tracker is unavailable, ask for it before publishing.
2. **Review the feedback.** Use `code-review` for code/spec review. Assess each item against the diff and originating requirements; mark it actionable, already addressed, or not applicable, with a concise reason for the latter two. Do not silently omit a thread.
3. **Apply and verify fixes.** Make the requested changes, then run the repository's required checks. Treat verification as bound to the exact commit tested: record that commit and the checks/results. Reuse those results only while the PR head is that same commit. Any new commit invalidates the prior verification; rerun the checks relevant to the changed commit before claiming it is verified.
4. **Recheck before publication.** Immediately before publishing any review reply or PR comment, fetch/check the PR head again. Publish only if it still matches the commit covered by this round's review and verification. If it moved, stop publication, inspect the new changes, and repeat review and relevant verification against the new head.
5. **Publish the complete response set.** One agent publishes all responses for the round. Reply to each item in its original review thread, explaining the fix and commit or the reason it was not changed. Do not create duplicate top-level comments when an original thread exists. After publication, report the reviewed head, verification commit and results, and any item that could not be addressed or published.

## Publication boundaries

- Keep a single publisher for the entire round; parallel reviewers may report findings but must not post replies or comments.
- Replies belong in their original threads so the author response stays beside the feedback.
- This skill does not authorize resolving threads, approving the PR, or merging it. Leave those actions to the user or their separately authorized workflow.
- Do not claim a round is complete when any requested feedback lacks a disposition, a required check has not run, or publication was blocked by a changed head.
