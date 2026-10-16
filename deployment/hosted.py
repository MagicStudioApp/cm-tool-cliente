"""Authenticated API adapter for Cloud Run. No client data is persisted."""
import hmac
import os
from http.server import ThreadingHTTPServer
from server import Handler

TOKEN = os.environ.get('CM_ACCESS_TOKEN', '')
ORIGIN = 'https://magicstudioapp.github.io'

class HostedHandler(Handler):
    def end_headers(self):
        if self.headers.get('Origin') == ORIGIN:
            self.send_header('Access-Control-Allow-Origin', ORIGIN)
            self.send_header('Vary', 'Origin')
        super().end_headers()

    def do_OPTIONS(self):
        if self.headers.get('Origin') != ORIGIN:
            return self.send_json({'error':'Origine non autorisée'},403)
        self.send_response(204)
        self.send_header('Access-Control-Allow-Methods','POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers','Content-Type, Authorization')
        self.end_headers()

    def do_GET(self):
        return self.send_json({'ok':True} if self.path == '/health' else {'error':'Introuvable'}, 200 if self.path == '/health' else 404)

    def do_POST(self):
        if self.path not in ('/api/ideas','/api/analysis-import'):
            return self.send_json({'error':'Introuvable'},404)
        if len(TOKEN) < 32 or not hmac.compare_digest(self.headers.get('Authorization',''), 'Bearer '+TOKEN):
            return self.send_json({'error':'Code d’accès non valide.'},401)
        if self.headers.get('Origin') != ORIGIN:
            return self.send_json({'error':'Origine non autorisée'},403)
        self.hosted_authorized = True
        super().do_POST()

if __name__ == '__main__':
    if len(TOKEN) < 32:
        raise SystemExit('CM_ACCESS_TOKEN must contain at least 32 characters')
    ThreadingHTTPServer(('0.0.0.0', int(os.environ.get('PORT','8080'))),HostedHandler).serve_forever()
