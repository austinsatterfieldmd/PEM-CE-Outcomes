"""
Vercel serverless function for POST /api/questions/filters/options/dynamic
"""

from http.server import BaseHTTPRequestHandler
import json
import sys
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from _shared.database import get_database


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(content_length)) if content_length else {}

            db = get_database()
            options = db.get_dynamic_filter_options(
                topics=body.get('topics'),
                disease_states=body.get('disease_states'),
                disease_stages=body.get('disease_stages'),
                disease_types=body.get('disease_types'),
                treatment_lines=body.get('treatment_lines'),
                treatments=body.get('treatments'),
                biomarkers=body.get('biomarkers'),
                trials=body.get('trials'),
            )

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(options).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
