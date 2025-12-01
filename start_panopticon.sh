#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------
# Colors for nicer UX
# ------------------------------------------------------------
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
BLUE="\033[1;34m"
RESET="\033[0m"

echo -e "${GREEN}=== Panopticon (Docker) Starter ===${RESET}"
echo
echo -e "${BLUE}This script will:${RESET}"
echo "  1) Verify you're in the Panopticon project directory."
echo "  2) Check that Docker is installed and the daemon is running."
echo "  3) Optionally run an Ollama host setup script (if present)."
echo "  4) Help you configure:"
echo "       - OpenAI (API key + model)"
echo "       - Ollama (host + model + server check)"
echo "       - Pixabay (for feed images)"
echo "       - News API (for news-based posts, if your code uses it)"
echo "  5) Ask which LLM backends you want to use (OpenAI / Ollama / both / none)."
echo "  6) Build the Docker image: panopticon:latest."
echo "  7) Run the container and expose the Streamlit app on a host port."
echo
echo "You can pre-configure keys/hosts/models inside this script so an evaluator"
echo "can just run it and go straight to the demo."
echo

# ------------------------------------------------------------
# 0) Always operate from the script's directory
# ------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ------------------------------------------------------------
# 1) Confirm we're in the right directory
# ------------------------------------------------------------
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

# ------------------------------------------------------------
# 2) Check Docker availability
# ------------------------------------------------------------
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

# ------------------------------------------------------------
# 3) Optional: run host-side Ollama setup script if present
# ------------------------------------------------------------
if [[ -f "./setup_ollama.sh" ]]; then
  echo -e "${BLUE}Found setup_ollama.sh (host-side helper for Ollama).${RESET}"
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

# ------------------------------------------------------------
# 4) Optional defaults for evaluators (set in-script to avoid prompts)
#
# If you set any of these to non-empty values, the script will use them
# and will NOT prompt the user for that setting.
#
# Example:
#   OPENAI_API_KEY_DEFAULT="sk-xxx"
#   OPENAI_MODEL_DEFAULT="gpt-4.1-mini"
#   OLLAMA_HOST_DEFAULT="http://host.docker.internal:11434"
#   OLLAMA_MODEL_DEFAULT="tinyllama"
PIXABAY_API_KEY_DEFAULT="51446488-f00733ed25756b94db32f5de3"
NEWS_API_KEY_DEFAULT="6e9c430fad3946a2b27b51bb5e1b3321"
# ------------------------------------------------------------

OPENAI_API_KEY_DEFAULT="${OPENAI_API_KEY_DEFAULT:-}"
OPENAI_MODEL_DEFAULT="${OPENAI_MODEL_DEFAULT:-gpt-4.1-mini}"

OLLAMA_HOST_DEFAULT="${OLLAMA_HOST_DEFAULT:-}"
OLLAMA_MODEL_DEFAULT="${OLLAMA_MODEL_DEFAULT:-tinyllama}"

PIXABAY_API_KEY_DEFAULT="${PIXABAY_API_KEY_DEFAULT:-}"
NEWS_API_KEY_DEFAULT="${NEWS_API_KEY_DEFAULT:-}"

# ------------------------------------------------------------
# 5) Configure Pixabay key (for image search in feeds)
# ------------------------------------------------------------
echo
echo -e "${BLUE}Configuring Pixabay (for feed images)...${RESET}"

if [[ -n "$PIXABAY_API_KEY_DEFAULT" ]]; then
  # Use in-script default, no prompt
  export PIXABAY_API_KEY="$PIXABAY_API_KEY_DEFAULT"
  echo -e "${GREEN}✔ Using PIXABAY_API_KEY_DEFAULT set inside this script.${RESET}"
elif [[ -n "${PIXABAY_API_KEY:-}" ]]; then
  echo -e "${GREEN}Detected existing PIXABAY_API_KEY in your environment.${RESET}"
  read -r -p "Use this existing PIXABAY_API_KEY inside the container? [Y/n]: " USE_PX_ENV
  USE_PX_ENV="${USE_PX_ENV:-y}"
  if [[ ! "$USE_PX_ENV" =~ ^[Yy]$ ]]; then
    unset PIXABAY_API_KEY
  fi
fi

if [[ -z "${PIXABAY_API_KEY:-}" ]]; then
  echo -e "${YELLOW}⚠ PIXABAY_API_KEY is not set.${RESET}"
  echo "   Without it, the app will still run, but some feed images may be disabled."
  read -r -p "Set PIXABAY_API_KEY for this run? [y/N]: " SET_PX
  SET_PX="${SET_PX:-n}"
  if [[ "$SET_PX" =~ ^[Yy]$ ]]; then
    read -r -p "Enter your Pixabay API key: " INPUT_PX_KEY
    export PIXABAY_API_KEY="$INPUT_PX_KEY"
    echo -e "${GREEN}✔ PIXABAY_API_KEY set for this run.${RESET}"
  else
    echo -e "${YELLOW}Continuing without Pixabay image search.${RESET}"
  fi
