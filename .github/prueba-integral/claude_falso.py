"""API de Claude simulada para la prueba integral (el backend la usa vía
ANTHROPIC_BASE_URL). Responde como Claude: marca como detectado cada tipo de
evento cuya descripción contenga "[SI]", y tarda 13 s si alguno contiene
"[LENTO]" (más que los 10 s que espera el equipo local). Cada llamada queda
en <carpeta>/claude_llamadas.jsonl.

Uso: python claude_falso.py <carpeta_estado> <puerto>
"""

import json
import re
import sys
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

TOKENS_ENTRADA = 1500
TOKENS_SALIDA = 60


def main():
    carpeta, puerto = Path(sys.argv[1]), int(sys.argv[2])
    carpeta.mkdir(parents=True, exist_ok=True)
    registro = carpeta / "claude_llamadas.jsonl"

    class Manejador(BaseHTTPRequestHandler):
        def do_POST(self):
            cuerpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            textos = [
                bloque["text"]
                for mensaje in cuerpo["messages"]
                for bloque in mensaje["content"]
                if isinstance(bloque, dict) and bloque.get("type") == "text"
            ]
            tiene_imagen = any(
                isinstance(bloque, dict) and bloque.get("type") == "image"
                for mensaje in cuerpo["messages"]
                for bloque in mensaje["content"]
            )
            catalogo = re.findall(r"- id=(\d+): (.*)", "\n".join(textos))
            detectados = [int(tipo_id) for tipo_id, linea in catalogo if "[SI]" in linea]
            lento = any("[LENTO]" in linea for _, linea in catalogo)
            if lento:
                time.sleep(13)
            with registro.open("a", encoding="utf-8") as archivo:
                archivo.write(json.dumps({
                    "hora": time.time(),
                    "catalogo": [int(tipo_id) for tipo_id, _ in catalogo],
                    "detectados": detectados,
                    "con_imagen": tiene_imagen,
                    "lento": lento,
                }) + "\n")
            respuesta = {
                "id": f"msg_{uuid.uuid4().hex[:24]}",
                "type": "message",
                "role": "assistant",
                "model": cuerpo["model"],
                "content": [{
                    "type": "text",
                    "text": json.dumps({
                        "eventos": detectados,
                        "descripcion": "Prueba integral: persona en la zona.",
                    }),
                }],
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": TOKENS_ENTRADA, "output_tokens": TOKENS_SALIDA},
            }
            datos = json.dumps(respuesta).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            self.wfile.write(datos)

        def log_message(self, formato, *args):
            sys.stderr.write("claude-falso: " + formato % args + "\n")

    servidor = ThreadingHTTPServer(("127.0.0.1", puerto), Manejador)
    servidor.daemon_threads = True
    print(f"Claude simulado en http://127.0.0.1:{puerto}", flush=True)
    servidor.serve_forever()


if __name__ == "__main__":
    main()
