import os
import streamlit as st
from psycopg2 import pool, OperationalError


# ─────────────────────────────────────────────
#  CONNECTION POOL
# ─────────────────────────────────────────────

@st.cache_resource
def init_pool():
    db_url = os.getenv("DB_URL") or st.secrets["DB_URL"]
    return pool.SimpleConnectionPool(minconn=1, maxconn=5, dsn=db_url)


def get_conn():
    """
    Borrow a connection from the pool.
    If the pool is stale (e.g. after Supabase wakes from pause),
    clear the cache and create a fresh pool automatically.
    """
    try:
        conn = init_pool().getconn()
        # Test the connection is actually alive
        conn.cursor().execute("SELECT 1")
        return conn
    except OperationalError:
        # Pool is stale — clear cache and reconnect
        st.cache_resource.clear()
        conn = init_pool().getconn()
        return conn


def release_conn(conn):
    """Return the connection to the pool."""
    try:
        init_pool().putconn(conn)
    except Exception:
        pass  # If pool is gone, just discard


# ─────────────────────────────────────────────
#  CLIENTS
# ─────────────────────────────────────────────

def get_clients():
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT client_name FROM clients ORDER BY client_name;")
        return [row[0] for row in cur.fetchall()]
    finally:
        release_conn(conn)


def add_client(name):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO clients (client_name) VALUES (%s) ON CONFLICT DO NOTHING;",
            (name,)
        )
        conn.commit()
    finally:
        release_conn(conn)


def get_client_id(name):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM clients WHERE client_name=%s;", (name,))
        res = cur.fetchone()
        return res[0] if res else None
    finally:
        release_conn(conn)


def delete_client(client_id):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM vendor_memory WHERE client_id=%s;", (client_id,))
        cur.execute("DELETE FROM banks WHERE client_id=%s;", (client_id,))
        cur.execute("DELETE FROM clients WHERE id=%s;", (client_id,))
        conn.commit()
    finally:
        release_conn(conn)


# ─────────────────────────────────────────────
#  BANKS
# ─────────────────────────────────────────────

def get_banks(client_id):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT bank_name FROM banks WHERE client_id=%s ORDER BY bank_name;", (client_id,))
        return [row[0] for row in cur.fetchall()]
    finally:
        release_conn(conn)


def add_bank(client_id, bank_name):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO banks (client_id, bank_name) VALUES (%s,%s) ON CONFLICT DO NOTHING;",
            (client_id, bank_name)
        )
        conn.commit()
    finally:
        release_conn(conn)


def get_bank_id(client_id, bank_name):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM banks WHERE client_id=%s AND bank_name=%s;",
            (client_id, bank_name)
        )
        res = cur.fetchone()
        return res[0] if res else None
    finally:
        release_conn(conn)


def delete_bank(bank_id):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM vendor_memory WHERE bank_id=%s;", (bank_id,))
        cur.execute("DELETE FROM banks WHERE id=%s;", (bank_id,))
        conn.commit()
    finally:
        release_conn(conn)


# ─────────────────────────────────────────────
#  VENDOR MEMORY
# ─────────────────────────────────────────────

def get_vendor_memory(client_id, bank_id):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT vendor, ledger, ledger_group FROM vendor_memory WHERE client_id=%s AND bank_id=%s;",
            (client_id, bank_id)
        )
        return {vendor: (ledger, group) for vendor, ledger, group in cur.fetchall()}
    finally:
        release_conn(conn)


def save_vendor_memory(client_id, bank_id, vendor, ledger, group):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO vendor_memory (client_id, bank_id, vendor, ledger, ledger_group)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (client_id, bank_id, vendor)
            DO UPDATE SET ledger = EXCLUDED.ledger, ledger_group = EXCLUDED.ledger_group;
        """, (client_id, bank_id, vendor, ledger, group))
        conn.commit()
    finally:
        release_conn(conn)


def delete_memory(client_id, bank_id, vendor):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM vendor_memory WHERE client_id=%s AND bank_id=%s AND vendor=%s;",
            (client_id, bank_id, vendor)
        )
        conn.commit()
    finally:
        release_conn(conn)


# ─────────────────────────────────────────────
#  STOPWORDS
# ─────────────────────────────────────────────

def get_stopwords():
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT word FROM stopwords ORDER BY word;")
        return {row[0].upper().strip() for row in cur.fetchall()}
    finally:
        release_conn(conn)


def add_stopword(word):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO stopwords (word) VALUES (%s) ON CONFLICT DO NOTHING;",
            (word.upper().strip(),)
        )
        conn.commit()
    finally:
        release_conn(conn)


def delete_stopword(word):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM stopwords WHERE word=%s;", (word.upper().strip(),))
        conn.commit()
    finally:
        release_conn(conn)