else
  echo -e "${GREEN}✔ Using PIXABAY_API_KEY=${PIXABAY_API_KEY:+(set)}${RESET}"
fi

# ------------------------------------------------------------
# 5B) Configure News API key (for curated news in feeds)
# ------------------------------------------------------------
echo
echo -e "${BLUE}Configuring News API (for news-based posts, if enabled)...${RESET}"

if [[ -n "$NEWS_API_KEY_DEFAULT" ]]; then
  # Use in-script default, no prompt
  export NEWS_API_KEY="$NEWS_API_KEY_DEFAULT"
  echo -e "${GREEN}✔ Using NEWS_API_KEY_DEFAULT set inside this script.${RESET}"
elif [[ -n "${NEWS_API_KEY:-}" ]]; then
  echo -e "${GREEN}Detected existing NEWS_API_KEY in your environment.${RESET}"
  read -r -p "Use this existing NEWS_API_KEY inside the container? [Y/n]: " USE_NEWS_ENV
  USE_NEWS_ENV="${USE_NEWS_ENV:-y}"
  if [[ ! "$USE_NEWS_ENV" =~ ^[Yy]$ ]]; then
    unset NEWS_API_KEY
  fi
fi

if [[ -z "${NEWS_API_KEY:-}" ]]; then
  echo -e "${YELLOW}⚠ NEWS_API_KEY is not set.${RESET}"
  echo "   Without it, news-based posts may be limited or disabled."
  read -r -p "Set NEWS_API_KEY for this run? [y/N]: " SET_NEWS
  SET_NEWS="${SET_NEWS:-n}"
  if [[ "$SET_NEWS" =~ ^[Yy]$ ]]; then
    read -r -p "Enter your News API key: " INPUT_NEWS_KEY
    export NEWS_API_KEY="$INPUT_NEWS_KEY"
    echo -e "${GREEN}✔ NEWS_API_KEY set for this run.${RESET}"
  else
    echo -e "${YELLOW}Continuing without News API integration.${RESET}"
  fi
else
  echo -e "${GREEN}✔ Using NEWS_API_KEY=${NEWS_API_KEY:+(set)}${RESET}"
fi

# ------------------------------------------------------------
# 6) Helper functions to configure OpenAI and Ollama
# ------------------------------------------------------------

configure_openai() {
  echo
  echo -e "${BLUE}Configuring OpenAI backend...${RESET}"

  # API key
  if [[ -n "$OPENAI_API_KEY_DEFAULT" ]]; then
    export OPENAI_API_KEY="$OPENAI_API_KEY_DEFAULT"
    echo -e "${GREEN}✔ Using OPENAI_API_KEY_DEFAULT set inside the script.${RESET}"
  elif [[ -n "${OPENAI_API_KEY:-}" ]]; then
    echo -e "${GREEN}Detected existing OPENAI_API_KEY in your environment.${RESET}"
    read -r -p "Use this existing OPENAI_API_KEY inside the container? [Y/n]: " USE_OAI_ENV
    USE_OAI_ENV="${USE_OAI_ENV:-y}"
    if [[ ! "$USE_OAI_ENV" =~ ^[Yy]$ ]]; then
      unset OPENAI_API_KEY
      read -r -s -p "Enter your OpenAI API key (or leave blank to skip OpenAI): " INPUT_KEY
      echo
      if [[ -n "$INPUT_KEY" ]]; then
        export OPENAI_API_KEY="$INPUT_KEY"
        echo -e "${GREEN}✔ OPENAI_API_KEY set for this run.${RESET}"
      else
        echo -e "${YELLOW}⚠ No OpenAI key provided; OpenAI calls will fail if selected in the app.${RESET}"
      fi
    else
      echo -e "${GREEN}✔ Keeping existing OPENAI_API_KEY.${RESET}"
    fi
  else
    echo -e "${YELLOW}⚠ OPENAI_API_KEY is not set.${RESET}"
    echo "   You can still run the app using Ollama-only if you prefer."
    read -r -p "Set OPENAI_API_KEY for this run? [y/N]: " SET_OAI
    SET_OAI="${SET_OAI:-n}"
    if [[ "$SET_OAI" =~ ^[Yy]$ ]]; then
      read -r -s -p "Enter your OpenAI API key: " INPUT_KEY
      echo
      export OPENAI_API_KEY="$INPUT_KEY"
      echo -e "${GREEN}✔ OPENAI_API_KEY set for this run.${RESET}"
    else
      echo -e "${YELLOW}Continuing without OpenAI; OpenAI backend will not work.${RESET}"
    fi
  fi

  # Model
  if [[ -z "${OPENAI_MODEL:-}" ]]; then
    read -r -p "Preferred OpenAI model [default: ${OPENAI_MODEL_DEFAULT}]: " INPUT_OPENAI_MODEL
    export OPENAI_MODEL="${INPUT_OPENAI_MODEL:-$OPENAI_MODEL_DEFAULT}"
    echo -e "${GREEN}✔ OPENAI_MODEL set to: ${OPENAI_MODEL}${RESET}"
  else
    echo -e "${GREEN}✔ OPENAI_MODEL already set: ${OPENAI_MODEL}${RESET}"
  fi
}

