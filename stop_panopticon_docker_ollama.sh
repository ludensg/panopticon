#!/usr/bin/env bash
set -euo pipefail

GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
RESET="\033[0m"

IMAGE_NAME="panopticon:latest"
APP_CONTAINER_NAME="panopticon-app"
OLLAMA_CONTAINER_NAME="panopticon-ollama"

echo -e "${GREEN}=== Stop Panopticon + Dockerized Ollama ===${RESET}"

# 1) Check Docker is available
if ! command -v docker >/dev/null 2>&1; then
  echo -e "${RED}✖ Docker is not installed or not on PATH.${RESET}"
  exit 1
fi

# 2) Stop Panopticon app containers (by name and by image, just in case)
APP_IDS_BY_NAME=$(docker ps --filter "name=^${APP_CONTAINER_NAME}$" -q || true)
APP_IDS_BY_IMAGE=$(docker ps --filter "ancestor=${IMAGE_NAME}" -q || true)

APP_IDS=$(printf "%s\n%s\n" "${APP_IDS_BY_NAME}" "${APP_IDS_BY_IMAGE}" | sort -u | tr '\n' ' ' | xargs -r echo || true)

if [[ -z "${APP_IDS// }" ]]; then
  echo -e "${YELLOW}No running Panopticon app containers found.${RESET}"
else
  echo -e "${YELLOW}Stopping Panopticon app container(s):${RESET}"
  echo "${APP_IDS}"
  docker stop ${APP_IDS}
  echo -e "${GREEN}✔ Panopticon app container(s) stopped.${RESET}"
fi

# 3) Stop the dedicated Ollama container (if running)
OLLAMA_ID=$(docker ps --filter "name=^${OLLAMA_CONTAINER_NAME}$" -q || true)

if [[ -z "${OLLAMA_ID// }" ]]; then
  echo -e "${YELLOW}No running Ollama container '${OLLAMA_CONTAINER_NAME}' found.${RESET}"
else
  echo -e "${YELLOW}Stopping Ollama container '${OLLAMA_CONTAINER_NAME}'...${RESET}"
  docker stop "${OLLAMA_CONTAINER_NAME}"
  echo -e "${GREEN}✔ Ollama container stopped.${RESET}"
fi

echo -e "${GREEN}All relevant containers have been handled.${RESET}"
