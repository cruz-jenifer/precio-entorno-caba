import sqlite3
from contextlib import closing
from pathlib import Path


# Columnas opcionales de listing_details: un aviso que no las trae se guarda sin dato.
OPTIONAL_DETAILS = ('expenses', 'age_years', 'condition', 'garages', 'floor')

# Vigencia de un aviso. `no_visto`: faltó en un barrido completo de su fuente, pero sigue contando
# (puede ser un error pasajero del sitio). `baja`: faltó en dos barridos completos seguidos.
# `reservado` queda definido para las fuentes que lo publiquen.
STATUSES = ('activo', 'no_visto', 'reservado', 'baja')
VIGENTES = ('activo', 'no_visto')
# Si en un barrido completo falta más de esta proporción de los avisos vigentes de la fuente, se
# supone una falla del sitio o del lector (no una ola de ventas) y no se cambia ninguna vigencia.
MAX_FALTANTES = 0.3


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with closing(self.connect()) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS listings (
                    id TEXT PRIMARY KEY, neighborhood TEXT NOT NULL,
                    price INTEGER NOT NULL, covered_area INTEGER NOT NULL, rooms INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'activo', status_at TEXT, last_seen TEXT
                );
                -- Precio publicado en cada momento en que se vio distinto: el primero y cada cambio.
                CREATE TABLE IF NOT EXISTS listing_prices (
                    listing_id TEXT NOT NULL REFERENCES listings(id), price REAL NOT NULL,
                    currency TEXT NOT NULL, seen_at TEXT
                );
                CREATE INDEX IF NOT EXISTS listing_prices_listing ON listing_prices (listing_id);
                CREATE TABLE IF NOT EXISTS listing_details (
                    listing_id TEXT PRIMARY KEY REFERENCES listings(id), source TEXT NOT NULL,
                    url TEXT NOT NULL, captured_at TEXT NOT NULL, currency TEXT NOT NULL,
                    total_area_m2 REAL, latitude REAL, longitude REAL, location_accuracy_m REAL,
                    expenses REAL, age_years INTEGER, condition TEXT, garages INTEGER, floor INTEGER
                );
                CREATE TABLE IF NOT EXISTS crime_file (
                    id INTEGER PRIMARY KEY CHECK (id = 1), filename TEXT NOT NULL, digest TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS crimes (
                    event_date TEXT NOT NULL, neighborhood TEXT NOT NULL, kind TEXT NOT NULL,
                    hour INTEGER, count INTEGER NOT NULL, event_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS searches (
                    id INTEGER PRIMARY KEY, neighborhood TEXT NOT NULL, budget INTEGER NOT NULL,
                    min_area INTEGER NOT NULL, rooms INTEGER NOT NULL, currency TEXT NOT NULL DEFAULT 'USD',
                    UNIQUE (neighborhood, budget, min_area, rooms, currency)
                );
                CREATE TABLE IF NOT EXISTS alerts (
                    search_id INTEGER REFERENCES searches(id), listing_id TEXT REFERENCES listings(id),
                    PRIMARY KEY (search_id, listing_id)
                );
            """)
            # Bases creadas antes de sumar alquileres o los datos del edificio: se agregan las columnas nuevas.
            for table, column, kind in (('searches', 'currency', "TEXT NOT NULL DEFAULT 'USD'"),
                                        ('listing_details', 'expenses', 'REAL'),
                                        ('listing_details', 'age_years', 'INTEGER'),
                                        ('listing_details', 'condition', 'TEXT'),
                                        ('listing_details', 'garages', 'INTEGER'),
                                        ('listing_details', 'floor', 'INTEGER'),
                                        ('listings', 'status', "TEXT NOT NULL DEFAULT 'activo'"),
                                        ('listings', 'status_at', 'TEXT'),
                                        ('listings', 'last_seen', 'TEXT')):
                if column not in {row['name'] for row in db.execute(f'PRAGMA table_info({table})')}:
                    db.execute(f'ALTER TABLE {table} ADD COLUMN {column} {kind}')
            # Bases anteriores a la vigencia: el aviso se vio por última vez en su captura y su primer
            # precio es el guardado. Solo completa lo que falta, así que repetirlo no cambia nada.
            db.execute("""
                UPDATE listings SET last_seen = (
                    SELECT captured_at FROM listing_details WHERE listing_id = listings.id)
                WHERE last_seen IS NULL
            """)
            db.execute("""
                INSERT INTO listing_prices (listing_id, price, currency, seen_at)
                SELECT l.id, l.price, COALESCE(d.currency, 'USD'), d.captured_at
                FROM listings l LEFT JOIN listing_details d ON d.listing_id = l.id
                WHERE NOT EXISTS (SELECT 1 FROM listing_prices p WHERE p.listing_id = l.id)
            """)
            db.commit()

    def connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        return db

    def seed(self, listings):
        with closing(self.connect()) as db, db:
            db.executemany(self._insert_sql(), listings)

    @staticmethod
    def _insert_sql():
        return """INSERT OR IGNORE INTO listings (id, neighborhood, price, covered_area, rooms)
                  VALUES (:id, :neighborhood, :price, :covered_area, :rooms)"""

    def ingest(self, listings, *, source=None, stats=None):
        """Guarda los avisos nuevos y genera sus alertas. Un aviso ya conocido no se duplica: se anota que
        se volvió a ver, vuelve a `activo` si estaba dado de baja y, si cambió su precio publicado, se
        guarda el precio nuevo en el historial y se vuelve a comparar con las búsquedas (una baja de precio
        puede hacerlo entrar en un presupuesto). Si se pasa `stats`, se completa con esos conteos."""
        new_listings = new_alerts = price_changes = reactivated = 0
        with closing(self.connect()) as db, db:
            if source is not None:
                db.execute("BEGIN IMMEDIATE")
                catalog = db.execute("SELECT source FROM listing_details LIMIT 1").fetchone()
                if catalog and catalog['source'] != source:
                    raise ValueError('La base ya tiene avisos de otro catálogo autorizado.')
            for item in listings:
                seen_at = item.get('captured_at')
                currency = item.get('currency') or 'USD'
                if not db.execute(self._insert_sql(), item).rowcount:
                    changed, back = self._seen_again(db, item, seen_at, currency)
                    price_changes += changed
                    reactivated += back
                    if changed or back:
                        new_alerts += self._match(db, item, currency)
                    continue
                db.execute("UPDATE listings SET last_seen = ? WHERE id = ?", (seen_at, item['id']))
                db.execute("INSERT INTO listing_prices VALUES (?, ?, ?, ?)",
                           (item['id'], item['price'], currency, seen_at))
                if source is not None:
                    db.execute("""
                        INSERT INTO listing_details (listing_id, source, url, captured_at, currency,
                            total_area_m2, latitude, longitude, location_accuracy_m, expenses,
                            age_years, condition, garages, floor)
                        VALUES (:id, :source, :url, :captured_at, :currency, :total_area_m2,
                            :latitude, :longitude, :location_accuracy_m, :expenses,
                            :age_years, :condition, :garages, :floor)
                    """, {**{k: None for k in OPTIONAL_DETAILS}, **item, 'source': source})
                new_listings += 1
                new_alerts += self._match(db, item, currency)
        if stats is not None:
            stats.update(cambios_de_precio=price_changes, reactivados=reactivated)
        return new_listings, new_alerts

    @staticmethod
    def _match(db, item, currency):
        # Una búsqueda solo recibe avisos publicados en su misma moneda, y cada aviso una sola vez.
        return db.execute("""
            INSERT OR IGNORE INTO alerts (search_id, listing_id)
            SELECT id, :id FROM searches WHERE neighborhood = :neighborhood
                AND budget >= :price AND min_area <= :covered_area AND rooms = :rooms
                AND currency = :currency
        """, dict(item, currency=currency)).rowcount

    @staticmethod
    def _seen_again(db, item, seen_at, currency):
        """Devuelve (cambió el precio, volvió de una baja) para un aviso que ya estaba en la base."""
        row = db.execute("""
            SELECT l.price, l.status, l.last_seen, COALESCE(d.currency, 'USD') AS currency
            FROM listings l LEFT JOIN listing_details d ON d.listing_id = l.id WHERE l.id = ?
        """, (item['id'],)).fetchone()
        # Una captura más vieja que la última vista no cambia nada (por ejemplo, al reimportar un archivo).
        if seen_at and row['last_seen'] and seen_at < row['last_seen']:
            return False, False
        back = row['status'] not in VIGENTES
        db.execute("""
            UPDATE listings SET last_seen = COALESCE(?, last_seen),
                status = 'activo', status_at = CASE WHEN status = 'activo' THEN status_at ELSE ? END
            WHERE id = ?
        """, (seen_at, seen_at, item['id']))
        changed = (item['price'], currency) != (row['price'], row['currency'])
        if changed:
            db.execute("UPDATE listings SET price = ? WHERE id = ?", (item['price'], item['id']))
            db.execute("UPDATE listing_details SET currency = ? WHERE listing_id = ?", (currency, item['id']))
            db.execute("INSERT INTO listing_prices VALUES (?, ?, ?, ?)", (item['id'], item['price'], currency, seen_at))
        return changed, back

    def apply_sweep(self, prefix, seen_ids, seen_at):
        """Aplica un barrido completo de una fuente (todos sus avisos, no solo los más recientes).

        Los avisos de la fuente (`prefix:...`) que se vieron quedan `activo`. Los vigentes que no se vieron
        pasan de `activo` a `no_visto` y de `no_visto` a `baja`: hace falta faltar en dos barridos seguidos.
        Solo se debe llamar con barridos completos: en una captura de los más recientes, faltar no
        significa que el aviso se haya dado de baja.
        """
        pattern = prefix + ':%'
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TEMP TABLE seen (id TEXT PRIMARY KEY)")
            db.executemany("INSERT OR IGNORE INTO seen VALUES (?)", ((i,) for i in seen_ids))
            marks = ','.join('?' * len(VIGENTES))
            vigentes = db.execute(f"SELECT COUNT(*) FROM listings WHERE id LIKE ? AND status IN ({marks})",
                                  (pattern, *VIGENTES)).fetchone()[0]
            missing = db.execute(f"""
                SELECT COUNT(*) FROM listings WHERE id LIKE ? AND status IN ({marks})
                    AND id NOT IN (SELECT id FROM seen)
            """, (pattern, *VIGENTES)).fetchone()[0]
            result = {'vigentes': vigentes, 'faltantes': missing, 'no_vistos': 0, 'bajas': 0, 'reactivados': 0}
            if vigentes and missing > MAX_FALTANTES * vigentes:
                return {**result, 'aplicado': False,
                        'motivo': f'Faltan {missing} de {vigentes} avisos vigentes: se supone una falla de la fuente.'}
            result['reactivados'] = db.execute("""
                UPDATE listings SET status = 'activo', status_at = ? WHERE id LIKE ? AND status != 'activo'
                    AND id IN (SELECT id FROM seen)
            """, (seen_at, pattern)).rowcount
            db.execute("""
                UPDATE listings SET last_seen = ? WHERE id LIKE ? AND id IN (SELECT id FROM seen)
                    AND (last_seen IS NULL OR last_seen < ?)
            """, (seen_at, pattern, seen_at))
            result['bajas'] = db.execute("""
                UPDATE listings SET status = 'baja', status_at = ?
                WHERE id LIKE ? AND status = 'no_visto' AND id NOT IN (SELECT id FROM seen)
            """, (seen_at, pattern)).rowcount
            result['no_vistos'] = db.execute("""
                UPDATE listings SET status = 'no_visto', status_at = ?
                WHERE id LIKE ? AND status = 'activo' AND id NOT IN (SELECT id FROM seen)
            """, (seen_at, pattern)).rowcount
            db.execute("DROP TABLE seen")
            return {**result, 'aplicado': True}

    def save_search(self, neighborhood, budget, min_area, rooms, currency='USD'):
        with closing(self.connect()) as db, db:
            return bool(db.execute("""
                INSERT OR IGNORE INTO searches (neighborhood, budget, min_area, rooms, currency)
                VALUES (?, ?, ?, ?, ?)
            """, (neighborhood, budget, min_area, rooms, currency)).rowcount)

    def listings(self, include_inactive=False):
        """Avisos vigentes (`activo` o `no_visto`). Con `include_inactive`, también los reservados y dados de baja."""
        where = '' if include_inactive else f"WHERE l.status IN ({','.join('?' * len(VIGENTES))})"
        with closing(self.connect()) as db:
            return [dict(row) for row in db.execute(
                f"SELECT l.*, d.* FROM listings l LEFT JOIN listing_details d ON d.listing_id = l.id {where} ORDER BY l.id",
                () if include_inactive else VIGENTES)]

    def price_history(self, listing_id):
        with closing(self.connect()) as db:
            return [dict(row) for row in db.execute(
                "SELECT price, currency, seen_at FROM listing_prices WHERE listing_id = ? ORDER BY rowid",
                (listing_id,))]

    def searches(self):
        with closing(self.connect()) as db:
            return [dict(row) for row in db.execute("SELECT * FROM searches ORDER BY id")]

    def alerts(self):
        with closing(self.connect()) as db:
            return [dict(row) for row in db.execute("""
                SELECT a.search_id, l.*, d.url, COALESCE(d.currency, 'USD') AS currency, d.expenses
                FROM alerts a JOIN listings l ON l.id = a.listing_id
                LEFT JOIN listing_details d ON d.listing_id = l.id
                ORDER BY a.search_id, l.id
            """)]

    def replace_crimes(self, events, filename, digest):
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT digest FROM crime_file").fetchone()
            if previous and previous['digest'] == digest:
                return False
            db.execute("DELETE FROM crimes")
            db.executemany("INSERT INTO crimes VALUES (?, ?, ?, ?, ?, ?)", events)
            db.execute("INSERT OR REPLACE INTO crime_file VALUES (1, ?, ?)", (filename, digest))
            return True

    def crime_periods(self):
        with closing(self.connect()) as db:
            file = db.execute("SELECT filename, digest FROM crime_file").fetchone()
            periods = db.execute("""
                SELECT DISTINCT substr(event_date, 1, 7) AS period FROM crimes ORDER BY period DESC
            """)
            return dict(file) if file else None, [row['period'] for row in periods]

    def crime_summary(self, neighborhood, period):
        with closing(self.connect()) as db:
            return [dict(row) for row in db.execute("""
                SELECT kind, hour, SUM(count) AS count FROM crimes
                WHERE neighborhood = ? AND substr(event_date, 1, 7) = ?
                GROUP BY kind, hour ORDER BY kind, hour
            """, (neighborhood, period))]