configure_ollama() {
  echo
  echo -e "${BLUE}Configuring Ollama (local) backend...${RESET}"

  # Host
  if [[ -n "$OLLAMA_HOST_DEFAULT" ]]; then
    export OLLAMA_HOST="$OLLAMA_HOST_DEFAULT"
    echo -e "${GREEN}✔ Using OLLAMA_HOST_DEFAULT set inside the script: $OLLAMA_HOST${RESET}"
  elif [[ -n "${OLLAMA_HOST:-}" ]]; then
    echo -e "${GREEN}✔ OLLAMA_HOST already set in the environment: ${OLLAMA_HOST}${RESET}"
  else
    local default_host="http://localhost:11434"
    echo "Panopticon needs the container to reach your Ollama server on the host."
    echo "For Docker Desktop (Mac/Windows), 'http://host.docker.internal:11434' usually works."
    echo "On native Linux, you might prefer 'http://localhost:11434' with '--network=host'."
    read -r -p "Ollama host URL [default: ${default_host}]: " INPUT_OLLAMA_HOST
    export OLLAMA_HOST="${INPUT_OLLAMA_HOST:-$default_host}"
    echo -e "${GREEN}✔ OLLAMA_HOST set to: ${OLLAMA_HOST}${RESET}"
  fi

  # Model
  if [[ -n "$OLLAMA_MODEL_DEFAULT" ]]; then
    export OLLAMA_MODEL="$OLLAMA_MODEL_DEFAULT"
    echo -e "${GREEN}✔ Using OLLAMA_MODEL_DEFAULT set inside the script: $OLLAMA_MODEL${RESET}"
  elif [[ -n "${OLLAMA_MODEL:-}" ]]; then
    echo -e "${GREEN}✔ OLLAMA_MODEL already set in the environment: ${OLLAMA_MODEL}${RESET}"
  else
    local default_model="tinyllama"
    read -r -p "Default Ollama model name [default: ${default_model}]: " INPUT_OLLAMA_MODEL
    export OLLAMA_MODEL="${INPUT_OLLAMA_MODEL:-$default_model}"
    echo -e "${GREEN}✔ OLLAMA_MODEL set to: ${OLLAMA_MODEL}${RESET}"
  fi

  # Manage Ollama server (best-effort)
  if [[ -n "${OLLAMA_HOST:-}" ]]; then
    echo
    echo -e "${GREEN}Checking Ollama server at ${OLLAMA_HOST}...${RESET}"

    # Normalize missing scheme
    _OLLAMA_HOST="${OLLAMA_HOST}"
    if [[ ! "$_OLLAMA_HOST" =~ ^https?:// ]]; then
      _OLLAMA_HOST="http://${_OLLAMA_HOST}"
    fi

    if curl -fsS "${_OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
      echo -e "${GREEN}✔ Ollama server appears to be running at ${_OLLAMA_HOST}.${RESET}"
      read -r -p "Restart Ollama server for a clean session? [y/N]: " RESTART_OLL
      RESTART_OLL="${RESTART_OLL:-n}"
      if [[ "$RESTART_OLL" =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Attempting to stop existing 'ollama serve' processes...${RESET}"
        pkill -f "ollama serve" >/dev/null 2>&1 || true
        sleep 1
        echo -e "${GREEN}Starting new Ollama server in background...${RESET}"
        (ollama serve > /tmp/ollama_server.log 2>&1 &) || {
          echo -e "${RED}✖ Failed to start Ollama server automatically.${RESET}"
          echo "You may need to start it manually (e.g., 'ollama serve')."
        }
        sleep 2
        if curl -fsS "${_OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
          echo -e "${GREEN}✔ Ollama server is now responding at ${_OLLAMA_HOST}.${RESET}"
        else
          echo -e "${YELLOW}⚠ Could not confirm Ollama at ${_OLLAMA_HOST}.${RESET}"
        fi
      fi
    else
      echo -e "${YELLOW}⚠ No Ollama server detected at ${_OLLAMA_HOST}.${RESET}"
      read -r -p "Start a new Ollama server in the background now? [y/N]: " START_OLL
      START_OLL="${START_OLL:-n}"
      if [[ "$START_OLL" =~ ^[Yy]$ ]]; then
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
        fi
      fi
    fi
  fi
}

# ------------------------------------------------------------
# 7) Choose which LLM backends to use (OpenAI / Ollama / both / none)
# ------------------------------------------------------------
echo
echo -e "${BLUE}Step: Choose which LLM backends you want to enable for this run.${RESET}"
echo "You can use OpenAI, Ollama, or both. The app will still run if you select"
echo "'none', but any LLM-based features will fail gracefully."
echo
echo "  1) OpenAI only"
echo "  2) Ollama only (local)"
echo "  3) OpenAI + Ollama"
echo "  4) None (run UI without LLMs)"
echo

read -r -p "Enter your choice [1-4]: " LLM_CHOICE
LLM_CHOICE="${LLM_CHOICE:-1}"

SELECTED_LLMS=()

case "$LLM_CHOICE" in
  1)
    SELECTED_LLMS=("openai")
    configure_openai
    ;;
  2)
    SELECTED_LLMS=("ollama")
    configure_ollama
    ;;
  3)
    SELECTED_LLMS=("openai" "ollama")
    configure_openai
    configure_ollama
    ;;
  4)
    SELECTED_LLMS=()
    echo -e "${YELLOW}⚠ No LLM backends selected. The UI will run, but LLM calls may fail or be skipped.${RESET}"
    ;;
  *)
    echo -e "${YELLOW}⚠ Unknown choice '${LLM_CHOICE}', defaulting to 'OpenAI only'.${RESET}"
    SELECTED_LLMS=("openai")
    configure_openai
    ;;
