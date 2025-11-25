#!/usr/bin/env bash
set -euo pipefail

# Simple colors
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
RESET="\033[0m"

echo -e "${GREEN}=== Ollama Setup & Check Script ===${RESET}"
echo "This will help you:"
echo "  - Install Ollama if missing"
echo "  - Start the Ollama server if needed"
echo "  - Pull a model (e.g., llama3)"
echo "  - Optionally run a quick test"
echo

prompt_yes_no() {
  local prompt="$1"
  local default="${2:-y}"  # y or n
  local choice

  while true; do
    if [[ "$default" == "y" ]]; then
      read -r -p "$prompt [Y/n]: " choice || true
      choice="${choice:-y}"
    else
      read -r -p "$prompt [y/N]: " choice || true
      choice="${choice:-n}"
    fi

    case "$choice" in
      [Yy]*) return 0 ;;
      [Nn]*) return 1 ;;
      *) echo "Please answer y or n." ;;
    esac
  done
}

check_ollama_installed() {
  if command -v ollama >/dev/null 2>&1; then
    echo -e "${GREEN}✔ Ollama is already installed.${RESET}"
    return 0
  else
    echo -e "${YELLOW}⚠ Ollama is not installed.${RESET}"
    return 1
  fi
}

install_ollama() {
  echo -e "${GREEN}Installing Ollama via official install script...${RESET}"
  curl -fsSL https://ollama.com/install.sh | sh
  echo -e "${GREEN}Ollama installation script finished.${RESET}"
}

check_server_running() {
  # Try hitting the local API; returns 0 if up, non-zero otherwise.
  if curl -sS --max-time 1 http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo -e "${GREEN}✔ Ollama server is running on localhost:11434.${RESET}"
    return 0
  else
    echo -e "${YELLOW}⚠ Ollama server does not appear to be running.${RESET}"
    return 1
  fi
}

start_server() {
  echo -e "${GREEN}Starting Ollama server in the background (ollama serve)...${RESET}"
  # Start in background, redirect output
  nohup ollama serve >/dev/null 2>&1 &
  sleep 2
  if check_server_running; then
    echo -e "${GREEN}✔ Ollama server started successfully.${RESET}"
  else
    echo -e "${RED}✖ Failed to start Ollama server. Check logs or run 'ollama serve' manually.${RESET}"
    exit 1
  fi
}

model_exists() {
  local model="$1"
  if ollama list 2>/dev/null | awk '{print $1}' | grep -Fxq "$model"; then
    return 0
  else
    return 1
  fi
}

pull_model() {
  local model="$1"
  echo -e "${GREEN}Pulling model '${model}'...${RESET}"
  ollama pull "$model"
  echo -e "${GREEN}✔ Model '${model}' is ready.${RESET}"
}

run_test_query() {
  local model="$1"
  echo -e "${GREEN}Running a quick test with model '${model}'...${RESET}"
  ollama run "$model" "Write a short one-sentence reply so I can confirm you're working."
}

### Main flow ###

echo "Step 1: Check and optionally install Ollama"
if ! check_ollama_installed; then
  if prompt_yes_no "Do you want to install Ollama now?" "y"; then
    install_ollama
    # Re-check
    if ! check_ollama_installed; then
      echo -e "${RED}Ollama still not found in PATH after installation. Aborting.${RESET}"
      exit 1
    fi
  else
    echo -e "${RED}Ollama is required. Aborting.${RESET}"
    exit 1
  fi
fi
echo

echo "Step 2: Check and optionally start the Ollama server"
if ! check_server_running; then
  if prompt_yes_no "Do you want to start the Ollama server now (ollama serve)?" "y"; then
    start_server
  else
    echo -e "${RED}Ollama server is not running. Your app will not be able to use Ollama. Aborting.${RESET}"
    exit 1
  fi
fi
echo

echo "Step 3: Choose and ensure a model is available"
read -r -p "Enter the Ollama model name you want to use [default: llama3]: " OLLAMA_MODEL
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3}"
echo "Selected model: ${OLLAMA_MODEL}"

if model_exists "$OLLAMA_MODEL"; then
  echo -e "${GREEN}✔ Model '${OLLAMA_MODEL}' is already available.${RESET}"
else
  echo -e "${YELLOW}⚠ Model '${OLLAMA_MODEL}' is not present locally.${RESET}"
  if prompt_yes_no "Do you want to pull '${OLLAMA_MODEL}' now?" "y"; then
    pull_model "$OLLAMA_MODEL"
  else
    echo -e "${RED}Model not available. Aborting.${RESET}"
    exit 1
  fi
fi
echo

echo "Step 4: Optional test query"
if prompt_yes_no "Do you want to run a quick test query against '${OLLAMA_MODEL}'?" "y"; then
  run_test_query "$OLLAMA_MODEL"
else
  echo "Skipping test query."
fi
echo

echo -e "${GREEN}All done.${RESET}"
echo "Ollama server is running and model '${OLLAMA_MODEL}' is ready."
echo "You can set OLLAMA_MODEL=${OLLAMA_MODEL} in your environment if you like:"
echo
echo "  export OLLAMA_MODEL=\"${OLLAMA_MODEL}\""
echo
echo "Then your app can use Ollama via that model name."
