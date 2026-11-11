"""SQLite CPU ledger. Every evaluation reserves time before it runs.

LLM-written programs do not import this module. Roles are proposer, evolver,
and promoter. `reserve` either returns a reservation id or records a refusal.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path


class BudgetRefused(RuntimeError):
    pass


class Ledger:
    def __init__(self, path, total_cpu_seconds: float):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS meta (
                k TEXT PRIMARY KEY,
                v REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY,
                role TEXT NOT NULL,
                amount REAL NOT NULL,
                actual REAL,
                status TEXT NOT NULL,
                created_at REAL NOT NULL
            );
            """
        )
        self.conn.execute(
            "INSERT INTO meta(k, v) VALUES('total', ?) ON CONFLICT(k) DO NOTHING",
            (float(total_cpu_seconds),),
        )
        self.conn.commit()

    def _total(self) -> float:
        row = self.conn.execute("SELECT v FROM meta WHERE k='total'").fetchone()
        return float(row[0])

    def _held(self) -> float:
        row = self.conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM reservations WHERE status='reserved'"
        ).fetchone()
        spent = self.conn.execute(
            "SELECT COALESCE(SUM(actual), 0) FROM reservations WHERE status='committed'"
        ).fetchone()
        return float(row[0]) + float(spent[0])

    def remaining(self) -> float:
        return self._total() - self._held()

    def reserve(self, role: str, cpu_seconds: float) -> int:
        amount = float(cpu_seconds)
        if amount < 0:
            raise ValueError("cpu_seconds must be >= 0")
        if self.remaining() < amount:
            self.conn.execute(
                "INSERT INTO reservations(role, amount, status, created_at) VALUES(?, ?, 'refused', ?)",
                (role, amount, time.time()),
            )
            self.conn.commit()
            raise BudgetRefused(f"{role} asked for {amount}s, remaining {self.remaining():.3f}s")
        cur = self.conn.execute(
            "INSERT INTO reservations(role, amount, status, created_at) VALUES(?, ?, 'reserved', ?)",
            (role, amount, time.time()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def commit(self, reservation_id: int, actual_seconds: float | None = None) -> None:
        row = self.conn.execute(
            "SELECT amount, status FROM reservations WHERE id=?", (reservation_id,)
        ).fetchone()
        if row is None:
            raise KeyError(reservation_id)
        if row[1] != "reserved":
            raise RuntimeError(f"reservation {reservation_id} is {row[1]}")
        actual = float(row[0] if actual_seconds is None else actual_seconds)
        if actual < 0:
            actual = 0.0
        # A run may exceed its reservation; the overage still counts as spent.
        self.conn.execute(
            "UPDATE reservations SET status='committed', actual=? WHERE id=?",
            (actual, reservation_id),
        )
        self.conn.commit()

    def spent_by_role(self) -> dict[str, float]:
        rows = self.conn.execute(
            "SELECT role, COALESCE(SUM(actual), 0) FROM reservations WHERE status='committed' GROUP BY role"
        ).fetchall()
        return {role: float(total) for role, total in rows}

    def refused_by_role(self) -> dict[str, int]:
        rows = self.conn.execute(
            "SELECT role, COUNT(*) FROM reservations WHERE status='refused' GROUP BY role"
        ).fetchall()
        return {role: int(n) for role, n in rows}
