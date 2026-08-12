#!/bin/sh
# Run a command with OPENADAPT_FLOW_GROUNDING_API_KEY sourced from the macOS
# Keychain item `oa-qwen-endpoint-token` (account `modal`) at runtime.
#
# The token value never touches the shell history, argv of the child, logs,
# or any file: it is exported as an environment variable only, and this
# script never echoes it.
#
# Usage:
#   ./with_token.sh curl ...                       # authed curl
#   ./with_token.sh python3 smoke_grounder.py ...  # authed grounder smoke
set -eu

OPENADAPT_FLOW_GROUNDING_API_KEY="$(security find-generic-password -s oa-qwen-endpoint-token -a modal -w)"
export OPENADAPT_FLOW_GROUNDING_API_KEY

exec "$@"
