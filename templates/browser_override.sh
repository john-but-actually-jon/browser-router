#!/bin/bash

# Add this to a dotfiles directory in your repository's root. Then source it as part of startup.

ctx="my-custom-context"

curl -fsS -G \
  --data-urlencode "url=$1" \
  --data-urlencode "ctx=${BROWSER_CTX:-$ctx}" \
  http://host.docker.internal:${BROWSER_PORT:8765}/open >/dev/null
