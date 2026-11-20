"""Gestión de la base de datos SQLite de MiPresupuesto."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

DB = Path(__file__).parent / "data" / "mipresupuesto.db"


@contextmanager
def _con():
    DB.parent.mkdir(exist_ok=True)
    c = sqlite3.connect(DB)
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init():
    with _con() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS movimientos(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL CHECK(tipo IN ('Ingreso','Gasto')),
            descripcion TEXT NOT NULL, monto REAL NOT NULL CHECK(monto>0),
            categoria TEXT NOT NULL, fecha TEXT NOT NULL, subtipo TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS presupuestos(clave TEXT PRIMARY KEY, monto REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS metas(
            id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, descripcion TEXT,
            objetivo REAL NOT NULL CHECK(objetivo>0), ahorrado REAL NOT NULL DEFAULT 0, limite TEXT);
        """)


def movimientos():
    with _con() as c:
        df = pd.read_sql_query("SELECT * FROM movimientos ORDER BY fecha DESC, id DESC", c)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["mes"] = df["fecha"].dt.strftime("%Y-%m")
    return df


def agregar_mov(tipo, desc, monto, cat, fecha, sub):
    with _con() as c:
        c.execute("INSERT INTO movimientos(tipo,descripcion,monto,categoria,fecha,subtipo) VALUES(?,?,?,?,?,?)",
                  (tipo, desc.strip(), round(monto, 2), cat, fecha.isoformat(), sub))


def editar_mov(mid, desc, monto, cat, fecha, sub):
    with _con() as c:
        c.execute("UPDATE movimientos SET descripcion=?,monto=?,categoria=?,fecha=?,subtipo=? WHERE id=?",
                  (desc.strip(), round(monto, 2), cat, fecha.isoformat(), sub, int(mid)))


def eliminar_mov(mid):
    with _con() as c:
        c.execute("DELETE FROM movimientos WHERE id=?", (int(mid),))


def presupuestos():
    with _con() as c:
        return dict(c.execute("SELECT clave, monto FROM presupuestos").fetchall())


def fijar_presupuesto(clave, monto):
    with _con() as c:
        if monto > 0:
            c.execute("INSERT INTO presupuestos(clave,monto) VALUES(?,?) "
                      "ON CONFLICT(clave) DO UPDATE SET monto=excluded.monto", (clave, round(monto, 2)))
        else:
            c.execute("DELETE FROM presupuestos WHERE clave=?", (clave,))


def metas():
    with _con() as c:
        return pd.read_sql_query("SELECT * FROM metas ORDER BY id DESC", c)


def agregar_meta(nombre, desc, objetivo, ahorrado, limite):
    with _con() as c:
        c.execute("INSERT INTO metas(nombre,descripcion,objetivo,ahorrado,limite) VALUES(?,?,?,?,?)",
                  (nombre.strip(), desc.strip(), round(objetivo, 2), round(ahorrado, 2),
                   limite.isoformat() if limite else None))


def editar_meta(mid, nombre, desc, objetivo, ahorrado, limite):
    with _con() as c:
        c.execute("UPDATE metas SET nombre=?,descripcion=?,objetivo=?,ahorrado=?,limite=? WHERE id=?",
                  (nombre.strip(), desc.strip(), round(objetivo, 2), round(ahorrado, 2),
                   limite.isoformat() if limite else None, int(mid)))


def eliminar_meta(mid):
    with _con() as c:
        c.execute("DELETE FROM metas WHERE id=?", (int(mid),))


def restaurar(contenido: bytes):
    """Reemplaza la base de datos por una copia de seguridad válida de SQLite."""
    if not contenido.startswith(b"SQLite format 3\x00"):
        raise ValueError("El archivo no es una base de datos SQLite válida.")
    DB.parent.mkdir(exist_ok=True)
    DB.write_bytes(contenido)
    init()
