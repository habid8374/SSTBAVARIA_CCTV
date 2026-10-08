"""Cámaras IP simuladas para la prueba integral del equipo local: cada una
sirve un stream MJPEG por HTTP a 25 imágenes por segundo (como el substream
de una cámara real), que OpenCV abre igual que un RTSP.

Escenas: "persona" (bus.jpg: varias personas de cuerpo entero), "primer_plano"
(zidane.jpg: dos personas cortadas por el borde de abajo), "vacia"
(sin nadie) y "aparece" (vacía hasta que exista el archivo
<carpeta>/aparecer.flag; desde ahí, persona — y deja la hora en
aparecio.txt para medir cuánto tarda en llegar la alerta).

Uso: python camaras_simuladas.py <carpeta_imagenes> <carpeta_estado> <puerto>
"""

import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import cv2
import numpy as np

ANCHO, ALTO = 1280, 720
FPS = 25

ESCENAS_POR_CAMARA = {
    "cam1": "persona",
    "cam2": "persona",
    "cam3": "persona",
    "cam4": "persona",
    "cam5": "vacia",
    "cam6": "persona",
    "cam8": "persona",
    "cam9": "aparece",
    "cam10": "primer_plano",
}


def _encuadrar(imagen):
    """Ajusta la imagen a 1280x720 sin deformarla (relleno gris)."""
    alto, ancho = imagen.shape[:2]
    escala = min(ANCHO / ancho, ALTO / alto)
    nueva = cv2.resize(imagen, (int(ancho * escala), int(alto * escala)))
    lienzo = np.full((ALTO, ANCHO, 3), 90, dtype=np.uint8)
    y = (ALTO - nueva.shape[0]) // 2
    x = (ANCHO - nueva.shape[1]) // 2
    lienzo[y : y + nueva.shape[0], x : x + nueva.shape[1]] = nueva
    return lienzo


def _jpeg(imagen):
    ok, buffer = cv2.imencode(".jpg", imagen, [cv2.IMWRITE_JPEG_QUALITY, 85])
    assert ok
    return buffer.tobytes()


def main():
    carpeta_imagenes, carpeta_estado, puerto = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3])
    carpeta_estado.mkdir(parents=True, exist_ok=True)
    vacia = np.full((ALTO, ANCHO, 3), 90, dtype=np.uint8)
    cv2.rectangle(vacia, (100, 400), (500, 700), (60, 60, 60), -1)  # algo de "escenario", sin personas
    escenas = {
        "persona": _jpeg(_encuadrar(cv2.imread(str(carpeta_imagenes / "bus.jpg")))),
        "primer_plano": _jpeg(_encuadrar(cv2.imread(str(carpeta_imagenes / "zidane.jpg")))),
        "vacia": _jpeg(vacia),
    }
    flag = carpeta_estado / "aparecer.flag"
    registro_aparicion = carpeta_estado / "aparecio.txt"
    lock = threading.Lock()

    def escena_actual(nombre):
        if nombre != "aparece":
            return escenas[nombre]
        if not flag.exists():
            return escenas["vacia"]
        with lock:
            if not registro_aparicion.exists():
                registro_aparicion.write_text(str(time.time()))
        return escenas["persona"]

    class Manejador(BaseHTTPRequestHandler):
        def do_GET(self):
            camara = self.path.strip("/").removesuffix(".mjpg")
            if camara not in ESCENAS_POR_CAMARA:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()
            siguiente = time.monotonic()
            try:
                while True:
                    datos = escena_actual(ESCENAS_POR_CAMARA[camara])
                    self.wfile.write(
                        b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                        + str(len(datos)).encode()
                        + b"\r\n\r\n"
                        + datos
                        + b"\r\n"
                    )
                    siguiente += 1 / FPS
                    time.sleep(max(0, siguiente - time.monotonic()))
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

        def log_message(self, formato, *args):
            sys.stderr.write("camaras: " + formato % args + "\n")

    servidor = ThreadingHTTPServer(("127.0.0.1", puerto), Manejador)
    servidor.daemon_threads = True
    print(f"Cámaras simuladas en http://127.0.0.1:{puerto}/camN.mjpg", flush=True)
    servidor.serve_forever()


if __name__ == "__main__":
    main()
