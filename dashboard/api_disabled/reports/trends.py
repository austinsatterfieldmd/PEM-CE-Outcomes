"""
Vercel serverless function for POST /api/reports/trends
"""

from http.server import BaseHTTPRequestHandler
import json
import sys
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from _shared.database import get_database


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(content_length)) if content_length else {}

            segment_by = body.get('segment_by')
            filters = body.get('filters', {})

            db = get_database()
            results = db.get_performance_trends(
                segment_by=segment_by,
                topics=filters.get('topics'),
                disease_states=filters.get('disease_states'),
                treatments=filters.get('treatments'),
                biomarkers=filters.get('biomarkers'),
            )

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"trends": results}).encode())

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
