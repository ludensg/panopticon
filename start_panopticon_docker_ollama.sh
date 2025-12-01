#!/usr/bin/env bash
set -euo pipefail

# Simple colors
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
RESET="\033[0m"

echo -e "${GREEN}=== Panopticon + Dockerized Ollama Starter ===${RESET}"

# -------------------------------------------------------------------
# 0) Always operate from the script's directory
# -------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# -------------------------------------------------------------------
# 1) Confirm we're in the right directory
# -------------------------------------------------------------------
if [[ ! -f "app.py" ]]; then
  echo -e "${RED}✖ app.py not found in current directory.${RESET}"
  echo "Run this script from the Panopticon project root (where app.py is)."
  exit 1
fi

if [[ ! -f "Dockerfile" ]]; then
  echo -e "${RED}✖ Dockerfile not found in current directory.${RESET}"
  echo "Make sure the Dockerfile is in the project root."
  exit 1
fi

# -------------------------------------------------------------------
# 2) Check Docker availability
# -------------------------------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
  echo -e "${RED}✖ Docker is not installed or not on PATH.${RESET}"
  echo "Please install Docker and try again."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo -e "${RED}✖ Docker daemon does not seem to be running.${RESET}"
  echo "Start Docker (e.g., 'sudo systemctl start docker' or Docker Desktop) and retry."
  exit 1
fi

# -------------------------------------------------------------------
# 3) Optional: OpenAI API key (for OpenAI backend)
# -------------------------------------------------------------------
if [[ -n "${OPENAI_API_KEY:-}" ]]; then
  echo -e "${GREEN}Detected existing OPENAI_API_KEY in your environment.${RESET}"
  read -r -p "Use this existing OPENAI_API_KEY inside the container? [Y/n]: " USE_OAI_ENV
  USE_OAI_ENV="${USE_OAI_ENV:-y}"
  if [[ ! "$USE_OAI_ENV" =~ ^[Yy]$ ]]; then
    unset OPENAI_API_KEY
  fi
fi

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo -e "${YELLOW}⚠ OPENAI_API_KEY is not set.${RESET}"
  echo "You can still run the app without OpenAI (Ollama-only)."
  read -r -p "Set OPENAI_API_KEY for this run? [y/N]: " SET_OAI
  SET_OAI="${SET_OAI:-n}"
  if [[ "$SET_OAI" =~ ^[Yy]$ ]]; then
    # -s to not echo key to terminal
    read -r -s -p "Enter your OpenAI API key: " INPUT_KEY
    echo
    export OPENAI_API_KEY="$INPUT_KEY"
    echo -e "${GREEN}✔ OPENAI_API_KEY set for this run.${RESET}"
  fi
fi

# -------------------------------------------------------------------
# 4) Optional: Pixabay API key (for image search)
# -------------------------------------------------------------------
if [[ -n "${PIXABAY_API_KEY:-}" ]]; then
  echo -e "${GREEN}Detected existing PIXABAY_API_KEY in your environment.${RESET}"
  read -r -p "Use this existing PIXABAY_API_KEY inside the container? [Y/n]: " USE_PX_ENV
  USE_PX_ENV="${USE_PX_ENV:-y}"
  if [[ ! "$USE_PX_ENV" =~ ^[Yy]$ ]]; then
    unset PIXABAY_API_KEY
  fi
fi

if [[ -z "${PIXABAY_API_KEY:-}" ]]; then
  echo -e "${YELLOW}⚠ PIXABAY_API_KEY is not set.${RESET}"
  echo "Image search in feeds will be disabled without it."
  read -r -p "Set PIXABAY_API_KEY for this run? [y/N]: " SET_PX
  SET_PX="${SET_PX:-n}"
  if [[ "$SET_PX" =~ ^[Yy]$ ]]; then
    read -r -p "Enter your Pixabay API key: " INPUT_PX_KEY
    export PIXABAY_API_KEY="$INPUT_PX_KEY"
    echo -e "${GREEN}✔ PIXABAY_API_KEY set for this run.${RESET}"
  fi
fi

# -------------------------------------------------------------------
# 5) Ask which port to run Streamlit on (host side)
# -------------------------------------------------------------------
read -r -p "Streamlit port on HOST [default 8501]: " PORT
PORT="${PORT:-8501}"

# -------------------------------------------------------------------
# 6) Docker network + Ollama container
# -------------------------------------------------------------------
NETWORK_NAME="panopticon-net"
OLLAMA_CONTAINER_NAME="panopticon-ollama"
OLLAMA_IMAGE="ollama/ollama"

