#!/bin/bash

# ==============================================================================
#           CodexCLI Proxy - Wrapper Script
# ==============================================================================
# This script automates the process of using the proxy. It will:
# 1. Automatically start the python proxy server in the background.
# 2. Run your CLI client (e.g., Codex), passing all arguments to it.
# 3. Automatically shut down the proxy server when the client exits.
# 4. On first run, it will copy the template config to the right directory.
# ==============================================================================

# --- USER CONFIGURATION ---
# The name of your AI client's executable.
# The script will call this command and pass all arguments to it.
CLIENT_EXECUTABLE="codex"

# The path to your AI client's configuration directory.
# The script will create a 'config.toml' file here if it doesn't exist.
# Common locations:
# - For CodexCLI: "$HOME/.config/codex-cli"
# - For others: Check your client's documentation.
CLIENT_CONFIG_DIR="$HOME/.config/codex-cli"
# --- END OF USER CONFIGURATION ---


# --- SCRIPT SETUP ---
# Get the absolute path of the directory where this script is located.
# This allows the script to find proxy.py and config_template.toml
# regardless of where it is run from.
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

PROXY_SCRIPT="$SCRIPT_DIR/proxy.py"
TEMPLATE_CONFIG="$SCRIPT_DIR/config_template.toml"
USER_CONFIG_FILE="$CLIENT_CONFIG_DIR/config.toml"
LOG_FILE="/tmp/codex_proxy_${USER}.log"

# --- 1. AUTO-CONFIGURE FOR NEW USERS ---
if [ ! -f "$USER_CONFIG_FILE" ]; then
    echo "[SETUP] Client config not found. Initializing from template..."
    if [ ! -f "$TEMPLATE_CONFIG" ]; then
        echo "[ERROR] Template config not found at $TEMPLATE_CONFIG" >&2
        exit 1
    fi
    mkdir -p "$CLIENT_CONFIG_DIR"
    cp "$TEMPLATE_CONFIG" "$USER_CONFIG_FILE"
    echo "[SETUP] New config created at: $USER_CONFIG_FILE"
fi

# --- 2. SET DUMMY API KEY ---
# Some clients require an API key to be set, even if we're using a proxy
# that doesn't need one from the client.
export DUMMY_KEY="sk-dummy-key-for-proxy"

# --- 3. START PROXY SERVER ---
# Check if python3 is available.
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 command not found. Please install Python 3." >&2
    exit 1
fi

# Check if the proxy script exists.
if [ ! -f "$PROXY_SCRIPT" ]; then
    echo "[ERROR] Proxy script not found at $PROXY_SCRIPT" >&2
    exit 1
fi

# Start the python proxy server in the background.
# Its output (logs) will be redirected to a file in /tmp.
echo "[PROXY] Starting proxy server in background. Log: $LOG_FILE"
python3 "$PROXY_SCRIPT" > "$LOG_FILE" 2>&1 &
PROXY_PID=$!

# Add a short delay to give the server time to start and bind to the port.
sleep 0.5

# --- 4. REGISTER CLEANUP ---
# The 'trap' command registers a command to be run when the script exits for
# any reason (including being closed with Ctrl+C). This ensures the background
# proxy process doesn't become a zombie.
trap "echo '[PROXY] Shutting down proxy server...'; kill $PROXY_PID 2> /dev/null" EXIT

# --- 5. RUN THE CLIENT ---
# Check if the client executable is available.
if ! command -v "$CLIENT_EXECUTABLE" &> /dev/null; then
    echo "[ERROR] Client executable '$CLIENT_EXECUTABLE' not found in your PATH." >&2
    echo "Please check the CLIENT_EXECUTABLE variable in this script." >&2
    # We still wait a moment before exiting to let the trap clean up the proxy.
    sleep 0.1
    exit 1
fi

# Execute the client application, passing all of this script's arguments ("$@")
# directly to it. The script will now wait here until the client finishes.
"$CLIENT_EXECUTABLE" "$@"
