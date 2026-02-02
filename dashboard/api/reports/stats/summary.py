"""
Vercel serverless function for GET /api/reports/stats/summary
"""

from http.server import BaseHTTPRequestHandler
import json
import sys
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from _shared.database import get_database


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            db = get_database()
            stats = db.get_stats()

            # Add report-specific stats
            report_stats = {
                "total_questions": stats["total_questions"],
                "tagged_questions": stats["tagged_questions"],
                "questions_with_performance": stats["questions_with_performance"],
                "total_activities": stats["total_activities"],
                "activities_with_dates": stats["activities_with_dates"],
            }

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(report_stats).encode())

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
