import sqlite3

def get_connection():
    return sqlite3.connect("memory.db", check_same_thread=False)


def init_db():

    conn = get_connection()
    cur = conn.cursor()

    # CLIENTS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS clients(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name TEXT UNIQUE
    )
    """)

    # BANKS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS banks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        bank_name TEXT,
        UNIQUE(client_id, bank_name)
    )
    """)

    # VENDOR MEMORY
    cur.execute("""
    CREATE TABLE IF NOT EXISTS vendor_memory(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        bank_id INTEGER,
        vendor TEXT,
        ledger TEXT,
        ledger_group TEXT,
        UNIQUE(client_id, bank_id, vendor)
    )
    """)

    conn.commit()
    conn.close()