"""Almacenamiento local (SQLite) de zonas restringidas y reglas de horario.

Con esto el equipo local pasa a ser la fuente de verdad de "qué alertas
vigilar" (rol de NVR) — antes esa configuración solo vivía en el backend en
la nube y el equipo local la recibía de solo lectura en cada sincronización
(ver obtener_reglas_activas en cliente_api.py). Ahora se edita acá (ver
visor_web.py, la UI de configuración) y se *reporta* hacia la nube (ver
sincronizacion_config.py) solo para que el dashboard la pueda mostrar — la
nube deja de ser quien manda.

Cada fila de zona/regla tiene:
- id: identificador local (autoincrement), estable mientras exista la fila
  — es lo único que necesita camara.py para el cooldown por zona, no hace
  falta que coincida con el id de la nube.
- cloud_id: el id real en el backend, None hasta el primer sincronizado
  exitoso (ver sincronizacion_config.py).
- actualizada_en / sincronizada_en: para saber qué filas están "sucias"
  (cambiaron después del último sincronizado) sin tener que llevar un flag
  aparte.
- eliminada: soft-delete — se necesita mantener la fila (con su cloud_id)
  hasta poder avisarle a la nube que la borre; recién ahí se borra de
  verdad (ver confirmar_eliminacion_zona/confirmar_eliminacion_regla).
"""

import json
import sqlite3
from datetime import datetime, timezone


def _ahora_iso():
    return datetime.now(timezone.utc).isoformat()


