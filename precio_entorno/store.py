import sqlite3
from contextlib import closing
from pathlib import Path


# Columnas opcionales de listing_details: un aviso que no las trae se guarda sin dato.
OPTIONAL_DETAILS = ('expenses', 'age_years', 'condition', 'garages', 'floor')


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with closing(self.connect()) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS listings (
                    id TEXT PRIMARY KEY, neighborhood TEXT NOT NULL,
                    price INTEGER NOT NULL, covered_area INTEGER NOT NULL, rooms INTEGER NOT NULL
                );
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
                                        ('listing_details', 'floor', 'INTEGER')):
                if column not in {row['name'] for row in db.execute(f'PRAGMA table_info({table})')}:
                    db.execute(f'ALTER TABLE {table} ADD COLUMN {column} {kind}')
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

    def ingest(self, listings, *, source=None):
        new_listings = new_alerts = 0
        with closing(self.connect()) as db, db:
            if source is not None:
                db.execute("BEGIN IMMEDIATE")
                catalog = db.execute("SELECT source FROM listing_details LIMIT 1").fetchone()
                if catalog and catalog['source'] != source:
                    raise ValueError('La base ya tiene avisos de otro catálogo autorizado.')
            for item in listings:
                if not db.execute(self._insert_sql(), item).rowcount:
                    continue
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
                # Una búsqueda solo recibe avisos publicados en su misma moneda.
                new_alerts += db.execute("""
                    INSERT INTO alerts (search_id, listing_id)
                    SELECT id, :id FROM searches WHERE neighborhood = :neighborhood
                        AND budget >= :price AND min_area <= :covered_area AND rooms = :rooms
                        AND currency = :currency
                """, dict(item, currency=item.get('currency') or 'USD')).rowcount
        return new_listings, new_alerts

    def save_search(self, neighborhood, budget, min_area, rooms, currency='USD'):
        with closing(self.connect()) as db, db:
            return bool(db.execute("""
                INSERT OR IGNORE INTO searches (neighborhood, budget, min_area, rooms, currency)
                VALUES (?, ?, ?, ?, ?)
            """, (neighborhood, budget, min_area, rooms, currency)).rowcount)

    def listings(self):
        with closing(self.connect()) as db:
            return [dict(row) for row in db.execute("SELECT l.*, d.* FROM listings l LEFT JOIN listing_details d ON d.listing_id = l.id ORDER BY l.id")]

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
