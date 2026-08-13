import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import argparse
from runner import run_from_repo

class CIWebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        # 1. Read the incoming webhook payload
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        if not post_data:
            self.send_response(400)
            self.end_headers()
            return

        try:
            payload = json.loads(post_data.decode('utf-8'))
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON payload")
            return

        # 2. Extract the repository URL. 
        # GitHub webhooks put this in payload['repository']['clone_url']
        repo_url = payload.get('repository', {}).get('clone_url')

        if not repo_url:
            self.send_error(400, "Missing repository clone_url in payload")
            return

        print(f"\n🔔 Webhook received! Triggering run for {repo_url}")
        
        # 3. Acknowledge the webhook immediately so GitHub doesn't time out
        self.send_response(202)  # 202 Accepted
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Pipeline triggered successfully.\n")

        # 4. Spin up a background thread to run the pipeline so we don't block the server
        threading.Thread(target=run_from_repo, args=(repo_url,)).start()

def main():
    parser = argparse.ArgumentParser(description="plan Webhook Server")
    parser.add_argument('--port', type=int, default=8000, help="Port to listen on")
    args = parser.parse_args()

    server_address = ('', args.port)
    httpd = HTTPServer(server_address, CIWebhookHandler)
    
    print(f"🎧 plan listening for webhooks on port {args.port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down server.")
        httpd.server_close()

if __name__ == "__main__":
    main()