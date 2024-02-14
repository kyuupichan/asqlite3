# Copyright (c) 2024 Neil Booth
#
# All rights reserved.
#
# See the file "LICENCE" for information about the copyright
# and warranty status of this software.

'''An asyncio version of sqlite3.'''

import asyncio
import queue
import sqlite3
import sys
import threading


class Cursor:
    '''An asynchronous wrapper around an sqlite3.Cursor object.'''

    def __init__(self, schedule, cursor):
        self.schedule = schedule
        self._cursor = cursor

    def __aiter__(self):
        async def iterate_rows():
            while True:
                rows = await self.schedule(self._cursor.fetchmany)
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
        await self.schedule(self._cursor.close)

    async def execute(self, sql, parameters=(), /):
        await self.schedule(self._cursor.execute, sql, parameters)
        return self

    async def executemany(self, sql, parameters, /):
        await self.schedule(self._cursor.executemany, sql, parameters)
        return self

    async def executescript(self, sql_script, /):
        await self.schedule(self._cursor.executescript, sql_script)
        return self

    async def fetchall(self):
        return await self.schedule(self._cursor.fetchall)

    async def fetchmany(self, size=None):
        return await self.schedule(self._cursor.fetchmany, size)

    async def fetchone(self):
        return await self.schedule(self._cursor.fetchone)

    async def setinputsizes(self, sizes):
        return await self.schedule(self._cursor.setinputsizes, sizes)

    async def setoutputsize(self, size, column=None):
        return await self.schedule(self._cursor.setoutputsize, size, column)

    @property
    def arraysize(self):
        return self._cursor.arraysize

    @arraysize.setter
    def arraysize(self, value):
        self._cursor.arraysize = value

    @property
    def connection(self):
        return self.schedule.__self__

    @property
    def sqlite3_connection(self):
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


