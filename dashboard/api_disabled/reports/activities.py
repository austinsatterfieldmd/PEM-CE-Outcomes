"""
Vercel serverless function for GET /api/reports/activities
"""

from http.server import BaseHTTPRequestHandler
import json
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from _shared.database import get_database


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Parse query parameters
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)

            quarter = params.get('quarter', [None])[0]
            has_date_str = params.get('has_date', [None])[0]
            has_date = None
            if has_date_str is not None:
                has_date = has_date_str.lower() == 'true'

            db = get_database()
            activities = db.list_activities(quarter=quarter, has_date=has_date)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                "activities": activities,
                "total": len(activities)
            }).encode())

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
