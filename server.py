"""Local CM Tool server with a same-origin news feed."""
import json
from analysis_import import prepare_import, build_prompt, validate_proposals, local_proposals
import os
import threading
import sqlite3
import uuid
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CACHE = {}
DATABASE = Path(__file__).parent.parent / 'cm-tool-trends.sqlite3'
PRIVATE_CONFIG = Path(__file__).parent.parent / 'cm-tool-client.private.json'
IDEAS_LOCK = threading.Lock()


def ideas_webhook():
    url = os.environ.get('CM_IDEAS_WEBHOOK_URL', '')
    if not url and PRIVATE_CONFIG.exists():
        url = json.loads(PRIVATE_CONFIG.read_text()).get('ideasWebhookUrl', '')
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname != 'hook.eu1.make.com' or parsed.username:
        raise ValueError('Invalid server configuration')
    return url


def request_ideas(data):
    request = urllib.request.Request(ideas_webhook(), data=json.dumps(data).encode(),
                                     headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(request, timeout=90) as response:
        result = json.loads(response.read(1_000_000))
    items = result if isinstance(result, list) else result.get('ideas')
    if not isinstance(items, list) or not items or not all(isinstance(item, dict) for item in items):
        raise ValueError('Invalid upstream response')
    return {'ideas': [{key: str(item.get(key, ''))[:4000] for key in
                       ('title', 'type', 'angle', 'description', 'hook')} for item in items[:10]]}


def database():
    connection = sqlite3.connect(DATABASE)
    connection.execute('CREATE TABLE IF NOT EXISTS trends (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
    return connection


def news(query):
    cached = CACHE.get(query)
    if cached and time.time() - cached[0] < 1800:
        return cached[1]
    params = urllib.parse.urlencode({"q": query + " when:14d", "hl": "fr", "gl": "FR", "ceid": "FR:fr"})
    request = urllib.request.Request("https://news.google.com/rss/search?" + params, headers={"User-Agent": "CMTool/1.0"})
    with urllib.request.urlopen(request, timeout=15) as response:
        root = ET.fromstring(response.read(2_000_000))
    items, seen = [], set()
    now = datetime.now(timezone.utc)
    for entry in root.findall("./channel/item"):
        title = entry.findtext("title", "").strip()
        link = entry.findtext("link", "")
        source = entry.findtext("source", "")
        try:
            date = parsedate_to_datetime(entry.findtext("pubDate", ""))
        except (ValueError, TypeError):
            continue
        if not now - timedelta(days=14) <= date <= now + timedelta(hours=1):
            continue
        if not link.startswith("https://") or title in seen:
            continue
        seen.add(title)
        if source and title.endswith(" - " + source):
            title = title[:-(len(source) + 3)]
        items.append({"title": title, "url": link, "source": source, "date": date.isoformat()})
        if len(items) == 8:
            break
    result = {"items": items, "updatedAt": now.isoformat()}
    CACHE[query] = (time.time(), result)
    return result


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).parent), **kwargs)

    def send_head(self):
        path = Path(self.translate_path(self.path)).resolve()
        root = Path(__file__).parent.resolve()
        public_files = {root / name for name in ('index.html', 'trend-editor.html')}
        allowed_asset = root / 'assets' in path.parents and path.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.svg', '.js', '.css')
        if path != root and path not in public_files and not allowed_asset:
            self.send_error(404)
            return None
        return super().send_head()

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == '/editeur/tendances':
            self.path = '/trend-editor.html'
            return super().do_GET()
        if parsed.path in ('/api/trends', '/api/editor/trends'):
            with database() as db:
                items = [json.loads(row[0]) for row in db.execute('SELECT data FROM trends ORDER BY rowid DESC')]
            if parsed.path == '/api/trends':
                items = [item for item in items if item['status'] == 'published']
            return self.send_json({'items': items})
        if parsed.path != "/api/news":
            return super().do_GET()
        query = urllib.parse.parse_qs(parsed.query).get("q", [""])[0].strip()[:250]
        try:
            result = news(query) if query else {"items": []}
            status = 200
        except Exception:
            result, status = {"error": "Actualités temporairement indisponibles."}, 502
        body = json.dumps(result, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, value, status=200):
        body = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path not in ('/api/editor/trends', '/api/ideas', '/api/analysis-import'):
            return self.send_json({'error': 'Introuvable'}, 404)
        # Local editor only: reject cross-origin writes. Hosted accounts need authentication.
        if self.headers.get('Origin') not in ('http://localhost:8127', 'http://127.0.0.1:8127'):
            return self.send_json({'error': 'Origine non autorisée'}, 403)
        if self.headers.get('Host') not in ('localhost:8127', '127.0.0.1:8127'):
            return self.send_json({'error': 'Hôte non autorisé'}, 403)
        if self.path == '/api/analysis-import':
            if not IDEAS_LOCK.acquire(blocking=False):
                return self.send_json({'error':'Une génération est déjà en cours.'}, 429)
            try:
                length = int(self.headers.get('Content-Length', 0))
                if not 0 < length <= 20_000_000:
                    raise ValueError('Import trop volumineux.')
                data = json.loads(self.rfile.read(length))
                fields, sources = prepare_import(data)
                payload = {'action':'GENERATE_IDEAS','query':'Extraction de statistiques : respecter le prompt', 'count':30,
                           'client':{'name':str(data.get('clientName',''))[:200]},'news':[], 'planning':[],
                           'prompt':build_prompt(fields, sources)}
                request = urllib.request.Request(ideas_webhook(), data=json.dumps(payload).encode(), headers={'Content-Type':'application/json'}, method='POST')
                try:
                    with urllib.request.urlopen(request, timeout=90) as response:
                        result = json.loads(response.read(1_000_000))
                    items = result if isinstance(result,list) else result.get('ideas',[])
                    if not isinstance(items,list):
                        raise ValueError('Réponse IA non valide.')
                    proposals = validate_proposals(items, fields, sources)
                    mode = 'ai'
                except Exception:
                    proposals = local_proposals(fields, sources)
                    mode = 'local'
                return self.send_json({'proposals':proposals, 'sources':sources, 'mode':mode})
            except ValueError as error:
                return self.send_json({'error':str(error)},400)
            except Exception:
                return self.send_json({'error':'La lecture ou le classement IA est indisponible. Le rapport n’a pas été modifié.'},502)
            finally:
                IDEAS_LOCK.release()
        if self.path == '/api/ideas':
            try:
                length = int(self.headers.get('Content-Length', 0))
                if not 0 < length <= 100_000:
                    raise ValueError()
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict) or not isinstance(data.get('prompt'), str) or not data['prompt'].strip():
                    raise ValueError()
            except (ValueError, TypeError):
                return self.send_json({'error': 'Requête non valide'}, 400)
            if not IDEAS_LOCK.acquire(blocking=False):
                return self.send_json({'error': 'Génération déjà en cours'}, 429)
            try:
                return self.send_json(request_ideas(data))
            except Exception:
                return self.send_json({'error': 'Génération temporairement indisponible'}, 502)
            finally:
                IDEAS_LOCK.release()
        try:
            length = int(self.headers.get('Content-Length', 0))
            if not 0 < length <= 4_000_000:
                raise ValueError('Fichier trop volumineux')
            data = json.loads(self.rfile.read(length))
            item = {key: str(data.get(key, '')).strip()[:4000] for key in
                    ('title', 'description', 'source', 'platform', 'difficulty', 'duration', 'date', 'status')}
            item['id'] = str(data.get('id') or uuid.uuid4())
            item['image'] = str(data.get('image', ''))
            if item['image'] and not item['image'].startswith(('data:image/png;base64,', 'data:image/jpeg;base64,', 'data:image/webp;base64,', 'https://')):
                raise ValueError('Image non valide')
            if item['source'] and not item['source'].startswith(('https://', 'http://')):
                raise ValueError('Le lien doit commencer par https://')
            item['flames'] = int(data.get('flames') or 0)
            if not item['title'] or item['status'] not in ('draft', 'published', 'archived') or item['flames'] not in range(4):
                raise ValueError('Vérifie le titre et le statut')
            with database() as db:
                db.execute('INSERT INTO trends VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',
                           (item['id'], json.dumps(item, ensure_ascii=False)))
            return self.send_json({'item': item})
        except (ValueError, TypeError) as error:
            return self.send_json({'error': str(error)}, 400)


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8127), Handler).serve_forever()