class Connection:
    '''An asynchronous wrapper around an sqlite3.Connection object.'''

    def __init__(self):
        self._jobs = queue.Queue()
        self._closed = True
        self._conn = None
        self._loop = asyncio.get_running_loop()
        self._thread = None

    async def _connect(self, database, kwargs):
        self._thread = threading.Thread(target=asyncio.run, args=(self._thread_loop(), ))
        self._thread.start()
        self._closed = False
        self._conn = await self.schedule(sqlite3.connect, database, **kwargs)

    async def _thread_loop(self):
        def set_result(future, value):
            if not future.done():
                future.set_result(value)

        def set_exception(future, exc):
            if not future.done():
                future.set_exception(exc)

        call_soon = self._loop.call_soon_threadsafe
        while True:
            item = self._jobs.get()
            if item is None:
                break

            future, func, args, kwargs = item
            try:
                call_soon(set_result, future, func(*args, **kwargs))
            except BaseException as e:
                call_soon(set_exception, future, e)

    def schedule(self, func, *args, **kwargs):
        if self._closed:
            raise RuntimeError('DB connection is closed')
        future = self._loop.create_future()
        self._jobs.put((future, func, args, kwargs))
        return future

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, _exc_value, _tb):
        if self.in_transaction:
            if exc_type:
                await self.rollback()
            else:
                await self.commit()

    async def cursor(self, factory=Cursor):
        return factory(self.schedule, await self.schedule(self._conn.cursor))

    async def commit(self):
        await self.schedule(self._conn.commit)

    async def rollback(self):
        await self.schedule(self._conn.rollback)

    async def close(self):
        if not self._closed:
            if self._conn:
                self.schedule(self._conn.close)  # No need to await this
            # Prevent new jobs being added to the queue, and wait for existing jobs to complete
            self._closed = True
            self._jobs.put(None)
            self._thread.join()

    async def execute(self, sql, parameters=(), /):
        cursor = await self.schedule(self._conn.execute, sql, parameters)
        return Cursor(self.schedule, cursor)

    async def executemany(self, sql, parameters, /):
        cursor = await self.schedule(self._conn.executemany, sql, parameters)
        return Cursor(self.schedule, cursor)

    async def executescript(self, sql_script, /):
        cursor = await self.schedule(self._conn.executescript, sql_script)
        return Cursor(self.schedule, cursor)

    async def create_function(self, name, narg, func, /, *, deterministic=False):
        await self.schedule(self._conn.create_function, name, narg, func,
                            deterministic=deterministic)

    async def create_aggregate(self, name, narg, aggregate_class, /):
        await self.schedule(self._conn.create_aggregate, name, narg, aggregate_class)

    async def create_collation(self, name, callable, /):
        await self.schedule(self._conn.create_collation, name, callable)

    async def set_authorizer(self, authorizer_callback, /):
        await self.schedule(self._conn.set_authorizer, authorizer_callback)

    async def set_progress_handler(self, handler, /, n):
        await self.schedule(self._conn.set_progress_handler, handler, n)

    async def set_trace_callback(self, trace_callback, /):
        await self.schedule(self._conn.set_trace_callback, trace_callback)

    if hasattr(sqlite3.Connection, 'enable_load_extension'):
        async def enable_load_extension(self, enable):
            await self.schedule(self._conn.enable_load_extension, enable)

        async def load_extension(self, path):
            await self.schedule(self._conn.load_extension, path)

    async def iterdump(self):
        '''Returns an asynchronous iterator.'''
        # Need to read the lines from iterdump in the DB thread
        def enqueue_lines(lines):
            for line in self._conn.iterdump():
                lines.put(line)
            lines.put(None)

        # And to return the lines from the caller's thread
        async def read_lines(lines):
            while True:
                line = lines.get()
                if line is None:
                    break
                yield line

        lines = queue.Queue(maxsize=100)
        self.schedule(enqueue_lines, lines)
        return read_lines(lines)

    async def iterdump_sync(self):
        '''Returns a synchronous iterator that must be iterated via a call to schedule().'''
        return await self.schedule(self._conn.iterdump)

    async def backup(self, target, *, pages=-1, progress=None, name="main", sleep=0.250):
        if isinstance(target, Connection):
            target = target._conn
        await self.schedule(self._conn.backup, target, pages=pages, progress=progress,
                            name=name, sleep=sleep)

    if sys.version_info >= (3, 11):
        async def create_window_function(self, name, num_params, aggregate_class, /):
            await self.schedule(self._conn.create_window_function, name,
                                num_params, aggregate_class)

        async def blobopen(self, table, column, row, /, *, readonly=False, name='main'):
            return await self.schedule(self._conn.blobopen, table, column, row,
                                       readonly=readonly, name=name)

        async def serialize(self, *, name='main'):
            return await self.schedule(self._conn.serialize, name=name)

        async def deserialize(self, data, /, *, name='main'):
            return await self.schedule(self._conn.deserialize, data, name=name)

        async def getlimit(self, category, /):
            return await self.schedule(self._conn.getlimit, category)

        async def setlimit(self, category, limit, /):
            return await self.schedule(self._conn.setlimit, category, limit)

    if sys.version_info >= (3, 12):
        async def getconfig(self, op, /):
            return await self.schedule(self._conn.getconfig, op)

        async def setconfig(self, op, enable=True, /):
            return await self.schedule(self._conn.setconfig, op, enable)

        async def autocommit_get(self):
            return await self.schedule(getattr, self._conn, 'autocommit')

        async def autocommit_set(self, value):
            return await self.schedule(setattr, self._conn, 'autocommit', value)

    def interrupt(self):
        return self._conn.interrupt()

    @property
    def isolation_level(self):
        return self._conn.isolation_level

    @isolation_level.setter
    def isolation_level(self, value):
        self._conn.isolation_level = value

    @property
    def in_transaction(self):
        return self._conn.in_transaction

    @property
    def row_factory(self):
        return self._conn.row_factory

    @row_factory.setter
    def row_factory(self, value):
        self._conn.row_factory = value

    @property
    def text_factory(self):
        return self._conn.text_factory

    @text_factory.setter
    def text_factory(self, value):
        self._conn.text_factory = value

    @property
    def total_changes(self):
        return self._conn.total_changes


class Connector:

    def __init__(self, database, *, timeout=5.0, detect_types=0, isolation_level='DEFERRED',
                 check_same_thread=True, factory=sqlite3.Connection, cached_statements=128,
                 uri=False, autocommit=None):
        self._database = database
        self._kwargs = {'timeout': timeout, 'detect_types': detect_types,
                        'isolation_level': isolation_level, 'check_same_thread': check_same_thread,
                        'factory': factory, 'cached_statements': cached_statements, 'uri': uri}
        if autocommit is not None:
            self._kwargs['autocommit'] = autocommit
        self._conn = Connection()

    async def __aenter__(self):
        failed = True
        try:
            await self._conn._connect(self._database, self._kwargs)
            failed = False
        finally:
            if failed:
                await self._conn.close()

        return self._conn

    async def __aexit__(self, *args):
        await self._conn.close()


connect = Connector
