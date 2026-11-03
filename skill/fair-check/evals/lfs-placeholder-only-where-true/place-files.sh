#!/usr/bin/env bash
set -eu
cp -R "$(dirname "$0")/files/." .
# GitHub refuses a Git LFS pointer without its file, so the fake one is written here
printf 'version https://git-lfs.github.com/spec/v1\noid sha256:4d7a2146c0bd2e1b0f6ad3ab2e9f0c1e5b6a7d8c9e0f1a2b3c4d5e6f7a8b9c0d\nsize 75219\n' \
  > sleep_models/data/processed/trials.rds
