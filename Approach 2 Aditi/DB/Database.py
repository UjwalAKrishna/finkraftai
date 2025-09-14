"""THIS FILE HAS ALL THE DB FUNCTIONS"""
import sqlite3
from typing import Dict, Any, List, Tuple


class DatabaseFunctions:
    def __init__(self, db_path: str = "chatbot.db"):
        self.db_path = db_path

    def get_connection(self):
        """
        Create a new SQLite connection with WAL mode and timeout to avoid 'database is locked'.
        """
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL;")   
        conn.execute("PRAGMA synchronous=NORMAL;") 
        return conn

    def select_df(self, table_name: str) -> List[Tuple]:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
        finally:
            conn.close()
        return rows

    def insert_df(self, table_name: str, data: Dict[str, Any]) -> None:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            columns = ", ".join(data.keys())
            placeholders = ", ".join(["?"] * len(data))
            values = tuple(data.values())

            cursor.execute(
                f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})",
                values,
            )
            conn.commit()
        finally:
            conn.close()

    def upsert_df(self, table_name: str, data: Dict[str, Any], pk_field: str) -> None:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            columns = ", ".join(data.keys())
            placeholders = ", ".join(["?"] * len(data))
            values = tuple(data.values())

            update_clause = ", ".join(
                [f"{col}=excluded.{col}" for col in data.keys() if col != pk_field]
            )

            sql = f"""
            INSERT INTO {table_name} ({columns}) VALUES ({placeholders})
            ON CONFLICT({pk_field}) DO UPDATE SET {update_clause}
            """
            cursor.execute(sql, values)
            conn.commit()
        finally:
            conn.close()

    def delete_df(self, table_name: str, condition: str, params: Tuple[Any, ...]) -> None:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f"DELETE FROM {table_name} WHERE {condition}", params)
            conn.commit()
        finally:
            conn.close()
