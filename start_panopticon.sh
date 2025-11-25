#!/usr/bin/env bash
set -euo pipefail

# Simple colors
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
RESET="\033[0m"

echo -e "${GREEN}=== Panopticon Project Starter ===${RESET}"

# 1) Confirm we're in the right directory
if [[ ! -f "app.py" ]]; then
  echo -e "${RED}✖ app.py not found in current directory.${RESET}"
  echo "Run this script from the Panopticon project root (where app.py is)."
  exit 1
fi

# 2) Optionally run Ollama setup script
if [[ -f "./setup_ollama.sh" ]]; then
  read -r -p "Run Ollama setup/check first? [Y/n]: " RUN_OLLAMA
  RUN_OLLAMA="${RUN_OLLAMA:-y}"
  if [[ "$RUN_OLLAMA" =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}Running ./setup_ollama.sh ...${RESET}"
    ./setup_ollama.sh
  else
    echo "Skipping Ollama setup."
  fi
else
  echo -e "${YELLOW}Note: setup_ollama.sh not found. Skipping Ollama setup.${RESET}"
fi

# 3) Ensure virtualenv exists
if [[ ! -d "venv" ]]; then
  echo -e "${YELLOW}⚠ Python virtualenv 'venv' not found.${RESET}"
  read -r -p "Create a new virtualenv at ./venv now? [Y/n]: " CREATE_VENV
  CREATE_VENV="${CREATE_VENV:-y}"
  if [[ "$CREATE_VENV" =~ ^[Yy]$ ]]; then
    python3 -m venv venv
    echo -e "${GREEN}✔ Created virtualenv at ./venv${RESET}"
  else
    echo -e "${RED}Virtualenv is required for this starter script. Aborting.${RESET}"
    exit 1
  fi
fi

# 4) Activate venv
# shellcheck disable=SC1091
source venv/bin/activate
echo -e "${GREEN}✔ Activated virtualenv.${RESET}"

# 5) Ensure dependencies (optional lightweight check)
if ! python -c "import streamlit" >/dev/null 2>&1; then
  echo -e "${YELLOW}⚠ streamlit not found in this venv.${RESET}"
  read -r -p "Install dependencies from requirements.txt now? [Y/n]: " INSTALL_REQ
  INSTALL_REQ="${INSTALL_REQ:-y}"
  if [[ "$INSTALL_REQ" =~ ^[Yy]$ ]]; then
    if [[ -f "requirements.txt" ]]; then
      python -m pip install -r requirements.txt
    else
      echo -e "${RED}requirements.txt not found. Please install dependencies manually.${RESET}"
    fi
  fi
fi

# 6) Check OpenAI key (for when backend=openai)
if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo -e "${YELLOW}⚠ OPENAI_API_KEY is not set in the environment.${RESET}"
  echo "You can still use Ollama backend only."
  read -r -p "Set OPENAI_API_KEY for this session now? [y/N]: " SET_OAI
  SET_OAI="${SET_OAI:-n}"
  if [[ "$SET_OAI" =~ ^[Yy]$ ]]; then
    read -r -p "Enter your OpenAI API key: " INPUT_KEY
    export OPENAI_API_KEY="$INPUT_KEY"
    echo -e "${GREEN}✔ OPENAI_API_KEY set for this shell session.${RESET}"
  fi
fi

# 7) Ask which port to run on (optional)
read -r -p "Streamlit port [default 8501]: " PORT
PORT="${PORT:-8501}"

echo
echo -e "${GREEN}Starting Panopticon with Streamlit on port ${PORT}...${RESET}"
echo "Use Ctrl+C to stop."

# 8) Run Streamlit
streamlit run app.py --server.port="$PORT"
