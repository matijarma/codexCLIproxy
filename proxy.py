import http.server
import socketserver
import json
import urllib.request
import urllib.error
import time
import config # Import the configuration module

# --- Proxy Handler ---
# This class handles incoming HTTP requests to the proxy server.
class ProxyHandler(http.server.BaseHTTPRequestHandler):
    """
    The core of the proxy server. This handler receives a request from the client,
    modifies it, sends it to the target API endpoint, and then streams the
    response back to the client. It includes a robust retry mechanism with
    progressive backoff to handle rate limiting and transient network issues.
    """

    # Silence the default logging of requests to the console to reduce noise.
    def log_message(self, format, *args):
        return

    def do_POST(self):
        """
        Handles POST requests. This is the main entry point for the proxy logic.
        """
        print(f"[INFO] Connection received from {self.client_address[0]}.")
        
        # Read the request body from the client
        try:
            content_length = int(self.headers.get('content-length', 0))
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data)
        except (json.JSONDecodeError, TypeError):
            self.send_error(400, "Invalid JSON in request body.")
            print("[ERROR] Could not parse JSON from request.")
            return

        # --- Modify the Request ---
        # Force specific parameters to ensure compatibility or enforce policy.
        # This is where you can override model names, or force streaming on.
        if config.FORCED_MODEL:
            body['model'] = config.FORCED_MODEL
        body['stream'] = True  # Streaming is required for the client to work correctly
        
        modified_payload = json.dumps(body).encode('utf-8')

        # --- Retry Loop ---
        # This loop will attempt to send the request to the target endpoint up to
        # `RETRY_ATTEMPTS` times. This is crucial for handling services like Azure
        # OpenAI that can be temporarily unavailable or rate-limit requests.
        for attempt in range(1, config.RETRY_ATTEMPTS + 1):
            print(f"[INFO] Attempt {attempt}/{config.RETRY_ATTEMPTS}: Sending {len(modified_payload)} bytes to target endpoint...")
            
            # Prepare the request for the target API
            req = urllib.request.Request(config.AZURE_ENDPOINT, data=modified_payload, method="POST")
            req.add_header("Content-Type", "application/json")
            req.add_header("api-key", config.AZURE_API_KEY)

            response_buffer = b""
            error_detected_mid_stream = False
            
            try:
                # Open the connection and start reading the response.
                with urllib.request.urlopen(req) as target_response:
                    
                    # --- Buffering Response ---
                    # We read the entire response into a buffer *before* sending anything
                    # to the client. This is a key part of the "shield" logic. If the
                    # target service sends an error mid-stream (like a rate limit error),
                    # we can catch it here, discard the broken response, and retry,
                    # without the client ever seeing the error.
                    while True:
                        chunk = target_response.read(8192)
                        if not chunk:
                            break
                        response_buffer += chunk
                        
                        # Heuristic check for common error messages in the stream.
                        # This is a fallback for when the service sends an error in the
                        # stream body instead of just a header.
                        if b'"code":"too_many_requests"' in chunk or b'"error":' in chunk:
                            error_detected_mid_stream = True
                            break  # Stop reading, this response is corrupt.

                if error_detected_mid_stream:
                    wait_time = attempt * config.RETRY_WAIT_SECONDS
                    print(f"[WARN] Shield: Target sent an error mid-stream. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue # Go to the next attempt in the retry loop.

                # --- Success ---
                # If we get here, the entire response was buffered without any
                # detectable errors. We can now send it to the client.
                print(f"[SUCCESS] Received {len(response_buffer)} bytes. Streaming to client.")
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                
                self.wfile.write(response_buffer)
                self.wfile.flush()
                return # Exit the function, request is successfully handled.

            except urllib.error.HTTPError as e:
                # Handle HTTP errors (e.g., 429 Too Many Requests, 500 Internal Server Error).
                if e.code == 429:
                    wait_time = attempt * config.RETRY_WAIT_SECONDS
                    print(f"[WARN] Shield: HTTP 429 (Too Many Requests). Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue # Retry
                else:
                    print(f"[ERROR] Target returned HTTP {e.code}: {e.reason}")
                    self.send_error(e.code, f"Target API returned HTTP {e.code}")
                    return # Do not retry on other HTTP errors.
            except Exception as e:
                # Handle other exceptions like network errors.
                print(f"[ERROR] A network or unknown error occurred: {e}")
                wait_time = 5 # Short wait for transient network issues.
                print(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue # Retry

        # If the loop completes without a successful response, send an error to the client.
        print(f"[FATAL] Failed to get a clean response after {config.RETRY_ATTEMPTS} attempts.")
        self.send_error(502, "Proxy failed to get a valid response from the target API.")

# --- Server Setup ---
if __name__ == "__main__":
    # Allow the server to reuse the address, which is useful for quick restarts.
    socketserver.TCPServer.allow_reuse_address = True
    
    # Create and start the server.
    with socketserver.TCPServer(("", config.PORT), ProxyHandler) as httpd:
        print("---" * 10)
        print(f"  CodexCLI PROXY: Buffering & Shielding Proxy")
        print(f"  Listening on: 127.0.0.1:{config.PORT}")
        print(f"  Target endpoint: {config.AZURE_ENDPOINT[:50]}...")
        if config.FORCED_MODEL:
            print(f"  Forcing model: {config.FORCED_MODEL}")
        print("---" * 10)
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[INFO] Server shutting down.")
            pass