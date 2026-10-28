#!/usr/bin/env bash
# Verify that two clean builds of the same source produce the same image.
#
# The comparison uses `--provenance=false`: with the default attestation
# enabled, BuildKit embeds per-build metadata in the attestation manifest,
# so the OCI *index* digest differs even when every layer and the image
# manifest are byte-identical. The platform manifest digest is the
# reproducible identity of the image.
#
# Usage:
#   scripts/check_reproducible_build.sh [TAG-PREFIX]

set -euo pipefail

cd "$(dirname "$0")/.."

PREFIX="${1:-percival-deep-research:repro}"
VERSION="$(python3 -c 'import tomllib; print(tomllib.load(open("pyproject.toml","rb"))["project"]["version"])')"
SOURCE_SHA="$(git rev-parse HEAD)"
SOURCE_DATE_EPOCH="$(git log -1 --pretty=%ct)"

build() {
  docker build --quiet --no-cache --provenance=false \
    --build-arg "VERSION=${VERSION}" \
    --build-arg "GIT_SHA=${SOURCE_SHA}" \
    --build-arg "SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH}" \
    -t "$1" .
}

build "${PREFIX}-a"
sleep 2
build "${PREFIX}-b"

ID_A="$(docker image inspect "${PREFIX}-a" --format '{{.Id}}')"
ID_B="$(docker image inspect "${PREFIX}-b" --format '{{.Id}}')"

if [ "${ID_A}" != "${ID_B}" ]; then
  echo "not reproducible: ${ID_A} != ${ID_B}" >&2
  exit 1
fi

echo "reproducible build: ${ID_A}"
