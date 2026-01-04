# Codex CLI Proxy: Shield & Adapter

This project is a simple but powerful Python proxy server designed to sit between a client application (like [Codex CLI](https://github.com/microsoft/Codex-CLI)) and a large language model (LLM) API endpoint.

Its primary purpose is to act as a **"shield"** against aggressive rate-limiting and transient API errors, and as an **"adapter"** to allow clients to connect to otherwise incompatible OpenAI-compatible APIs.

## Key Features

- **Rate-Limit Shield**: The proxy buffers the *entire* response from the API before sending a single byte to the client. If the API cuts off the connection mid-stream (e.g., due to a rate limit error), the proxy will catch the broken response, wait, and automatically retry. This prevents the client application from crashing or displaying a partial, corrupted response.
- **Progressive Backoff**: When a retry is necessary, the proxy waits for a progressively longer time between each attempt, giving the API time to recover.
- **Endpoint Agnostic**: It can proxy requests to any OpenAI-compatible API endpoint (e.g., Azure OpenAI, custom inference servers, other third-party providers).
- **Model Forcing**: You can configure the proxy to override the model requested by the client, forcing all requests to use a specific model.
- **Easy Configuration**: All settings are managed in a simple `.env` file.
- **Minimal Dependencies**: Runs with a single, lightweight Python dependency (`python-dotenv`).

## How It Works

1.  **Client Request**: Your client application (e.g., Codex CLI) is configured to send its requests to this proxy server instead of directly to the LLM API.
2.  **Proxy Receives**: The proxy server, running locally, receives the JSON request from the client.
3.  **Proxy Modifies**: It modifies the request payload, forcing streaming (`stream: true`) and optionally overriding the model name (`model: "your-forced-model"`).
4.  **Proxy Forwards**: The proxy sends the modified payload to the target API endpoint (e.g., Azure OpenAI) defined in its `.env` file.
5.  **Buffering & Shielding**: The proxy reads the *entire* response stream from the API into memory. It watches for common error messages in the stream.
    - If an error is detected or the connection is cut, the proxy discards the response, waits, and retries the request from the beginning (go to step 4).
    - If the entire response is received without errors, it proceeds to the next step.
6.  **Proxy Responds**: The complete, clean response is sent to the client application in a single, uninterrupted stream.

## Setup and Usage

### 1. Prerequisites

-   Python 3.6 or newer.
-   Git.

### 2. Installation

Clone the repository to your local machine:

```bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
```

Install the required Python package:

```bash
pip install -r requirements.txt
```

### 3. Configuration

The proxy is configured using a `.env` file. An example is provided in `.env.example`.

1.  **Create your configuration file:**

    ```bash
    cp .env.example .env
    ```

2.  **Edit the `.env` file:**

    Open `.env` in a text editor and set the required values:

    -   `AZURE_ENDPOINT`: The full URL of the target API endpoint you want to proxy to.
    -   `AZURE_API_KEY`: The API key for that endpoint.

    You can also change the optional values like `PORT` and `FORCED_MODEL` if needed.

### 4. Running the Proxy

Start the proxy server by running:

```bash
python proxy.py
```

You should see a confirmation that the server is running:

```
------------------------------
  Codex CLI PROXY: Buffering & Shielding Proxy
  Listening on: 127.0.0.1:8888
  Target endpoint: https://your-endpoint.com/openai/...
  Forcing model: your-forced-model
------------------------------
```

Keep this terminal window open. The proxy must be running for your client application to connect to it.

### 5. Configuring Your Client

Now, configure your client application to point to the proxy. The `config_template.toml` file shows an example configuration for a tool like Codex CLI.

The key settings are:

-   `model_provider`: A custom name for your proxy (e.g., "my-proxy").
-   `base_url`: The address of the running proxy (e.g., `http://127.0.0.1:8888`).
-   `env_key`: Can be set to a dummy value, as the proxy handles authentication.

Your client will now send requests to the proxy, which will securely handle the connection to your target LLM API.

## All-in-One Wrapper Script (`chatgpt.sh`)

For a much more seamless experience, the project includes `chatgpt.sh`, a powerful wrapper script that automates the entire process.

**What it does:**
-   Starts the `proxy.py` server in the background automatically.
-   If you're running it for the first time, it automatically creates the client configuration file for you.
-   Executes your client application (e.g., `codex`), passing all arguments to it.
-   When the client application exits, it automatically kills the background proxy server, so you don't have zombie processes.

### Usage

The wrapper script is the recommended way to use this proxy system.

**1. Configure the Script:**

Open `chatgpt.sh` in a text editor. You may need to change the two variables at the top of the file:

-   `CLIENT_EXECUTABLE`: Should be the command for your AI client (defaults to `"codex"`).
-   `CLIENT_CONFIG_DIR`: Should be the path to your client's configuration directory (defaults to `"$HOME/.config/codex-cli"`).

**2. Make the Script Executable:**

In your terminal, run:
```bash
chmod +x chatgpt.sh
```

**3. Run It!**

You can now run the script instead of your client executable. It will handle starting and stopping the proxy for you. All arguments are passed through.

```bash
# Instead of running 'codex "your prompt"'
./chatgpt.sh "your prompt"
```

**4. (Optional) Make it System-Wide:**

To use it just like a native command (e.g., `chatgpt "your prompt"`), create a symbolic link to the script in a directory in your system's `PATH`.

*Note: Do not move the script file itself, as it needs to stay in the same folder as `proxy.py`.*

```bash
# Create a symbolic link in /usr/local/bin named 'chatgpt'
# Replace $(pwd) with the full path to your directory if you are not currently in it.
sudo ln -s "$(pwd)/chatgpt.sh" /usr/local/bin/chatgpt
```

Now you can call it from anywhere:
```bash
chatgpt "summarize this article: ..."
```

## Disclaimer

This proxy is a simple solution and may not be suitable for all production environments. It buffers responses in memory, which could be an issue for extremely large responses. It is intended for personal use to improve the reliability of local development tools.
