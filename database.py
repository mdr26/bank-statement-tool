import os
import psycopg2
import streamlit as st

def get_connection():
    try:
        db_url = os.getenv("DB_URL") or st.secrets["DB_URL"]
    except:
        db_url = os.getenv("DB_URL")

    return psycopg2.connect(db_url)

# ---------------- CLIENTS ----------------
def get_clients():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT client_name FROM clients ORDER BY client_name;")
    data = [c[0] for c in cur.fetchall()]
    cur.close(); conn.close()
    return data


def add_client(name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO clients (client_name)
    VALUES (%s)
    ON CONFLICT DO NOTHING;
    """, (name,))
    conn.commit()
    cur.close(); conn.close()


def delete_client(client_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM vendor_memory WHERE client_id=%s", (client_id,))
    cur.execute("DELETE FROM banks WHERE client_id=%s", (client_id,))
    cur.execute("DELETE FROM clients WHERE id=%s", (client_id,))
    conn.commit()
    cur.close(); conn.close()


def get_client_id(name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM clients WHERE client_name=%s", (name,))
    res = cur.fetchone()
    cur.close(); conn.close()
    return res[0] if res else None


# ---------------- BANKS ----------------
def get_banks(client_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT bank_name FROM banks WHERE client_id=%s", (client_id,))
    data = [b[0] for b in cur.fetchall()]
    cur.close(); conn.close()
    return data


def add_bank(client_id, bank_name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO banks (client_id, bank_name)
    VALUES (%s,%s)
    ON CONFLICT DO NOTHING;
    """, (client_id, bank_name))
    conn.commit()
    cur.close(); conn.close()


def delete_bank(bank_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM vendor_memory WHERE bank_id=%s", (bank_id,))
    cur.execute("DELETE FROM banks WHERE id=%s", (bank_id,))
    conn.commit()
    cur.close(); conn.close()


def get_bank_id(client_id, bank_name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT id FROM banks WHERE client_id=%s AND bank_name=%s
    """, (client_id, bank_name))
    res = cur.fetchone()
    cur.close(); conn.close()
    return res[0] if res else None


# ---------------- MEMORY ----------------
def get_vendor_memory(client_id, bank_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT vendor, ledger, ledger_group
    FROM vendor_memory
    WHERE client_id=%s AND bank_id=%s
    """, (client_id, bank_id))
    data = {v: (l, g) for v, l, g in cur.fetchall()}
    cur.close(); conn.close()
    return data


def save_vendor_memory(client_id, bank_id, vendor, ledger, group):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO vendor_memory (client_id, bank_id, vendor, ledger, ledger_group)
    VALUES (%s,%s,%s,%s,%s)
    ON CONFLICT (client_id, bank_id, vendor)
    DO UPDATE SET ledger=EXCLUDED.ledger, ledger_group=EXCLUDED.ledger_group
    """, (client_id, bank_id, vendor, ledger, group))
    conn.commit()
    cur.close(); conn.close()


def delete_memory(client_id, bank_id, vendor):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    DELETE FROM vendor_memory
    WHERE client_id=%s AND bank_id=%s AND vendor=%s
    """, (client_id, bank_id, vendor))
    conn.commit()
    cur.close(); conn.close()
