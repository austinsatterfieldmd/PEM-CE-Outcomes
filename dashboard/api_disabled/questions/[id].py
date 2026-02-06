"""
Vercel serverless function for GET /api/questions/{id}
"""

from http.server import BaseHTTPRequestHandler
import json
import re
import sys
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from _shared.database import get_database


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Extract question ID from path
            # Path will be like /api/questions/123
            match = re.search(r'/api/questions/(\d+)', self.path)
            if not match:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Invalid question ID"}).encode())
                return

            question_id = int(match.group(1))

            db = get_database()
            question = db.get_question_detail(question_id)

            if not question:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Question not found"}).encode())
                return

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(question).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
