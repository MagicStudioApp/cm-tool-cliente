"""API adapter for Cloud Run, open to the published page. No client data is persisted."""
import os
from http.server import ThreadingHTTPServer
from server import Handler

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
        # Authorization stays allowed so the previous page keeps working until it is replaced.
        self.send_header('Access-Control-Allow-Headers','Content-Type, Authorization')
        self.end_headers()

    def do_GET(self):
        return self.send_json({'ok':True} if self.path == '/health' else {'error':'Introuvable'}, 200 if self.path == '/health' else 404)

    def do_POST(self):
        if self.path not in ('/api/ideas','/api/analysis-import'):
            return self.send_json({'error':'Introuvable'},404)
        if self.headers.get('Origin') != ORIGIN:
            return self.send_json({'error':'Origine non autorisée'},403)
        self.hosted_authorized = True
        super().do_POST()

if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', int(os.environ.get('PORT','8080'))),HostedHandler).serve_forever()
