"""Demostración local de reinscripción; no conectar a datos reales."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json, secrets, time, urllib.parse

TOKENS = {}
GRUPOS = [
    {'id': 1, 'codigo': '183801', 'materia': 'Programación', 'docente': 'Ana López', 'creditos': 5, 'horario': 'Lunes 9-11', 'cupo': 3, 'reprobada': True},
    {'id': 2, 'codigo': '183802', 'materia': 'Bases de datos', 'docente': 'Luis Pérez', 'creditos': 5, 'horario': 'Martes 9-11', 'cupo': 2, 'reprobada': False},
    {'id': 3, 'codigo': '183803', 'materia': 'Redes', 'docente': 'María Ruiz', 'creditos': 5, 'horario': 'Lunes 9-11', 'cupo': 3, 'reprobada': False},
    {'id': 4, 'codigo': '183804', 'materia': 'Ingeniería de software', 'docente': 'José Díaz', 'creditos': 5, 'horario': 'Jueves 9-11', 'cupo': 0, 'reprobada': False},
    {'id': 5, 'codigo': '183805', 'materia': 'Sistemas operativos', 'docente': 'Pedro Soto', 'creditos': 5, 'horario': 'Viernes 9-11', 'cupo': 2, 'reprobada': False},
]

class Handler(BaseHTTPRequestHandler):
    def responder(self, status, data):
        raw = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status); self.send_header('Content-Type', 'application/json; charset=utf-8'); self.send_header('Content-Length', str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def leer(self):
        try: return json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'{}')
        except (ValueError, TypeError): return {}
    def sesion(self):
        token = self.headers.get('Authorization', '').removeprefix('Bearer ')
        s = TOKENS.get(token)
        return s if s and s['vence'] > time.time() else None
    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == '/':
            raw = open('index.html', encoding='utf-8').read().encode(); self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers(); self.wfile.write(raw); return
        s = self.sesion()
        if not s: return self.responder(401, {'error':'Inicia sesión o revisa tu token'})
        if path == '/api/v1/grupos': return self.responder(200, {'grupos': GRUPOS})
        if path == '/api/v1/reinscripcion': return self.responder(200, {'seleccion':s['seleccion'], 'creditos':sum(g['creditos'] for g in GRUPOS if g['id'] in s['seleccion']), 'minimo':20, 'maximo':25, 'segundos':max(0,int(s['vence']-time.time()))})
        return self.responder(404, {'error':'Ruta no encontrada'})
    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path; data = self.leer()
        if path == '/api/v1/sesiones':
            if data.get('numero_control') != '12345678' or data.get('contrasena') != 'tec123': return self.responder(401, {'error':'Credenciales incorrectas'})
            token = secrets.token_urlsafe(24); TOKENS[token] = {'vence':time.time()+1200,'seleccion':[]}
            return self.responder(200, {'token':token, 'tipo':'Bearer', 'vigencia_segundos':1200})
        s = self.sesion()
        if not s: return self.responder(401, {'error':'Sesión inválida o vencida'})
        if path == '/api/v1/reinscripcion/grupos':
            g = next((x for x in GRUPOS if x['id'] == data.get('id')), None)
            if not g: return self.responder(404, {'error':'Grupo inexistente'})
            elegidos = [x for x in GRUPOS if x['id'] in s['seleccion']]
            if g['id'] in s['seleccion']: return self.responder(409, {'error':'Grupo ya seleccionado'})
            if not g['reprobada'] and not any(x['reprobada'] for x in elegidos): return self.responder(409, {'error':'Selecciona primero la materia reprobada'})
            if g['cupo'] <= 0: return self.responder(409, {'error':'Grupo lleno'})
            if any(x['horario'] == g['horario'] for x in elegidos): return self.responder(409, {'error':'Empalme de horario'})
            if sum(x['creditos'] for x in elegidos)+g['creditos'] > 25: return self.responder(409, {'error':'Carga máxima excedida'})
            s['seleccion'].append(g['id']); return self.responder(201, {'mensaje':'Grupo agregado'})
        if path == '/api/v1/casos-criticos':
            creditos = sum(g['creditos'] for g in GRUPOS if g['id'] in s['seleccion'])
            if creditos >= 20: return self.responder(409, {'error':'Ya alcanzaste la carga mínima'})
            return self.responder(201, {'numero_caso':'CC-'+secrets.token_hex(3).upper(), 'creditos':creditos})
        return self.responder(404, {'error':'Ruta no encontrada'})
    def do_DELETE(self):
        s = self.sesion()
        if not s: return self.responder(401, {'error':'Sesión inválida o vencida'})
        try: ident = int(self.path.rsplit('/',1)[1])
        except ValueError: return self.responder(404, {'error':'Grupo inexistente'})
        if ident not in s['seleccion']: return self.responder(404, {'error':'Grupo no seleccionado'})
        if ident == 1 and len(s['seleccion']) > 1: return self.responder(409, {'error':'Quita primero las demás materias'})
        s['seleccion'].remove(ident); return self.responder(200, {'mensaje':'Grupo retirado'})

if __name__ == '__main__':
    import os
    puerto = int(os.environ.get('PORT', 8000))
    print(f'Portal iniciado en el puerto {puerto}')
    ThreadingHTTPServer(('0.0.0.0', puerto), Handler).serve_forever()
