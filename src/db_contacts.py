import sqlite3
import os

DB_PATH = 'data/contacts.db'

def _get_connection():
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    # Create table if it doesn't exist
    conn.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            zone TEXT NOT NULL
        )
    ''')
    conn.commit()
    return conn

def add_contact(name: str, phone: str, zone: str):
    conn = _get_connection()
    try:
        conn.execute('INSERT INTO contacts (name, phone, zone) VALUES (?, ?, ?)', (name, phone, zone))
        conn.commit()
    finally:
        conn.close()

def get_all_contacts():
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, phone, zone FROM contacts ORDER BY name')
        return cursor.fetchall()
    finally:
        conn.close()

def get_contacts_by_zone(zone: str):
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT name, phone FROM contacts WHERE zone = ?', (zone,))
        return cursor.fetchall()
    finally:
        conn.close()

def delete_contact(contact_id: int):
    conn = _get_connection()
    try:
        conn.execute('DELETE FROM contacts WHERE id = ?', (contact_id,))
        conn.commit()
    finally:
        conn.close()
