import sqlite3


class LCIAutoDB:
    """
    Lightweight SQLite helper.

    Features:
    - Connection management with row factory
    - Create table(s)
    - Insert single row (append)
    - Query with WHERE/ORDER BY/LIMIT
    - Delete rows older than N days based on a timestamp column
    """

    def __init__(self, db_path, timeout=5.0):
        self.db_path = db_path
        self.timeout = timeout
        self._conn = sqlite3.connect(
            db_path,
            timeout=timeout,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        self._conn.row_factory = sqlite3.Row
        # Enable FK constraints in case the user wants to leverage them
        self._conn.execute("PRAGMA foreign_keys = ON;")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ---------- Internal helpers ----------

    @staticmethod
    def _sanitize_identifier(identifier):
        """
        Allow only ASCII letters, digits, and underscore in identifiers (table/column names).
        Prevents injection via identifiers (values are still parameterized separately).
        """
        if not identifier or any(not (c.isalnum() or c == "_") for c in identifier):
            raise ValueError("Invalid identifier: %r" % (identifier,))
        return identifier

    def _get_conn(self):
        if self._conn is None:
            raise RuntimeError("Database connection is closed")
        return self._conn

    def _execute(self, sql, params=(), commit=False):
        conn = self._get_conn()
        cur = conn.execute(sql, params)
        if commit:
            conn.commit()
        return cur

    # ---------- DDL ----------

    def create_table_sql(self, create_sql):
        """
        Execute a CREATE TABLE ... statement as-is (useful for custom schemas).
        """
        self._execute(create_sql, commit=True)

    def create_default_entries_table(self, table_name="entries"):
        """
        Create a simple entries table with:
          - id INTEGER PRIMARY KEY AUTOINCREMENT
          - local_ue_log_path TEXT
          - nw_ue_log_path TEXT
          - ue_log_date TIMESTAMP defaulting to CURRENT_TIMESTAMP (UTC)
          - laf_job_id TEXT
          - created_at TIMESTAMP defaulting to CURRENT_TIMESTAMP (UTC)
        """
        tn = self._sanitize_identifier(table_name)
        sql = """
        CREATE TABLE IF NOT EXISTS %s (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            local_ue_log_path TEXT NOT NULL,
            nw_ue_log_path TEXT NOT NULL,
            ue_log_date TEXT NOT NULL,
            laf_job_id TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT (CURRENT_TIMESTAMP)
        );
        """ % tn
        self._execute(sql, commit=True)
        # Ensure required columns exist for pre-existing tables (lightweight migration)
        existing_cols = {row["name"] for row in self._execute("PRAGMA table_info(%s);" % tn).fetchall()}
        if "local_ue_log_path" not in existing_cols:
            self._execute("ALTER TABLE %s ADD COLUMN local_ue_log_path TEXT;" % tn, commit=True)
        if "nw_ue_log_path" not in existing_cols:
            self._execute("ALTER TABLE %s ADD COLUMN nw_ue_log_path TEXT;" % tn, commit=True)
        if "ue_log_date" not in existing_cols:
            self._execute("ALTER TABLE %s ADD COLUMN ue_log_date TEXT;" % tn, commit=True)
        if "laf_job_id" not in existing_cols:
            self._execute("ALTER TABLE %s ADD COLUMN laf_job_id TEXT;" % tn, commit=True)
        if "created_at" not in existing_cols:
            self._execute("ALTER TABLE %s ADD COLUMN created_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP);" % tn, commit=True)

    # ---------- DML: Insert (Append) ----------

    def insert(self, table_name, row):
        """
        Insert a single row (append). Returns last inserted row id.
        Example:
            db.insert("entries", {"local_ue_log_path": "/path/local.log", "nw_ue_log_path": "/mnt/nw/local.log", "laf_job_id": "job-123"})
        """
        if not row:
            raise ValueError("Insert row cannot be empty")

        tn = self._sanitize_identifier(table_name)
        # Snapshot items once to guarantee cols and values stay in the same order
        items = [(self._sanitize_identifier(k), v) for k, v in row.items()]
        cols = [k for k, v in items]
        values = tuple(v for k, v in items)
        placeholders = ", ".join(["?"] * len(cols))
        col_list = ", ".join(cols)

        sql = "INSERT INTO %s (%s) VALUES (%s);" % (tn, col_list, placeholders)
        cur = self._execute(sql, values, commit=True)
        lid = cur.lastrowid
        if lid is None:
            raise RuntimeError("Insert did not return a lastrowid")
        return int(lid)

    # ---------- Update ----------

    def update_laf_job_id(self, table_name, new_laf_job_id, row_id=None, local_ue_log_path=None):
        """
        Update laf_job_id for a single row selected by id or local_ue_log_path.
        Returns number of rows updated (0 or 1).
        """
        tn = self._sanitize_identifier(table_name)

        # Ensure exactly one selector is supplied
        provided = (row_id is not None) + (local_ue_log_path is not None)
        if provided != 1:
            raise ValueError("Provide exactly one selector: row_id or local_ue_log_path")

        if row_id is not None:
            sql = "UPDATE %s SET laf_job_id = ? WHERE id = ?;" % tn
            params = (new_laf_job_id, row_id)
        else:
            assert local_ue_log_path is not None
            sql = "UPDATE %s SET laf_job_id = ? WHERE local_ue_log_path = ?;" % tn
            params = (new_laf_job_id, local_ue_log_path)

        cur = self._execute(sql, params, commit=True)
        return cur.rowcount or 0

    # ---------- Query ----------

    def query(self, table_name, columns="*", where=None, params=(), order_by=None, limit=None, offset=None):
        """
        Query rows and return as list of dicts.

        columns: "*" or an iterable of column names
        where: SQL where clause fragment without the "WHERE" keyword (e.g. "amount > ?" or "data LIKE ?")
        params: parameters for the where fragment
        order_by: safe column list or expression (caller responsibility)
        limit/offset: pagination

        NOTE: For complex WHERE/ORDER BY expressions, ensure they are trusted strings.
        """
        tn = self._sanitize_identifier(table_name)

        if columns == "*":
            col_sql = "*"
        else:
            col_list = [self._sanitize_identifier(c) for c in columns]
            col_sql = ", ".join(col_list)

        sql_parts = ["SELECT %s FROM %s" % (col_sql, tn)]
        if where:
            # where is a fragment, caller responsibility; values are still parameterized
            sql_parts.append("WHERE %s" % where)
        if order_by:
            sql_parts.append("ORDER BY %s" % order_by)
        if limit is not None:
            if limit < 0:
                raise ValueError("limit must be non-negative")
            sql_parts.append("LIMIT %d" % int(limit))
        if offset is not None:
            if offset < 0:
                raise ValueError("offset must be non-negative")
            sql_parts.append("OFFSET %d" % int(offset))

        sql = " ".join(sql_parts) + ";"
        cur = self._execute(sql, params, commit=False)
        rows = cur.fetchall()
        return [dict(r) for r in rows]

    # ---------- Delete old entries ----------

    def delete_older_than(self, table_name, days, date_column="created_at"):
        """
        Delete rows where (now - date_column) >= days.
        Uses julianday() for robust date arithmetic regardless of storage class,
        provided date_column is parseable by SQLite date/time functions (e.g., ISO8601 or default CURRENT_TIMESTAMP).
        Returns number of rows deleted.
        """
        if days < 0:
            raise ValueError("days must be non-negative")

        tn = self._sanitize_identifier(table_name)
        dc = self._sanitize_identifier(date_column)

        # julianday('now') - julianday(column) returns difference in days (float)
        sql = """
        DELETE FROM %s
        WHERE (julianday('now') - julianday(%s)) >= ?;
        """ % (tn, dc)
        cur = self._execute(sql, (float(days),), commit=True)
        return cur.rowcount or 0

    # ---------- Maintenance (optional) ----------

    def vacuum(self):
        """
        Reclaim space after large deletes (optional call).
        """
        self._execute("VACUUM;", commit=True)


if __name__ == "__main__":
    # Example usage
    with LCIAutoDB("example.db") as db:
        # 1) Create a simple table if missing
        db.create_default_entries_table("entries")

        # 2) Append/insert entries
        db.insert("entries", {"local_ue_log_path": "C:/logs/ue1.log", "nw_ue_log_path": "//server/share/ue1.log", "laf_job_id": "job-1"})
        db.insert("entries", {"local_ue_log_path": "C:/logs/ue2.log", "nw_ue_log_path": "//server/share/ue2.log", "laf_job_id": "job-2"})

        # 3) Update laf_job_id for a specific row by local path
        updated = db.update_laf_job_id("entries", "job-2B", local_ue_log_path="C:/logs/ue2.log")
        print("Rows updated: %s" % updated)

        # 4) Query entries (all)
        rows = db.query("entries", order_by="created_at DESC")
        print("All rows: %s" % rows)

        # 4) Query with filter
        filtered = db.query("entries", where="local_ue_log_path LIKE ?", params=("%ue1%",))
        print("Filtered rows: %s" % filtered)

        # 5) Delete entries older than N days (e.g., 7)
        deleted = db.delete_older_than("entries", days=7, date_column="created_at")
        print("Deleted rows older than 7 days: %s" % deleted)

        # 6) Optional: reclaim space after large deletes
        # db.vacuum()
