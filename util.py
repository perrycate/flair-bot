#!/usr/bin/env python3
import sqlite3

DB_NAME = 'newton_storage.db'

class Storage:
    def __init__(self):
        self._conn = sqlite3.connect(DB_NAME)
        self._cursor = self._conn.cursor()

        self._exec('''CREATE TABLE IF NOT EXISTS commands (key INTEGER PRIMARY KEY, date TEXT, user TEXT, trigger TEXT, content TEXT);''')
    
    def __del__(self):
        self._conn.close()

    def _exec(self, command):
        self._cursor.execute(command)
        self._conn.commit()
 