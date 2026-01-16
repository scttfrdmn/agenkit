#!/bin/bash
# Wrapper script for TypeScript harness
cd "$(dirname "$0")/harness_ts"
node dist/index.js
