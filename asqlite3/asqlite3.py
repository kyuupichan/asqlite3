# Copyright (c) 2024 Neil Booth
#
# All rights reserved.
#
# See the file "LICENCE" for information about the copyright
# and warranty status of this software.

import asyncio
import queue
import sqlite3
import threading
from functools import partial


class Cursor:
    '''An asynchronous wrapper around an sqlite3.Cursor object.'''

    def __init__(self, schedule, cursor):
        self._schedule = schedule
        self._cursor = cursor

    def __aiter__(self):
        async def iterate_rows():
            while True:
                rows = await self._schedule(self._cursor.fetchmany)
                if not rows:
                    break
                for row in rows:
                    yield row
        return iterate_rows()

    async def __aenter__(self):
        return self

    async def __aexit__(self, typ, val, tb):
        await self.close()

    async def close(self):
        await self._schedule(self._cursor.close)

    async def execute(self, sql, parameters=(), /):
        await self._schedule(partial(self._cursor.execute, sql, parameters))
        return self

    async def executemany(self, sql, parameters, /):
        await self._schedule(partial(self._cursor.executemany, sql, parameters))
        return self

    async def executescript(self, sql_script, /):
        await self._schedule(partial(self._cursor.executescript, sql_script))
        return self

    async def fetchall(self):
        return await self._schedule(self._cursor.fetchall)

    async def fetchmany(self, size=None):
        return await self._schedule(partial(self._cursor.fetchmany, size))

    async def fetchone(self):
        return await self._schedule(self._cursor.fetchone)

    @property
    def arraysize(self):
        return self._cursor.arraysize

    @arraysize.setter
    def arraysize(self, value):
        self._cursor.arraysize = value

    @property
    def connection(self):
        # Note - this returns an sqlite3.Connection, not an asqlite3.Connection, object.
        return self._cursor.connection

    @property
    def description(self):
        return self._cursor.description

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def row_factory(self):
        return self._cursor.row_factory

    @row_factory.setter
    def row_factory(self, value):
        self._cursor.row_factory = value


class Connection(threading.Thread):

    def __init__(self, database, **kwargs):
        super().__init__()
        self.database = database
        self.kwargs = kwargs
        self.jobs = queue.Queue()
        self.done_event = asyncio.Event()
        self.conn = None

    def _schedule(self, job):
        future = self.loop.create_future()
        self.jobs.put((future, job))
        return future

    async def main_loop(self):
        # Runs in the database thread
        self.conn = conn = sqlite3.connect(self.database, **self.kwargs)
        try:
            while True:
                item = self.jobs.get()
                if item is None:
                    break
                future, job = item
                try:
                    self.loop.call_soon_threadsafe(future.set_result, job())
                except BaseException as e:
                    self.loop.call_soon_threadsafe(future.set_exception, e)
        finally:
            self.conn = None
            conn.close()
            self.loop.call_soon_threadsafe(self.done_event.set)

    async def close(self):
        self.jobs.put(None)
        await self.done_event.wait()

    async def cursor(self):
        return Cursor(self._schedule, await self._schedule(self.conn.cursor))

    # @async_wrap('commit')
    # @async_wrap('rollback')
    # @async_wrap('executemany')
    # @async_wrap('executescript')
    async def execute(self, *args, **kwargs):
        cursor = await self._schedule(partial(self.conn.execute, *args, **kwargs))
        return Cursor(self._schedule, cursor)

    def run(self):
        # Run main_loop in this thread
        asyncio.run(self.main_loop())

    async def __aenter__(self):
        self.loop = asyncio.get_running_loop()
        self.start()
        await self._schedule(lambda : 0)
        return self

    async def __aexit__(self, typ, val, tb):
        await self.close()


connect = Connection