echo
echo -e "${GREEN}Setting up Docker network '${NETWORK_NAME}' and Ollama container...${RESET}"

# Ensure network exists
if ! docker network ls --format '{{.Name}}' | grep -q "^${NETWORK_NAME}$"; then
  echo -e "${GREEN}Creating Docker network '${NETWORK_NAME}'...${RESET}"
  docker network create "${NETWORK_NAME}"
else
  echo -e "${GREEN}Docker network '${NETWORK_NAME}' already exists.${RESET}"
fi

# Ensure Ollama image is present (pull if needed)
if ! docker image ls --format '{{.Repository}}:{{.Tag}}' | grep -q "^${OLLAMA_IMAGE}"; then
  echo -e "${GREEN}Pulling Ollama image '${OLLAMA_IMAGE}'...${RESET}"
  docker pull "${OLLAMA_IMAGE}"
fi

# Start or create the Ollama container
if docker ps --all --format '{{.Names}}' | grep -q "^${OLLAMA_CONTAINER_NAME}$"; then
  echo -e "${GREEN}Starting existing Ollama container '${OLLAMA_CONTAINER_NAME}'...${RESET}"
  docker start "${OLLAMA_CONTAINER_NAME}" >/dev/null
else
  echo -e "${GREEN}Creating and starting new Ollama container '${OLLAMA_CONTAINER_NAME}'...${RESET}"
  docker run -d \
    --name "${OLLAMA_CONTAINER_NAME}" \
    --network "${NETWORK_NAME}" \
    -p 11434:11434 \
    "${OLLAMA_IMAGE}"
fi

# Give Ollama a second to start
sleep 2

# Optional: check health
echo -e "${GREEN}Checking Ollama API health on http://localhost:11434/api/tags ...${RESET}"
if curl -fsS "http://localhost:11434/api/tags" >/dev/null 2>&1; then
  echo -e "${GREEN}✔ Ollama is responding on http://localhost:11434.${RESET}"
else
  echo -e "${YELLOW}⚠ Could not confirm Ollama at http://localhost:11434.${RESET}"
  echo "You can still continue; Panopticon will attempt to use Ollama if selected."
fi

# This is the host the Panopticon container should use to reach Ollama
export OLLAMA_HOST="http://${OLLAMA_CONTAINER_NAME}:11434"
echo -e "${GREEN}✔ OLLAMA_HOST set to ${OLLAMA_HOST} for the Panopticon container.${RESET}"

# -------------------------------------------------------------------
# 7) Build Panopticon Docker image
# -------------------------------------------------------------------
IMAGE_NAME="panopticon:latest"

echo
echo -e "${GREEN}Building Docker image '${IMAGE_NAME}'...${RESET}"
docker build -t "${IMAGE_NAME}" "$SCRIPT_DIR"
echo -e "${GREEN}✔ Docker image built.${RESET}"

# -------------------------------------------------------------------
# 8) Run Panopticon container
# -------------------------------------------------------------------
APP_CONTAINER_NAME="panopticon-app"

# If an old container with this name exists, remove it to avoid conflicts
if docker ps --all --format '{{.Names}}' | grep -q "^${APP_CONTAINER_NAME}$"; then
  echo -e "${YELLOW}Removing existing container '${APP_CONTAINER_NAME}'...${RESET}"
  docker rm -f "${APP_CONTAINER_NAME}" >/dev/null 2>&1 || true
fi

DOCKER_RUN_CMD=(
  docker run
  --rm
  --name "${APP_CONTAINER_NAME}"
  --network "${NETWORK_NAME}"
  -p "${PORT}:8501"
)

# Pass keys into the container if set
if [[ -n "${OPENAI_API_KEY:-}" ]]; then
  DOCKER_RUN_CMD+=(-e "OPENAI_API_KEY=${OPENAI_API_KEY}")
fi

if [[ -n "${PIXABAY_API_KEY:-}" ]]; then
  DOCKER_RUN_CMD+=(-e "PIXABAY_API_KEY=${PIXABAY_API_KEY}")
fi

if [[ -n "${OLLAMA_HOST:-}" ]]; then
  DOCKER_RUN_CMD+=(-e "OLLAMA_HOST=${OLLAMA_HOST}")
fi

DOCKER_RUN_CMD+=("${IMAGE_NAME}")

echo
echo -e "${GREEN}Starting Panopticon container '${APP_CONTAINER_NAME}' on port ${PORT}...${RESET}"
echo "Use Ctrl+C to stop the app container (Ollama will continue running unless you stop it explicitly)."
echo

exec "${DOCKER_RUN_CMD[@]}"
