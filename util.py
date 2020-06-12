#!/usr/bin/env python3
import sqlite3
import time

DB_NAME = 'newton_storage.db'

class Storage:

    def save(self, username, command, content):
        self._exec("INSERT INTO commands (date, user, trigger, content) VALUES(strftime('%s', 'now'), ?, ?, ?)", username, command, content)

    def get(self, command):
        rows = self._read('''SELECT content FROM commands where trigger=? ORDER BY date DESC LIMIT 1;''', command)
        if len(rows) == 0:
            return ""
        print(rows)
        return rows[0][0]


    def _exec(self, sql_str, *args):
        self._cursor.execute(sql_str, args)
        self._conn.commit()

    def _read(self, sql, *args):
        self._cursor.execute(sql, args)
        return self._cursor.fetchall()
 

    def __init__(self):
        self._conn = sqlite3.connect(DB_NAME)
        self._cursor = self._conn.cursor()

        self._exec('''CREATE TABLE IF NOT EXISTS commands (key INTEGER PRIMARY KEY, date TEXT, user TEXT, trigger TEXT, content TEXT);''')
    
    def __del__(self):
        self._conn.close()
