#!/usr/bin/env python3
import sqlite3


class CmdStore:
    def __init__(self, sqlite3_db_name):
        self._conn = sqlite3.connect(sqlite3_db_name)
        self._cursor = self._conn.cursor()
        self._exec('''CREATE TABLE IF NOT EXISTS commands (key INTEGER PRIMARY KEY, date REAL, user TEXT, trigger TEXT, content TEXT, enabled INTEGER);''')

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

    def __del__(self):
        self._conn.close()


class FlairStore:
    def __init__(self, sqlite3_db_name):
        self._conn = sqlite3.connect(sqlite3_db_name)
        self._cursor = self._conn.cursor()
        self._exec('''CREATE TABLE IF NOT EXISTS flairs (key INTEGER PRIMARY KEY, date REAL, user TEXT, message_id TEXT, reaction_id TEXT, role_id TEXT, enabled INTEGER);''')

    def save(self, username, message_id, reaction_id, role_id):
        """Associates the given role_id with the given message and reaction ids."""
        self._exec('''INSERT INTO flairs (date, user, message_id, reaction_id, role_id, enabled) VALUES(strftime('%s.%f', 'now'), ?, ?, ?, ?, 1);''',
                   username, message_id, reaction_id, role_id)

    def get(self, message_id, reaction_id):
        """Returns an array containing any role ids associated with the given message and reaction pair."""
        rows = self._read(
            '''SELECT role_id FROM flairs where message_id=? AND reaction_id=? AND enabled=1;''', message_id, reaction_id)
        return [r[0] for r in rows]

    def list_flair_messages(self):
        """Lists the messages that have one or more flairs associated with them."""
        return self._read('''SELECT message_id, reaction_id, role_id FROM flairs WHERE enabled=1;''')

    def delete(self, message_id, reaction_id):
        self._exec('''UPDATE flairs SET enabled=0 WHERE message_id=? AND reaction_id=?''',
                   message_id, reaction_id)

    def _exec(self, sql_str, *args):
        self._cursor.execute(sql_str, args)
        self._conn.commit()

    def _read(self, sql, *args):
        self._cursor.execute(sql, args)
        return self._cursor.fetchall()

    def __del__(self):
        self._conn.close()