esac

if ((${#SELECTED_LLMS[@]} == 0)); then
  export PANOPTICON_LLM_BACKENDS="none"
else
  PANOPTICON_LLM_BACKENDS="$(IFS=,; echo "${SELECTED_LLMS[*]}")"
  export PANOPTICON_LLM_BACKENDS
  echo -e "${GREEN}✔ Selected LLM backends: ${PANOPTICON_LLM_BACKENDS}${RESET}"
fi

# ------------------------------------------------------------
# 8) Ask which port to run on (host side)
# ------------------------------------------------------------
echo
read -r -p "Streamlit port on HOST [default 8501]: " PORT
PORT="${PORT:-8501}"

# ------------------------------------------------------------
# 9) Build Docker image (always, cached builds are quick)
# ------------------------------------------------------------
IMAGE_NAME="panopticon:latest"

echo
echo -e "${BLUE}Building Docker image '${IMAGE_NAME}'...${RESET}"
docker build -t "${IMAGE_NAME}" "$SCRIPT_DIR"
echo -e "${GREEN}✔ Docker image built (or updated).${RESET}"

# ------------------------------------------------------------
# 10) Decide whether to use --network=host (for Ollama on native Linux)
# ------------------------------------------------------------
USE_HOST_NETWORK="n"
if [[ " ${SELECTED_LLMS[*]} " == *" ollama "* ]]; then
  echo
  echo -e "${BLUE}Networking for Ollama:${RESET}"
  echo "If you're running Docker on native Linux and Ollama on the same host,"
  echo "you can use '--network=host' so the container can reach Ollama via 'localhost:11434'."
  echo "If you're using Docker Desktop (Mac/Windows), it's usually better to keep"
  echo "the default bridge network and use 'host.docker.internal:11434' instead."
  read -r -p "Use '--network=host' for this container? [y/N]: " USE_HOST_NETWORK
  USE_HOST_NETWORK="${USE_HOST_NETWORK:-n}"
fi

# ------------------------------------------------------------
# 11) Prepare docker run command
# ------------------------------------------------------------
DOCKER_RUN_CMD=(docker run --rm -p "${PORT}:8501")

# Pass keys/hosts/models into the container
DOCKER_RUN_CMD+=(
  -e OPENAI_API_KEY
  -e OPENAI_MODEL
  -e PIXABAY_API_KEY
  -e NEWS_API_KEY
  -e OLLAMA_HOST
  -e OLLAMA_MODEL
  -e PANOPTICON_LLM_BACKENDS
)

if [[ "${USE_HOST_NETWORK}" =~ ^[Yy]$ ]]; then
  DOCKER_RUN_CMD+=(--network=host)
fi

DOCKER_RUN_CMD+=("${IMAGE_NAME}")

echo
echo -e "${GREEN}Starting Panopticon Docker container on host port ${PORT}...${RESET}"
echo "  - Image:  ${IMAGE_NAME}"
echo "  - URL:    http://localhost:${PORT}"
echo "  - LLMs:   ${PANOPTICON_LLM_BACKENDS}"
echo
echo "Use Ctrl+C in this terminal to stop the container."
echo

# ------------------------------------------------------------
# 12) Run the container
# ------------------------------------------------------------
exec "${DOCKER_RUN_CMD[@]}"
