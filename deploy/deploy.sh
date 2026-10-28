#!/usr/bin/env bash
# Rolls the stack out from origin/master when master has a commit that is not deployed yet.
# Runs every minute from a checkout used only for deploys (~/ChangeBot-deploy) by
# changebot-deploy.timer, so the development checkout can stay on any branch.
set -euo pipefail

main() {
    cd "$(dirname "$0")/.."
    local state="${XDG_STATE_HOME:-$HOME/.local/state}/changebot-deployed"

    git fetch -q origin master
    local target
    target=$(git rev-parse origin/master)
    # The marker is written only after a successful rollout, so a failed build is retried
    [ "$(cat "$state" 2>/dev/null)" = "$target" ] && return

    echo "Deploying $(git log -1 --format='%h %s' "$target")"
    git reset -q --hard "$target"
    docker compose up -d --build

    mkdir -p "$(dirname "$state")"
    echo "$target" > "$state"
    echo "Deployed $target"
}

# Wrapped in a function so bash parses the whole file before git reset rewrites it
main "$@"
