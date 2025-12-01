#!/usr/bin/env bash
set -euo pipefail

# Simple colors
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
RESET="\033[0m"

echo -e "${GREEN}=== Panopticon (Docker) Starter ===${RESET}"

# 0) Always operate from the script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1) Confirm we're in the right directory
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

# 2) Check Docker availability
if ! command -v docker >/dev/null 2>&1; then
  echo -e "${RED}✖ Docker is not installed or not on PATH.${RESET}"
  echo "Please install Docker and try again."
  exit 1
fi

# Optional: check Docker daemon
if ! docker info >/dev/null 2>&1; then
  echo -e "${RED}✖ Docker daemon does not seem to be running.${RESET}"
  echo "Start Docker (e.g., 'sudo systemctl start docker' or Docker Desktop) and retry."
  exit 1
fi

# 3) Optional: Ollama setup script (for host-side Ollama)
if [[ -f "./setup_ollama.sh" ]]; then
  read -r -p "Run Ollama setup/check on host first? [Y/n]: " RUN_OLLAMA
  RUN_OLLAMA="${RUN_OLLAMA:-y}"
  if [[ "$RUN_OLLAMA" =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}Running ./setup_ollama.sh on host...${RESET}"
    ./setup_ollama.sh
  else
    echo "Skipping Ollama setup."
  fi
else
  echo -e "${YELLOW}Note: setup_ollama.sh not found. Skipping Ollama host setup.${RESET}"
fi

# 4) Handle OpenAI API key
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
  echo "You can still run the app without OpenAI (e.g., Ollama-only),"
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

# 5) Handle Pixabay API key
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

# 6) Optional: Ollama host (for local Ollama on the host machine)
# Only relevant if your app actually reads OLLAMA_HOST
if [[ -z "${OLLAMA_HOST:-}" ]]; then
  read -r -p "Do you want to configure OLLAMA_HOST for local Ollama? [y/N]: " SET_OLLAMA_HOST
  SET_OLLAMA_HOST="${SET_OLLAMA_HOST:-n}"
  if [[ "$SET_OLLAMA_HOST" =~ ^[Yy]$ ]]; then
    echo "For Linux host Ollama, a common value is: http://host.docker.internal:11434 or http://localhost:11434"
    read -r -p "Enter OLLAMA_HOST URL: " INPUT_OLLAMA_HOST
    export OLLAMA_HOST="$INPUT_OLLAMA_HOST"
    echo -e "${GREEN}✔ OLLAMA_HOST set for this run.${RESET}"
  fi
fi

# 6B) Optional: manage Ollama server (restart/start)
if [[ -n "${OLLAMA_HOST:-}" ]]; then
  echo
  echo -e "${GREEN}Checking Ollama server at ${OLLAMA_HOST}...${RESET}"

  # Normalize missing scheme (user might have entered host.docker.internal:11434)
  _OLLAMA_HOST="${OLLAMA_HOST}"
  if [[ ! "$_OLLAMA_HOST" =~ ^https?:// ]]; then
    _OLLAMA_HOST="http://${_OLLAMA_HOST}"
  fi

  if curl -fsS "${_OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
    echo -e "${GREEN}✔ Ollama server appears to be running at ${_OLLAMA_HOST}.${RESET}"
    read -r -p "Restart Ollama server for a clean session? [y/N]: " RESTART_OLLAMA
    RESTART_OLLAMA="${RESTART_OLLAMA:-n}"
    if [[ "$RESTART_OLLAMA" =~ ^[Yy]$ ]]; then
      echo -e "${YELLOW}Attempting to stop existing Ollama 'serve' processes...${RESET}"
      # Best-effort kill of any 'ollama serve' procs; ignore errors
      pkill -f "ollama serve" >/dev/null 2>&1 || true
      sleep 1

      echo -e "${GREEN}Starting new Ollama server in background...${RESET}"
      # Run in background; log to /tmp so it doesn't spam the terminal
      (ollama serve > /tmp/ollama_server.log 2>&1 &) || {
        echo -e "${RED}✖ Failed to start Ollama server automatically.${RESET}"
        echo "You may need to start it manually (e.g., 'ollama serve')."
      }

      # Give it a moment to boot, then re-check
      sleep 2
      if curl -fsS "${_OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
        echo -e "${GREEN}✔ Ollama server is now responding at ${_OLLAMA_HOST}.${RESET}"
      else
        echo -e "${YELLOW}⚠ Could not confirm Ollama at ${_OLLAMA_HOST}.${RESET}"
        echo "You can still try using the Ollama backend, but generation may fail."
      fi
    fi
  else
    echo -e "${YELLOW}⚠ No Ollama server detected at ${_OLLAMA_HOST}.${RESET}"
    read -r -p "Start a new Ollama server in the background now? [y/N]: " START_OLLAMA
    START_OLLAMA="${START_OLLAMA:-n}"
    if [[ "$START_OLLAMA" =~ ^[Yy]$ ]]; then
      echo -e "${GREEN}Starting Ollama server in background...${RESET}"
      (ollama serve > /tmp/ollama_server.log 2>&1 &) || {
        echo -e "${RED}✖ Failed to start Ollama server automatically.${RESET}"
        echo "You may need to start it manually (e.g., 'ollama serve')."
      }
      sleep 2
      if curl -fsS "${_OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
        echo -e "${GREEN}✔ Ollama server is now responding at ${_OLLAMA_HOST}.${RESET}"
      else
        echo -e "${YELLOW}⚠ Still cannot confirm Ollama at ${_OLLAMA_HOST}.${RESET}"
        echo "Check your Ollama install or host/port, and restart this script if needed."
      fi
    fi
  fi
fi


# 7) Ask which port to run on
read -r -p "Streamlit port on HOST [default 8501]: " PORT
PORT="${PORT:-8501}"

# 8) Build Docker image (always, for simplicity; fast if cached)
IMAGE_NAME="panopticon:latest"

echo
echo -e "${GREEN}Building Docker image '${IMAGE_NAME}'...${RESET}"
docker build -t "${IMAGE_NAME}" "$SCRIPT_DIR"

echo -e "${GREEN}✔ Docker image built.${RESET}"

# 9) Prepare docker run command
DOCKER_RUN_CMD=(docker run --rm -p "${PORT}:8501")

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

# If you want to support host-network Ollama on Linux, you could uncomment:
DOCKER_RUN_CMD+=(--network=host)

DOCKER_RUN_CMD+=("${IMAGE_NAME}")

echo
echo -e "${GREEN}Starting Panopticon Docker container on port ${PORT}...${RESET}"
echo "Use Ctrl+C to stop the container."
echo

# 10) Run the container
exec "${DOCKER_RUN_CMD[@]}"
