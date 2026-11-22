#!/usr/bin/env bash
# Run from a normal terminal after leaving the restricted Codex session.
# This requests supported workspace networking; managed policy still applies.
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v codex >/dev/null 2>&1; then
    echo 'Codex CLI is not available in this terminal PATH.' >&2
    exit 1
fi

# Pass a session ID as the first argument to select a specific conversation.
# Otherwise --all allows --last to find the conversation even when its original
# working directory was the parent ResearchAgent folder.
session_args=(--last --all)
if [[ $# -gt 0 ]]; then
    session_args=("$1")
fi

exec codex resume "${session_args[@]}" \
    --cd "$project_root" \
    --sandbox workspace-write \
    --config sandbox_workspace_write.network_access=true \
    --ask-for-approval on-request \
    --no-daemon
