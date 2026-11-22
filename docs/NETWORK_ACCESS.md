# Restoring Codex command networking

The user's normal terminal successfully called `gemini-3.5-flash-lite` on
8 November 2026 using the project's `.env`: a valid structured response,
24 tokens, about 1.67 seconds. The key and that terminal's connectivity work.
The restricted agent shell separately fails to create network sockets and
resolve Google, Semantic Scholar and PyPI hosts. That failure occurs before
Gemini can accept or reject the key.

The active session explicitly has restricted network access. Its sandbox
approval category is disabled, and its project `.codex` directory is read-only.
The assistant cannot change those permissions from inside this conversation.
No permission-escalation attempt or network bridge was used.

## Resume from a normal terminal

Leave the current Codex session. From `agentic_research_review`, run:

```bash
bash scripts/resume_with_network.sh
```

This uses the documented `sandbox_workspace_write.network_access=true` setting,
keeps workspace-write filesystem boundaries and on-request approvals, and
uses a fresh CLI process rather than the existing shared daemon. It resumes
the latest conversation across working directories. If a different conversation
is selected, pass this conversation's session ID explicitly:

```bash
bash scripts/resume_with_network.sh SESSION_ID
```

The launcher has been checked locally for shell syntax and argument construction.
It has not been launched from inside the restricted session: doing so would
inherit the restriction and would not validate the fix. Resuming a conversation
does not automatically run experiments or change the Gemini model.

An administrator-enforced permission profile may reject this request or enforce
restricted networking regardless of the flag. In that case the host app or
administrator must enable command networking for this project; repository code
cannot override that policy.

## Verify after resuming

Ask the resumed agent to run:

```bash
../.venv/bin/python scripts/check_gemini.py
```

Use `.venv/bin/python` instead if you created a project-local environment.
The script reads `.env`, makes one small structured-output request, prints no
credential value, and records the actual result in
`results/gemini_connection_check.json`. Do not infer success just from the
presence of a key or from the launcher's syntax check.

References: [OpenAI configuration reference](https://developers.openai.com/codex/config-reference)
documents `sandbox_workspace_write.network_access`,
`default_permissions` compatibility, and administrator-enforced requirements.
The installed CLI's `codex resume --help` confirms the launcher flags.
