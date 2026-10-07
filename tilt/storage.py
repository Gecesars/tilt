"""SQLite catalog and immutable project revisions; no ADT runtime dependency."""
from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sqlite3

DATA = Path(__file__).parent / 'data' / 'cables.json'


@dataclass(frozen=True)
class Cable:
    name: str
    kind: str
    velocity_factor: float
    impedance_ohm: float
    peak_power_kw: float
    peak_voltage_v: float
    samples: tuple[tuple[float, float, float], ...]

    @property
    def frequency_range(self):
        return self.samples[0][0], self.samples[-1][0]

    def at(self, frequency_mhz):
        lo, hi = self.frequency_range
        if not math.isfinite(frequency_mhz) or not lo <= frequency_mhz <= hi:
            raise ValueError(f'{self.name}: frequência fora do catálogo ({lo:g} a {hi:g} MHz).')
        idx = bisect_left([row[0] for row in self.samples], frequency_mhz)
        if self.samples[idx][0] == frequency_mhz:
            return self.samples[idx][1], self.samples[idx][2]
        a, b = self.samples[idx-1], self.samples[idx]
        t = math.log(frequency_mhz / a[0]) / math.log(b[0] / a[0])
        def blend(x, y):
            if x > 0 and y > 0:
                return math.exp(math.log(x) + t * math.log(y / x))
            return x + t * (y-x)
        return blend(a[1], b[1]), blend(a[2], b[2])


class Database:
    def __init__(self, path: Path | str):
        if str(path) != ':memory:':
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(path))
        self.connection.row_factory = sqlite3.Row
        self.connection.execute('PRAGMA foreign_keys=ON')
        self.connection.execute('PRAGMA busy_timeout=5000')
        version = self.connection.execute('PRAGMA user_version').fetchone()[0]
        if version > 1:
            self.connection.close()
            raise ValueError('Banco criado por uma versão mais recente. Atualize a aplicação.')
        self.connection.executescript('''
            CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS cables (
                name TEXT PRIMARY KEY, kind TEXT NOT NULL, velocity_factor REAL NOT NULL,
                impedance_ohm REAL NOT NULL, peak_power_kw REAL NOT NULL, peak_voltage_v REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS samples (
                cable_name TEXT NOT NULL REFERENCES cables(name) ON DELETE CASCADE,
                frequency_mhz REAL NOT NULL, attenuation_db_100m REAL NOT NULL,
                average_power_kw REAL NOT NULL, PRIMARY KEY(cable_name, frequency_mhz)
            );
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
                created_at TEXT NOT NULL, payload TEXT NOT NULL, snapshot TEXT NOT NULL
            );
            PRAGMA user_version=1;
        ''')
        catalog = json.loads(DATA.read_text(encoding='utf-8'))
        self.catalog_hash = catalog['sha256']
        existing = self.connection.execute("SELECT value FROM metadata WHERE key='catalog_hash'").fetchone()
        if not existing or existing[0] != self.catalog_hash:
            with self.connection:
                # This table contains only the bundled catalog, never user projects.
                self.connection.execute('DELETE FROM samples')
                self.connection.execute('DELETE FROM cables')
                for row in catalog['cables']:
                    self.connection.execute('INSERT INTO cables VALUES (?,?,?,?,?,?)', tuple(
                        row[k] for k in ('name', 'kind', 'velocity_factor', 'impedance_ohm', 'peak_power_kw', 'peak_voltage_v')))
                    self.connection.executemany('INSERT INTO samples VALUES (?,?,?,?)',
                                                [(row['name'], *s) for s in row['samples']])
                self.connection.execute("INSERT OR REPLACE INTO metadata VALUES ('catalog_hash',?)", (self.catalog_hash,))

    def cables(self, kind=None):
        rows = self.connection.execute('SELECT * FROM cables ORDER BY name').fetchall()
        return [self.cable(row['name']) for row in rows if kind is None or row['kind'] == kind]

    def cable(self, name):
        row = self.connection.execute('SELECT * FROM cables WHERE name=?', (name,)).fetchone()
        if row is None:
            raise ValueError('Modelo não encontrado no catálogo local.')
        samples = self.connection.execute('SELECT frequency_mhz,attenuation_db_100m,average_power_kw '
                                          'FROM samples WHERE cable_name=? ORDER BY frequency_mhz', (name,)).fetchall()
        return Cable(**dict(row), samples=tuple(tuple(s) for s in samples))

    def save_project(self, title, payload, snapshot):
        title = title.strip()
        if not title or len(title) > 160:
            raise ValueError('Nome do projeto: informe de 1 a 160 caracteres.')
        with self.connection:
            cursor = self.connection.execute('INSERT INTO projects(title,created_at,payload,snapshot) VALUES (?,?,?,?)',
                (title, datetime.now(timezone.utc).isoformat(),
                 json.dumps(payload, ensure_ascii=False, allow_nan=False),
                 json.dumps(snapshot, ensure_ascii=False, allow_nan=False)))
        return cursor.lastrowid

    def projects(self):
        return self.connection.execute('SELECT id,title,created_at FROM projects ORDER BY id DESC').fetchall()

    def project(self, project_id):
        row = self.connection.execute('SELECT * FROM projects WHERE id=?', (project_id,)).fetchone()
        if row is None:
            raise ValueError('Revisão não encontrada.')
        return {'id': row['id'], 'title': row['title'], 'created_at': row['created_at'],
                'payload': json.loads(row['payload']), 'snapshot': json.loads(row['snapshot'])}

    def close(self):
        self.connection.close()