class AlmacenamientoLocal:
    def __init__(self, ruta_db):
        self._conn = sqlite3.connect(str(ruta_db), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._crear_tablas()

    def cerrar(self):
        self._conn.close()

    def _crear_tablas(self):
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS zonas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cloud_id INTEGER,
                camara_id INTEGER NOT NULL,
                nombre TEXT NOT NULL,
                tipo TEXT NOT NULL DEFAULT 'poligono',
                poligono TEXT NOT NULL DEFAULT '[]',
                centro_x REAL,
                centro_y REAL,
                radio_metros REAL,
                activa INTEGER NOT NULL DEFAULT 1,
                actualizada_en TEXT NOT NULL,
                sincronizada_en TEXT,
                eliminada INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS reglas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cloud_id INTEGER,
                zona_id INTEGER NOT NULL REFERENCES zonas(id) ON DELETE CASCADE,
                nombre TEXT NOT NULL DEFAULT '',
                hora_inicio TEXT NOT NULL,
                hora_fin TEXT NOT NULL,
                dias_semana TEXT NOT NULL DEFAULT '[]',
                canal_notificacion TEXT NOT NULL DEFAULT 'whatsapp',
                destinatario TEXT NOT NULL DEFAULT '',
                activa INTEGER NOT NULL DEFAULT 1,
                actualizada_en TEXT NOT NULL,
                sincronizada_en TEXT,
                eliminada INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        self._conn.commit()

    # --- Zonas ---

    def crear_zona(
        self,
        camara_id,
        nombre,
        tipo="poligono",
        poligono=None,
        centro_x=None,
        centro_y=None,
        radio_metros=None,
        activa=True,
    ):
        ahora = _ahora_iso()
        cur = self._conn.execute(
            """INSERT INTO zonas
               (camara_id, nombre, tipo, poligono, centro_x, centro_y, radio_metros, activa, actualizada_en)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (camara_id, nombre, tipo, json.dumps(poligono or []), centro_x, centro_y, radio_metros, int(activa), ahora),
        )
        self._conn.commit()
        return cur.lastrowid

    def actualizar_zona(self, zona_id, **campos):
        """`campos` acepta nombre/tipo/poligono/centro_x/centro_y/radio_metros/activa."""
        if not campos:
            return
        columnas = []
        valores = []
        for clave, valor in campos.items():
            if clave == "poligono":
                valor = json.dumps(valor or [])
            if clave == "activa":
                valor = int(valor)
            columnas.append(f"{clave} = ?")
            valores.append(valor)
        columnas.append("actualizada_en = ?")
        valores.append(_ahora_iso())
        valores.append(zona_id)
        self._conn.execute(f"UPDATE zonas SET {', '.join(columnas)} WHERE id = ?", valores)
        self._conn.commit()

    def eliminar_zona(self, zona_id):
        fila = self._conn.execute("SELECT cloud_id FROM zonas WHERE id = ?", (zona_id,)).fetchone()
        if fila is None:
            return
        if fila["cloud_id"] is None:
            self._conn.execute("DELETE FROM zonas WHERE id = ?", (zona_id,))
        else:
            self._conn.execute(
                "UPDATE zonas SET eliminada = 1, actualizada_en = ? WHERE id = ?", (_ahora_iso(), zona_id)
            )
        self._conn.commit()

    def obtener_zona(self, zona_id):
        fila = self._conn.execute("SELECT * FROM zonas WHERE id = ? AND eliminada = 0", (zona_id,)).fetchone()
        return self._zona_a_dict(fila) if fila else None

    def listar_zonas_por_camara(self, camara_id, incluir_inactivas=False):
        """Zonas de una cámara, con sus reglas anidadas — mismo formato que
        ZonaActivaSerializer del backend, para que camara.py
        (evaluar_deteccion) no note la diferencia de dónde vienen. Por
        defecto solo trae las activas (lo que necesita la detección);
        `incluir_inactivas=True` es para la UI de configuración, que
        también debe poder mostrar/reactivar las que están apagadas."""
        consulta = "SELECT * FROM zonas WHERE camara_id = ? AND eliminada = 0"
        if not incluir_inactivas:
            consulta += " AND activa = 1"
        consulta += " ORDER BY id"
        filas = self._conn.execute(consulta, (camara_id,)).fetchall()
        zonas = [self._zona_a_dict(fila) for fila in filas]
        for zona in zonas:
            zona["reglas"] = self.listar_reglas_por_zona(zona["id"], solo_activas=not incluir_inactivas)
        return zonas

    def zonas_pendientes_de_sincronizar(self):
        filas = self._conn.execute(
            """SELECT * FROM zonas WHERE eliminada = 0
               AND (sincronizada_en IS NULL OR actualizada_en > sincronizada_en)"""
        ).fetchall()
        return [self._zona_a_dict(fila) for fila in filas]

    def zonas_pendientes_de_eliminar(self):
        filas = self._conn.execute("SELECT * FROM zonas WHERE eliminada = 1 AND cloud_id IS NOT NULL").fetchall()
        return [self._zona_a_dict(fila) for fila in filas]

    def marcar_zona_sincronizada(self, zona_id, cloud_id):
        ahora = _ahora_iso()
        self._conn.execute(
            "UPDATE zonas SET cloud_id = ?, sincronizada_en = ? WHERE id = ?", (cloud_id, ahora, zona_id)
        )
        self._conn.commit()

    def confirmar_eliminacion_zona(self, zona_id):
        self._conn.execute("DELETE FROM zonas WHERE id = ?", (zona_id,))
        self._conn.commit()

    def importar_zona_desde_cloud(self, camara_id, cloud_id, nombre, tipo, poligono, centro_x, centro_y, radio_metros, activa):
        """Migración de arranque: si el equipo local todavía no tiene nada
        configurado para una cámara, importa lo que ya existía en el
        dashboard (para no perder configuración previa) — se guarda ya
        marcada como sincronizada, no hace falta volver a subirla."""
        ahora = _ahora_iso()
        cur = self._conn.execute(
            """INSERT INTO zonas
               (cloud_id, camara_id, nombre, tipo, poligono, centro_x, centro_y, radio_metros, activa,
                actualizada_en, sincronizada_en)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (cloud_id, camara_id, nombre, tipo, json.dumps(poligono or []), centro_x, centro_y, radio_metros,
             int(activa), ahora, ahora),
        )
        self._conn.commit()
        return cur.lastrowid

    def tiene_zonas(self, camara_id):
        fila = self._conn.execute(
            "SELECT 1 FROM zonas WHERE camara_id = ? AND eliminada = 0 LIMIT 1", (camara_id,)
        ).fetchone()
        return fila is not None

    def _zona_a_dict(self, fila):
        return {
            "id": fila["id"],
            "cloud_id": fila["cloud_id"],
            "camara_id": fila["camara_id"],
            "nombre": fila["nombre"],
            "tipo": fila["tipo"],
            "poligono": json.loads(fila["poligono"]),
            "centro_x": fila["centro_x"],
            "centro_y": fila["centro_y"],
            "radio_metros": fila["radio_metros"],
            "activa": bool(fila["activa"]),
        }

    # --- Reglas ---

    def crear_regla(
        self,
        zona_id,
        hora_inicio,
        hora_fin,
        dias_semana=None,
        canal_notificacion="whatsapp",
        destinatario="",
        nombre="",
        activa=True,
    ):
        ahora = _ahora_iso()
        cur = self._conn.execute(
            """INSERT INTO reglas
               (zona_id, nombre, hora_inicio, hora_fin, dias_semana, canal_notificacion, destinatario, activa,
                actualizada_en)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (zona_id, nombre, hora_inicio, hora_fin, json.dumps(dias_semana or []), canal_notificacion,
             destinatario, int(activa), ahora),
        )
        self._conn.commit()
        return cur.lastrowid

    def actualizar_regla(self, regla_id, **campos):
        if not campos:
            return
        columnas = []
        valores = []
        for clave, valor in campos.items():
            if clave == "dias_semana":
                valor = json.dumps(valor or [])
            if clave == "activa":
                valor = int(valor)
            columnas.append(f"{clave} = ?")
            valores.append(valor)
        columnas.append("actualizada_en = ?")
        valores.append(_ahora_iso())
        valores.append(regla_id)
        self._conn.execute(f"UPDATE reglas SET {', '.join(columnas)} WHERE id = ?", valores)
        self._conn.commit()

    def eliminar_regla(self, regla_id):
        fila = self._conn.execute("SELECT cloud_id FROM reglas WHERE id = ?", (regla_id,)).fetchone()
        if fila is None:
            return
        if fila["cloud_id"] is None:
            self._conn.execute("DELETE FROM reglas WHERE id = ?", (regla_id,))
        else:
            self._conn.execute(
                "UPDATE reglas SET eliminada = 1, actualizada_en = ? WHERE id = ?", (_ahora_iso(), regla_id)
            )
        self._conn.commit()

    def obtener_regla(self, regla_id):
        fila = self._conn.execute("SELECT * FROM reglas WHERE id = ? AND eliminada = 0", (regla_id,)).fetchone()
        return self._regla_a_dict(fila) if fila else None

    def listar_reglas_por_zona(self, zona_id, solo_activas=False):
        consulta = "SELECT * FROM reglas WHERE zona_id = ? AND eliminada = 0"
        if solo_activas:
            consulta += " AND activa = 1"
        consulta += " ORDER BY id"
        filas = self._conn.execute(consulta, (zona_id,)).fetchall()
        return [self._regla_a_dict(fila) for fila in filas]

    def reglas_pendientes_de_sincronizar(self):
        filas = self._conn.execute(
            """SELECT * FROM reglas WHERE eliminada = 0
               AND (sincronizada_en IS NULL OR actualizada_en > sincronizada_en)"""
        ).fetchall()
        return [self._regla_a_dict(fila) for fila in filas]

    def reglas_pendientes_de_eliminar(self):
        filas = self._conn.execute("SELECT * FROM reglas WHERE eliminada = 1 AND cloud_id IS NOT NULL").fetchall()
        return [self._regla_a_dict(fila) for fila in filas]

    def marcar_regla_sincronizada(self, regla_id, cloud_id):
        ahora = _ahora_iso()
        self._conn.execute(
            "UPDATE reglas SET cloud_id = ?, sincronizada_en = ? WHERE id = ?", (cloud_id, ahora, regla_id)
        )
        self._conn.commit()

    def confirmar_eliminacion_regla(self, regla_id):
        self._conn.execute("DELETE FROM reglas WHERE id = ?", (regla_id,))
        self._conn.commit()

    def importar_regla_desde_cloud(self, zona_id, cloud_id, hora_inicio, hora_fin, dias_semana, canal_notificacion, destinatario, nombre="", activa=True):
        ahora = _ahora_iso()
        cur = self._conn.execute(
            """INSERT INTO reglas
               (cloud_id, zona_id, nombre, hora_inicio, hora_fin, dias_semana, canal_notificacion, destinatario,
                activa, actualizada_en, sincronizada_en)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (cloud_id, zona_id, nombre, hora_inicio, hora_fin, json.dumps(dias_semana or []), canal_notificacion,
             destinatario, int(activa), ahora, ahora),
        )
        self._conn.commit()
        return cur.lastrowid

    def _regla_a_dict(self, fila):
        return {
            "id": fila["id"],
            "cloud_id": fila["cloud_id"],
            "zona_id": fila["zona_id"],
            "nombre": fila["nombre"],
            "hora_inicio": fila["hora_inicio"],
            "hora_fin": fila["hora_fin"],
            "dias_semana": json.loads(fila["dias_semana"]),
            "canal_notificacion": fila["canal_notificacion"],
            "destinatario": fila["destinatario"],
            "activa": bool(fila["activa"]),
        }
