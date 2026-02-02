"""
Vercel serverless function for POST /api/questions/search
"""

from http.server import BaseHTTPRequestHandler
import json
import math
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

            filters = body.get('filters', {})
            pagination = body.get('pagination', {})
            sort_by = body.get('sort_by', 'id')
            sort_desc = body.get('sort_desc', False)

            page = pagination.get('page', 1)
            page_size = pagination.get('page_size', 20)

            db = get_database()
            questions, total = db.search_questions(
                query=filters.get('query'),
                topics=filters.get('topics'),
                disease_states=filters.get('disease_states'),
                disease_stages=filters.get('disease_stages'),
                disease_types=filters.get('disease_types'),
                treatments=filters.get('treatments'),
                biomarkers=filters.get('biomarkers'),
                trials=filters.get('trials'),
                activities=filters.get('activities'),
                min_confidence=filters.get('min_confidence'),
                has_performance_data=filters.get('has_performance_data'),
                page=page,
                page_size=page_size,
                sort_by=sort_by,
                sort_desc=sort_desc
            )

            result = {
                "questions": questions,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": math.ceil(total / page_size) if total > 0 else 0
            }

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())

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
