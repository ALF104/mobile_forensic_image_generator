import sqlite3
import logging
from pathlib import Path
from typing import Optional

class SQLiteDB:
    """
    Context Manager for SQLite database operations.
    Handles connection, committing, rollback on error, and closing.
    """
    def __init__(self, db_path: Path, logger: Optional[logging.Logger] = None):
        self.db_path = db_path
        self.logger = logger
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None

    def __enter__(self):
        try:
            # Ensure parent directory exists
            if not self.db_path.parent.exists():
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
                
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            return self.cursor
        except sqlite3.Error as e:
            if self.logger:
                self.logger.error(f"Failed to connect to database {self.db_path.name}: {e}")
            raise e

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            try:
                if exc_type:
                    self.conn.rollback()
                    if self.logger:
                        self.logger.error(f"Transaction failed in {self.db_path.name}: {exc_val}")
                else:
                    self.conn.commit()
            except sqlite3.Error as e:
                if self.logger:
                    self.logger.error(f"Commit failed for {self.db_path.name}: {e}")
            finally:
                self.conn.close()