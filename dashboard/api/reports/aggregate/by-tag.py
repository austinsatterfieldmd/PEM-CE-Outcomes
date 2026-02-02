"""
Vercel serverless function for POST /api/reports/aggregate/by-tag
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

            group_by = body.get('group_by', 'topic')
            filters = body.get('filters', {})

            db = get_database()
            results = db.aggregate_performance_by_tag(
                group_by=group_by,
                topics=filters.get('topics'),
                disease_states=filters.get('disease_states'),
                treatments=filters.get('treatments'),
                biomarkers=filters.get('biomarkers'),
                trials=filters.get('trials'),
                activities=filters.get('activities'),
                quarters=filters.get('quarters'),
            )

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"results": results}).encode())

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
