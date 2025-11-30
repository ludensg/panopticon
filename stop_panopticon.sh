#!/usr/bin/env bash
set -euo pipefail

GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
RESET="\033[0m"

IMAGE_NAME="panopticon:latest"

echo -e "${GREEN}=== Stop Panopticon Docker Containers ===${RESET}"

# 1) Check Docker is available
if ! command -v docker >/dev/null 2>&1; then
  echo -e "${RED}✖ Docker is not installed or not on PATH.${RESET}"
  exit 1
fi

# 2) Find running containers for this image
CONTAINER_IDS=$(docker ps --filter "ancestor=${IMAGE_NAME}" -q)

if [[ -z "${CONTAINER_IDS}" ]]; then
  echo -e "${YELLOW}No running containers found for image '${IMAGE_NAME}'.${RESET}"
  exit 0
fi

echo -e "${YELLOW}Stopping the following container(s) based on '${IMAGE_NAME}':${RESET}"
echo "${CONTAINER_IDS}"

# 3) Stop them
docker stop ${CONTAINER_IDS}

echo -e "${GREEN}✔ All Panopticon containers have been stopped.${RESET}"
