#!/usr/bin/env python3
import sqlite3


class Storage:

    def save(self, username, command, content):
        self._exec('''INSERT INTO commands (date, user, trigger, content, enabled) VALUES(strftime('%s.%f', 'now'), ?, ?, ?, 1)''',
                   username, command, content)

    def get(self, command):
        rows = self._read(
            '''SELECT content FROM commands where trigger=? AND enabled=1 ORDER BY RANDOM() LIMIT 1;''', command)
        if len(rows) == 0:
            return ""
        return rows[0][0]

    def list_commands(self):
        return self._read(
            '''SELECT trigger, user, (strftime('%s.%f')-date) FROM commands WHERE enabled=1 GROUP BY trigger ORDER BY trigger;''')

    def count(self, command):
        rows = self._read(
            '''SELECT COUNT(*) FROM commands where trigger=? AND enabled=1;''', command)
        if len(rows) == 0:
            return 0
        return int(rows[0][0])

    def delete(self, command):
        self._exec('''UPDATE commands SET enabled=0 WHERE trigger=?''', command)

    def _exec(self, sql_str, *args):
        self._cursor.execute(sql_str, args)
        self._conn.commit()

    def _read(self, sql, *args):
        self._cursor.execute(sql, args)
        return self._cursor.fetchall()

    def __init__(self, sqlite3_db_name):
        self._conn = sqlite3.connect(sqlite3_db_name)
        self._cursor = self._conn.cursor()

        self._exec('''CREATE TABLE IF NOT EXISTS commands (key INTEGER PRIMARY KEY, date REAL, user TEXT, trigger TEXT, content TEXT, enabled INTEGER);''')

    def __del__(self):
        self._conn.close()
