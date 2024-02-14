# Copyright (c) 2024 Neil Booth
#
# All rights reserved.
#
# See the file "LICENCE" for information about the copyright
# and warranty status of this software.

import asyncio
import os
import sqlite3
import sys
import threading
import time

import pytest

import asqlite3

from asqlite3 import (
    connect, Connection, Cursor, Row,
    ProgrammingError, OperationalError, DatabaseError,
    SQLITE_OK, SQLITE_DENY, SQLITE_CREATE_TABLE, asqlite3_version, asqlite3_version_str,
)


class TestCursor:

    def test_context_manager(self):
        async def test():
            async with connect(':memory:') as conn:
                async with (await conn.execute('SELECT 1, 5')) as cursor:
                    assert await cursor.fetchone() == (1, 5)

        asyncio.run(test())

    def test_iterable(self):
        async def test():
            async with connect(':memory:') as conn:
                sql = ' UNION '.join((f'SELECT {n}, {n * 2}') for n in range(100))
                cursor = await conn.execute(sql)
                n = 0
                async for row in cursor:
                    assert row == (n, n * 2)
                    n += 1

        asyncio.run(test())

    def test_close(self):
        with sqlite3.connect(':memory:') as conn:
            cursor = conn.cursor()
            assert cursor.close() is None

        async def test():
            async with connect(':memory:') as conn:
                cursor = await conn.execute('SELECT 1, 5')
                assert await cursor.close() is None
                with pytest.raises(ProgrammingError):
                    await cursor.fetchone()

        asyncio.run(test())

    def test_execute(self):
        with sqlite3.connect(':memory:') as conn:
            cursor = conn.cursor()
            with pytest.raises(TypeError):
                cursor.execute('SELECT 1, 5', parameters=())
            assert cursor.execute('SELECT 1, 5', ()) is cursor
            assert cursor.fetchone() == (1, 5)

        async def test():
            async with connect(':memory:') as conn:
                cursor = await conn.cursor()
                assert isinstance(cursor, Cursor)
                with pytest.raises(TypeError):
                    await cursor.execute('SELECT 1, 5', parameters=())
                assert await cursor.execute('SELECT 1, 5', ()) is cursor
                assert await cursor.fetchone() == (1, 5)

        asyncio.run(test())

    def test_executemany(self):
        with sqlite3.connect(':memory:') as conn:
            cursor = conn.cursor()
            cursor.execute('CREATE TABLE T(x);')
            params = ((1, ), (2, ))
            with pytest.raises(TypeError):
                cursor.executemany('INSERT INTO T VALUES(?)', parameters=params)
            assert cursor.executemany('INSERT INTO T VALUES(?)', params) is cursor

        async def test():
            async with connect(':memory:') as conn:
                cursor = await conn.cursor()
                assert isinstance(cursor, Cursor)
                await cursor.execute('CREATE TABLE T(x);')
                params = ((1, ), (2, ))
                with pytest.raises(TypeError):
                    await cursor.executemany('INSERT INTO T VALUES(?)', parameters=params)
                assert await cursor.executemany('INSERT INTO T VALUES(?)', params) is cursor
                assert await cursor.fetchall() == []
                assert await cursor.execute('SELECT * FROM T') is cursor
                assert await cursor.fetchall() == list(params)

        asyncio.run(test())

    def test_executescript(self):
        with sqlite3.connect(':memory:') as conn:
            cursor = conn.cursor()
            with pytest.raises(TypeError):
                cursor.executescript(sql_script='CREATE TABLE T(x); INSERT INTO T Values(1);')
            result = cursor.executescript('CREATE TABLE T(x); INSERT INTO T Values(1);')
            assert result is cursor

        async def test():
            async with connect(':memory:') as conn:
                cursor = await conn.cursor()
                with pytest.raises(TypeError):
                    await cursor.executescript(sql_script='')
                assert (await cursor.executescript('CREATE TABLE T(x); INSERT INTO T Values(1);')
                        is cursor)
                assert await cursor.execute('SELECT * FROM T')
                assert await cursor.fetchall() == [(1, )]

        asyncio.run(test())

    def test_fetchall(self):
        async def test():
            async with connect(':memory:') as conn:
                cursor = await conn.execute('SELECT 1, 5')
                assert await cursor.fetchall() == [(1, 5)]

        asyncio.run(test())

    def test_fetchmany(self):
        async def test():
            async with connect(':memory:') as conn:
                sql = ' UNION '.join((f'SELECT {n}, {n * 2}') for n in range(10))
                cursor = await conn.execute(sql)
                assert await cursor.fetchmany(size=3) == [(0, 0), (1, 2), (2, 4)]

        asyncio.run(test())

    def test_fetchone(self):
        async def test():
            async with connect(':memory:') as conn:
                cursor = await conn.execute('SELECT 1, 5')
                assert await cursor.fetchone() == (1, 5)

        asyncio.run(test())

    def test_setinputsizes(self):
        async def test():
            async with connect(':memory:') as conn:
                cursor = await conn.execute('SELECT 1, 5')
                await cursor.setinputsizes([2])

        asyncio.run(test())

    def test_setoutputsize(self):
        async def test():
            async with connect(':memory:') as conn:
                cursor = await conn.execute('SELECT 1, 5')
                await cursor.setoutputsize(12, 0)

        asyncio.run(test())

    def test_arraysize(self):
        async def test():
            async with connect(':memory:') as conn:
                cursor = await conn.cursor()
                assert cursor.arraysize == cursor._cursor.arraysize
                cursor.arraysize = 123
                assert cursor._cursor.arraysize == 123

        asyncio.run(test())

    def test_description(self):
        async def test():
            async with connect(':memory:') as conn:
                cursor = await conn.execute('SELECT 1, 5')
                assert cursor.description == cursor._cursor.description

        asyncio.run(test())

    def test_rowcount(self):
        async def test():
            async with connect(':memory:') as conn:
                cursor = await conn.cursor()
                assert cursor.rowcount == -1
                await cursor.execute('CREATE TABLE T(x);')
                assert cursor.rowcount == -1
                params = ((1, ), (2, ))
                assert await cursor.executemany('INSERT INTO T VALUES(?)', params) is cursor
                assert cursor.rowcount == 2

        asyncio.run(test())

    def test_lastrowid(self):
        async def test():
            async with connect(':memory:') as conn:
                cursor = await conn.cursor()
                assert cursor.lastrowid is None
                await cursor.execute('CREATE TABLE T(x);')
                await cursor.execute('INSERT INTO T VALUES(1)')
                assert cursor.lastrowid == 1
                await cursor.execute('INSERT INTO T VALUES(0)')
                assert cursor.lastrowid == 2

        asyncio.run(test())

    def test_row_factory(self):
        async def test():
            async with connect(':memory:') as conn:
                cursor = await conn.cursor()
                assert cursor.row_factory is None
                assert cursor._cursor.row_factory is None
                cursor.row_factory = Row
                assert cursor.row_factory is Row
                assert cursor._cursor.row_factory is Row

        asyncio.run(test())

    def test_connection(self):
        async def test():
            async with connect(':memory:') as conn:
                cursor = await conn.cursor()
                assert cursor.connection is conn
                assert isinstance(cursor.connection, Connection)

        asyncio.run(test())

    def test_sqlite3_connection(self):
        async def test():
            async with connect(':memory:') as conn:
                cursor = await conn.cursor()
                assert cursor.sqlite3_connection is cursor._cursor.connection
                assert isinstance(cursor.sqlite3_connection, sqlite3.Connection)

        asyncio.run(test())


class TestConnection:

    def test_close_no_connect(self):
        async def test():
            conn = Connection()
            await conn.close()

        asyncio.run(test())

    def test_thread_closed_bad_invocation(self):
        async def test():
            count = threading.active_count()
            with pytest.raises(TypeError):
                async with connect(None):
                    pass
            assert threading.active_count() == count

        asyncio.run(test())

    def test_connect(self):
        async def test():
            async with connect(':memory:') as conn:
                assert isinstance(conn, Connection)

        asyncio.run(test())

    def test_connect_args(self):
        async def test():
            async with connect(':memory:', isolation_level="IMMEDIATE", check_same_thread=True):
                pass

        asyncio.run(test())

    def test_connect_autocommit_arg(self):
        async def test():
            if sys.version_info < (3, 12):
                with pytest.raises(TypeError):
                    await connect(':memory:', autocommit=False).__aenter__()
            else:
                async with connect(':memory:', autocommit=False):
                    pass

        asyncio.run(test())

    def test_connect_args_bad(self):
        async def test():
            with pytest.raises(TypeError):
                await connect(':memory:', zombie=6)

        asyncio.run(test())

    def test_closed(self):
        async def test():
            async with connect(':memory:') as conn:
                pass
            with pytest.raises(RuntimeError):
                await conn.execute('SELECT 1, 5')

        asyncio.run(test())

    def test_close(self):
        async def test():
            async with connect(':memory:') as conn:
                # Don't await, so that the context manager is exited immediately
                conn.schedule(time.sleep, 0.02)
            assert conn._closed
            assert conn._jobs.empty()

        asyncio.run(test())

    def test_close_idempotent(self):
        async def test():
            async with connect(':memory:') as conn:
                pass
            await conn.close()

        asyncio.run(test())

    def test_cursor(self):

        class MyCursor(Cursor):
            pass

        async def test():
            async with connect(':memory:') as conn:
                cursor = await conn.cursor(factory=MyCursor)
                assert isinstance(cursor, MyCursor)

        asyncio.run(test())

    def test_cursor_closed(self):
        async def test():
            async with connect(':memory:') as conn:
                async with await conn.cursor() as cursor:
                    pass
                with pytest.raises(ProgrammingError) as e:
                    await cursor.execute('BEGIN')
                assert 'annot operate on a closed cursor' in str(e.value)

        asyncio.run(test())

    def test_commit(self):
        with sqlite3.connect(':memory:') as conn:
            conn.execute('BEGIN')
            conn.execute('CREATE TABLE T(x)')
            assert conn.commit() is None
            assert conn.execute('SELECT * from T').fetchall() == []

        async def test():
            async with connect(':memory:') as conn:
                await conn.execute('BEGIN')
                await conn.execute('CREATE TABLE T(x)')
                assert await conn.commit() is None
                assert await (await conn.execute('SELECT * from T')).fetchall() == []

        asyncio.run(test())

    def test_rollback(self):
        with sqlite3.connect(':memory:') as conn:
            conn.execute('BEGIN')
            conn.execute('CREATE TABLE T(x)')
            assert conn.rollback() is None
            with pytest.raises(OperationalError):
                conn.execute('SELECT * from T')

        async def test():
            async with connect(':memory:') as conn:
                await conn.execute('BEGIN')
                await conn.execute('CREATE TABLE T(x)')
                assert await conn.rollback() is None
                with pytest.raises(OperationalError):
                    await conn.execute('SELECT * from T')

        asyncio.run(test())

    def test_interrupt(self):
        conn = None
        from threading import Thread, Event

        def interrupt():
            e.wait()
            assert conn.interrupt() is None

        e = Event()
        t = Thread(target=interrupt)
        t.start()

        async def test():
            nonlocal conn
            async with connect(':memory:') as conn:
                await conn.execute('CREATE TABLE T(x)')
                await conn.executemany('INSERT INTO T VALUES(?)',
                                       ((os.urandom(1000), ) for _ in range(500)))

                with pytest.raises(OperationalError):
                    cursor = await conn.execute('SELECT * from T')
                    e.set()
                    await cursor.fetchall()

        asyncio.run(test())

    def test_execute(self):
        with sqlite3.connect(':memory:') as conn:
            with pytest.raises(TypeError):
                conn.execute('SELECT 1, 5', parameters=())
            cursor = conn.execute('SELECT 1, 5', ())
            assert isinstance(cursor, sqlite3.Cursor)
            assert cursor.fetchone() == (1, 5)

        async def test():
            async with connect(':memory:') as conn:
                with pytest.raises(TypeError):
                    await conn.execute('SELECT 1, 5', parameters=())
                cursor = await conn.execute('SELECT 1, 5', ())
                assert isinstance(cursor, Cursor)
                assert await cursor.fetchone() == (1, 5)

        asyncio.run(test())

    def test_executemany(self):
        with sqlite3.connect(':memory:') as conn:
            conn.execute('CREATE TABLE T(x);')
            params = ((1, ), (2, ))
            with pytest.raises(TypeError):
                conn.executemany('INSERT INTO T VALUES(?)', parameters=params)
            cursor = conn.executemany('INSERT INTO T VALUES(?)', params)
            assert isinstance(cursor, sqlite3.Cursor)

        async def test():
            async with connect(':memory:') as conn:
                await conn.execute('CREATE TABLE T(x);')
                params = ((1, ), (2, ))
                with pytest.raises(TypeError):
                    await conn.executemany('INSERT INTO T VALUES(?)', parameters=params)
                cursor = await conn.executemany('INSERT INTO T VALUES(?)', params)
                assert isinstance(cursor, Cursor)
                assert await cursor.fetchall() == []
                cursor = await conn.execute('SELECT * FROM T')
                assert await cursor.fetchall() == list(params)

        asyncio.run(test())

    def test_executescript(self):
        with sqlite3.connect(':memory:') as conn:
            with pytest.raises(TypeError):
                conn.executescript(sql_script='CREATE TABLE T(x); INSERT INTO T Values(1);')
            result = conn.executescript('CREATE TABLE T(x); INSERT INTO T Values(1);')
            assert isinstance(result, sqlite3.Cursor)

        async def test():
            async with connect(':memory:') as conn:
                with pytest.raises(TypeError):
                    await conn.executescript(sql_script='')
                cursor = await conn.executescript('CREATE TABLE T(x); INSERT INTO T Values(1);')
                assert isinstance(cursor, Cursor)
                cursor = await conn.execute('SELECT * FROM T')
                assert await cursor.fetchall() == [(1, )]

        asyncio.run(test())

    def test_create_function(self):
        def myfunc(x):
            return x * 8

        with sqlite3.connect(':memory:') as conn:
            result = conn.create_function('myfunc', 1, myfunc, deterministic=True)
            assert result is None
            assert conn.execute('SELECT myfunc(5)').fetchone() == (40, )

        async def test():
            async with connect(':memory:') as conn:
                # sqlite3 in 3.13 deprecated name as a named argument; removed from 3.15
                with pytest.raises(TypeError):
                    await conn.create_function(name='mf')
                result = await conn.create_function('mf', 1, myfunc, deterministic=True)
                assert result is None
                cursor = await conn.execute('SELECT mf(5)')
                assert await cursor.fetchone() == (40, )
                result = await conn.create_function('mf', 1, None)
                with pytest.raises(OperationalError):
                    await conn.execute('SELECT mf(5)')

        asyncio.run(test())

    def test_create_aggregate(self):
        class MySum:
            def __init__(self):
                self.count = 0

            def step(self, value):
                self.count += value

            def finalize(self):
                return self.count

        with sqlite3.connect(':memory:') as conn:
            assert conn.create_aggregate('mysum', -1, MySum) is None
            cursor = conn.execute('CREATE TABLE T(x)')
            cursor.executemany('INSERT INTO T VALUES(?)', ((1, ), (5, )))
            assert cursor.execute('SELECT mysum(x) FROM T').fetchone() == (6, )

        async def test():
            async with connect(':memory:') as conn:
                with pytest.raises(TypeError):
                    await conn.create_aggregate('mysum2', aggregate_class=MySum)
                assert await conn.create_aggregate('mysum2', -1, MySum) is None
                cursor = await conn.execute('CREATE TABLE T(x)')
                await cursor.executemany('INSERT INTO T VALUES(?)', ((1, ), (5, )))
                await cursor.execute('SELECT mysum2(x) FROM T')
                await cursor.fetchone() == (6, )
                assert await conn.create_aggregate('mysum2', -1, None) is None
                with pytest.raises(OperationalError):
                    await cursor.execute('SELECT mysum2(x) FROM T')

        asyncio.run(test())

    def test_create_collation(self):
        def collate_reverse(a, b):
            if a == b:
                return 0
            return 1 if a < b else -1

        with sqlite3.connect(':memory:') as conn:
            assert conn.create_collation('reverse', collate_reverse) is None
            cursor = conn.execute('CREATE TABLE T(x)')
            cursor.executemany('INSERT INTO T VALUES(?)', (("a", ), ("b", )))
            assert (cursor.execute('SELECT x FROM T ORDER BY x COLLATE reverse').fetchall()
                    == [('b', ), ('a', )])

        async def test():
            async with connect(':memory:') as conn:
                assert await conn.create_collation('reverse2', collate_reverse) is None
                await conn.execute('CREATE TABLE T(x)')
                await conn.executemany('INSERT INTO T VALUES(?)', (("a", ), ("b", ), ("a", )))
                cursor = await conn.execute('SELECT x FROM T ORDER BY x COLLATE reverse2')
                assert await cursor.fetchall() == [('b', ), ('a', ), ('a', )]
                assert await conn.create_collation('reverse2', None) is None
                with pytest.raises(OperationalError):
                    await conn.execute('SELECT x FROM T ORDER BY x COLLATE reverse2')

        asyncio.run(test())

    @pytest.mark.skipif(sys.version_info < (3, 11), reason='requires Python 3.11')
    def test_create_window_function(self):
        class WindowSum:
            def __init__(self):
                self.count = 0

            def step(self, value):
                self.count += value

            def value(self):
                return self.count

            def inverse(self, value):
                self.count -= value

            def finalize(self):
                return self.count

        values = [('a', 4), ('b', 5), ('c', 3), ('d', 8), ('e', 1)]
        answer = [('a', 9), ('b', 12), ('c', 16), ('d', 12), ('e', 9)]

        with sqlite3.connect(':memory:') as conn:
            cursor = conn.execute('CREATE TABLE T(x, y)')
            cursor.executemany('INSERT INTO T VALUES(?, ?)', values)
            with pytest.raises(TypeError):
                conn.create_window_function('sumint', 1, aggregate_class=WindowSum)
            assert conn.create_window_function('sumint', 1, WindowSum) is None
            result = cursor.execute('''SELECT x, sumint(y) OVER (
               ORDER BY x ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING) AS sum_y
               FROM T ORDER BY x''').fetchall()
            assert result == answer

        async def test():
            async with connect(':memory:') as conn:
                cursor = await conn.execute('CREATE TABLE T(x, y)')
                await cursor.executemany('INSERT INTO T VALUES(?, ?)', values)
                with pytest.raises(TypeError):
                    await conn.create_window_function('sumint', 1, aggregate_class=WindowSum)
                assert await conn.create_window_function('sumint', 1, WindowSum) is None
                await cursor.execute('''SELECT x, sumint(y) OVER (
                   ORDER BY x ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING) AS sum_y
                   FROM T ORDER BY x''')
                assert await cursor.fetchall() == answer

        asyncio.run(test())

    @pytest.mark.skipif(sys.version_info < (3, 11), reason='requires Python 3.11')
    def test_blob_open(self):
        def use_blob(blob):
            prefix = b'foo bar baz'
            assert blob.read() == bytes(100)
            blob.seek(0)
            blob.write(prefix)
            blob.seek(0)
            assert blob.read() == prefix + bytes(100 - len(prefix))

        with sqlite3.connect(':memory:') as conn:
            conn.execute('CREATE TABLE T(b BLOB)')
            conn.execute('INSERT INTO T VALUES (zeroblob(100))')
            use_blob(conn.blobopen('T', 'b', 1))

        async def test():
            async with connect(':memory:') as conn:
                await conn.execute('CREATE TABLE T(b BLOB)')
                await conn.execute('INSERT INTO T VALUES (zeroblob(100))')
                await conn.schedule(use_blob, await conn.blobopen('T', 'b', 1))

        asyncio.run(test())

    def test_set_authorizer(self):
        def authorizer(action, arg1, _arg2, _db_name, _trigger_name):
            if action == SQLITE_CREATE_TABLE and arg1 == 'T':
                return SQLITE_DENY
            return SQLITE_OK

        with sqlite3.connect(':memory:') as conn:
            assert conn.set_authorizer(authorizer) is None
            conn.execute('CREATE TABLE Z(x)')
            with pytest.raises(DatabaseError) as e:
                conn.execute('CREATE TABLE T(x)')
            assert str(e.value) == "not authorized"

        async def test():
            async with connect(':memory:') as conn:
                with pytest.raises(TypeError):
                    await conn.set_authorizer(authorizer_callback=authorizer)
                assert await conn.set_authorizer(authorizer) is None
                await conn.execute('CREATE TABLE Z(x)')
                with pytest.raises(DatabaseError) as e:
                    await conn.execute('CREATE TABLE T(x)')
                assert str(e.value) == "not authorized"
                # None only works from Python 3.11
                if sys.version_info >= (3, 11):
                    assert await conn.set_authorizer(None) is None
                    await conn.execute('CREATE TABLE T(x)')

        asyncio.run(test())

    def test_set_progress_handler(self):
        def progress():
            return SQLITE_DENY

        async def test():
            async with connect(':memory:') as conn:
                with pytest.raises(TypeError):
                    await conn.set_progress_handler(progress_handler=progress, n=2)
                assert await conn.set_progress_handler(progress, n=2) is None
                with pytest.raises(OperationalError) as e:
                    await conn.execute('CREATE TABLE Z(x, y, z)')
                assert str(e.value) == "interrupted"
                assert await conn.set_progress_handler(None, 2) is None
                await conn.execute('CREATE TABLE Z(x, y, z)')

        asyncio.run(test())

    def test_set_trace_callback(self):
        stmts = []

        def trace_callback(stmt):
            stmts.append(stmt)

        async def test():
            async with connect(':memory:') as conn:
                with pytest.raises(TypeError):
                    await conn.set_trace_callback(trace_callback=trace_callback)
                assert await conn.set_trace_callback(trace_callback) is None
                sql = 'CREATE TABLE Z(x, y, z)'
                await conn.execute(sql)
                assert stmts == [sql]
                assert await conn.set_trace_callback(None) is None
                await conn.execute('CREATE TABLE Y(x, y, z)')
                assert stmts == [sql]

        asyncio.run(test())

    @pytest.mark.skipif(not hasattr(sqlite3.Connection, 'enable_load_extension'),
                        reason='loadable extensions not compiled in')
    def test_load_extension(self):
        with sqlite3.connect(':memory:') as conn:
            assert conn.enable_load_extension(True) is None

        async def test():
            async with connect(':memory:') as conn:
                assert await conn.enable_load_extension(False) is None
                with pytest.raises(OperationalError) as e:
                    assert await conn.load_extension('foo') is None
                assert str(e.value) == 'not authorized'
                assert await conn.enable_load_extension(True) is None
                with pytest.raises(OperationalError):
                    assert await conn.load_extension('foo') is None

        asyncio.run(test())

    def test_iterdump(self):
        lines = []

        def collect_lines(sync_it):
            return list(line for line in sync_it)

        with sqlite3.connect(':memory:') as conn:
            sql = 'CREATE TABLE Z(x, y, z);'
            conn.execute(sql)
            lines = collect_lines(conn.iterdump())
            assert len(lines) == 3 and lines[1] == sql

        async def test():
            async with connect(':memory:') as conn:
                await conn.execute(sql)
                async_it = await conn.iterdump()
                assert lines == [line async for line in async_it]

                sync_it = await conn.iterdump_sync()
                assert await conn.schedule(collect_lines, sync_it) == lines

        asyncio.run(test())

    def test_backup(self, tmpdir):
        with sqlite3.connect(':memory:') as conn:
            sql = 'CREATE TABLE Z(x, y, z);'
            conn.execute(sql)
            with sqlite3.connect(os.path.join(tmpdir, 'dest.db')) as dest:
                assert conn.backup(dest) is None

        async def test():
            async with connect(':memory:') as conn:
                sql = 'CREATE TABLE Z(x, y, z);'
                await conn.execute(sql)
                async with connect(os.path.join(tmpdir, 'dest2.db')) as dest:
                    assert await conn.backup(dest) is None

        asyncio.run(test())

    @pytest.mark.skipif(sys.version_info < (3, 11), reason='requires Python 3.11')
    def test_serialize(self):
        sql = 'CREATE TABLE Z(x, y, z);'
        with sqlite3.connect(':memory:') as conn:
            conn.execute(sql)
            answer = conn.serialize()

        async def test():
            async with connect(':memory:') as conn:
                await conn.execute(sql)
                assert await conn.serialize(name='main') == answer

        asyncio.run(test())

    @pytest.mark.skipif(sys.version_info < (3, 11), reason='requires Python 3.11')
    def test_deserialize(self):
        sql = 'CREATE TABLE Z(x, y, z);'
        with sqlite3.connect(':memory:') as conn:
            conn.execute(sql)
            conn.execute('INSERT INTO Z VALUES(3,2,1)')
            raw = conn.serialize()
            assert conn.deserialize(raw, name='main') is None

        async def test():
            async with connect(':memory:') as conn:
                assert await conn.deserialize(raw, name='main') is None
                cursor = await conn.execute('SELECT * FROM Z')
                assert await cursor.fetchall() == [(3, 2, 1)]

        asyncio.run(test())

    @pytest.mark.skipif(sys.version_info < (3, 11), reason='requires Python 3.11')
    def test_limits(self):
        async def test():
            async with connect(':memory:') as conn:
                limit = await conn.getlimit(asqlite3.SQLITE_LIMIT_ATTACHED)
                assert isinstance(limit, int)
                assert await conn.setlimit(asqlite3.SQLITE_LIMIT_ATTACHED, limit - 1) == limit
                assert await conn.getlimit(asqlite3.SQLITE_LIMIT_ATTACHED) == limit - 1

        asyncio.run(test())

    @pytest.mark.skipif(sys.version_info < (3, 12), reason='requires Python 3.12')
    def test_config(self):
        async def test():
            async with connect(':memory:') as conn:
                value = await conn.getconfig(asqlite3.SQLITE_DBCONFIG_ENABLE_LOAD_EXTENSION)
                assert isinstance(value, bool)
                with pytest.raises(TypeError):
                    await conn.setconfig(asqlite3.SQLITE_DBCONFIG_ENABLE_LOAD_EXTENSION,
                                         enable=not value)
                assert await conn.setconfig(asqlite3.SQLITE_DBCONFIG_ENABLE_LOAD_EXTENSION,
                                            not value) is None
                assert (await conn.getconfig(asqlite3.SQLITE_DBCONFIG_ENABLE_LOAD_EXTENSION)) \
                    is not value

        asyncio.run(test())

    @pytest.mark.skipif(sys.version_info < (3, 12), reason='requires Python 3.12')
    def test_autocommit(self):
        with sqlite3.connect(':memory:') as conn:
            assert conn.autocommit == asqlite3.LEGACY_TRANSACTION_CONTROL
            conn.autocommit = True
            assert conn.autocommit is True
            conn.autocommit = False
            assert conn.autocommit is False

        async def test():
            async with connect(':memory:') as conn:
                assert await conn.autocommit_get() == asqlite3.LEGACY_TRANSACTION_CONTROL
                await conn.autocommit_set(True)
                assert await conn.autocommit_get() is True
                await conn.autocommit_set(False)
                assert await conn.autocommit_get() is False

        asyncio.run(test())

    def test_isolation_level(self):
        async def test():
            async with connect(':memory:') as conn:
                assert conn.isolation_level == conn._conn.isolation_level
                conn.isolation_level = 'IMMEDIATE'
                assert conn._conn.isolation_level == 'IMMEDIATE'
                conn.isolation_level = 'DEFERRED'
                assert conn._conn.isolation_level == 'DEFERRED'

        asyncio.run(test())

    def test_in_transaction(self):
        async def test():
            async with connect(':memory:') as conn:
                assert not conn.in_transaction
                await conn.execute('BEGIN')
                assert conn.in_transaction

        asyncio.run(test())

    def test_row_factory(self):
        async def test():
            async with connect(':memory:') as conn:
                assert conn.row_factory is None
                assert conn._conn.row_factory is None
                conn.row_factory = Row
                assert conn.row_factory is Row
                assert conn._conn.row_factory is Row

        asyncio.run(test())

    def test_text_factory(self):
        async def test():
            async with connect(':memory:') as conn:
                assert conn.text_factory is str
                assert conn._conn.text_factory is str
                conn.text_factory = bytes
                assert conn.text_factory is bytes
                assert conn._conn.text_factory is bytes

        asyncio.run(test())

    def test_total_changes(self):
        async def test():
            async with connect(':memory:') as conn:
                assert conn.total_changes == 0
                await conn.execute('CREATE TABLE T(x)')
                await conn.executemany('INSERT INTO T VALUES(?)',
                                       ((n, ) for n in range(100)))
                assert conn.total_changes == 100

        asyncio.run(test())

    def test_leave_with_context_commit(self, tmpdir):

        filename = os.path.join(tmpdir, 'test.sqlite')
        N = 100

        async def test():
            async with connect(filename) as conn:
                async with conn:
                    await conn.execute('CREATE TABLE T(x)')
                    await conn.executemany('INSERT INTO T VALUES(?)', ((n, ) for n in range(N)))

                async with connect(filename) as conn2:
                    cursor = await conn2.execute('SELECT * FROM T')
                    values = await cursor.fetchall()
                    assert len(values) == N

        asyncio.run(test())

    def test_leave_with_context_rollback(self, tmpdir):

        filename = os.path.join(tmpdir, 'test.sqlite')
        N = 100

        async def test():
            try:
                async with connect(filename) as conn:
                    async with conn:
                        await conn.execute('CREATE TABLE T(x)')
                        await conn.executemany('INSERT INTO T VALUES(?)',
                                               ((n, ) for n in range(N)))
                        raise ValueError
            except ValueError:
                pass

            async with connect(filename) as conn:
                cursor = await conn.execute('SELECT * FROM T')
                values = await cursor.fetchall()
                assert not values

        asyncio.run(test())

    def test_leave_connect_context_no_commit(self, tmpdir):

        filename = os.path.join(tmpdir, 'test.sqlite')
        N = 100

        async def test():
            async with connect(filename) as conn:
                await conn.execute('CREATE TABLE T(x)')
                await conn.executemany('INSERT INTO T VALUES(?)', ((n, ) for n in range(N)))

            async with connect(filename) as conn2:
                cursor = await conn2.execute('SELECT * FROM T')
                values = await cursor.fetchall()
                assert not values

        asyncio.run(test())


def test_module_constants():
    from asqlite3 import (
        complete_statement, enable_callback_tracebacks, register_adapter,
        register_converter, PARSE_COLNAMES, PARSE_DECLTYPES, SQLITE_IGNORE,
        apilevel, paramstyle, threadsafety, PrepareProtocol
    )

    assert not complete_statement('SELECT')
    assert complete_statement('SELECT 1;')
    assert enable_callback_tracebacks is not None
    assert register_adapter is not None
    assert register_converter is not None
    assert isinstance(PARSE_COLNAMES, int)
    assert isinstance(PARSE_DECLTYPES, int)
    assert isinstance(SQLITE_IGNORE, int)
    assert apilevel == "2.0"
    assert paramstyle == "qmark"
    assert threadsafety in (0, 1, 3)
    assert PrepareProtocol is not None

    for symbol in (
            '''SQLITE_CREATE_INDEX SQLITE_CREATE_TABLE SQLITE_CREATE_TEMP_INDEX
            SQLITE_CREATE_TEMP_TABLE SQLITE_CREATE_TEMP_VIEW SQLITE_CREATE_TRIGGER
            SQLITE_CREATE_VIEW SQLITE_DELETE SQLITE_DROP_INDEX SQLITE_DROP_TABLE
            SQLITE_DROP_TABLE SQLITE_DROP_TEMP_INDEX SQLITE_DROP_TEMP_TABLE
            SQLITE_DROP_TEMP_TRIGGER SQLITE_DROP_TEMP_VIEW SQLITE_DROP_TRIGGER
            SQLITE_DROP_TEMP_VIEW SQLITE_DROP_TRIGGER SQLITE_DROP_VIEW SQLITE_INSERT SQLITE_PRAGMA
            SQLITE_READ SQLITE_SELECT SQLITE_TRANSACTION SQLITE_UPDATE SQLITE_ATTACH SQLITE_DETACH
            SQLITE_ALTER_TABLE SQLITE_REINDEX SQLITE_ANALYZE SQLITE_CREATE_VTABLE
            SQLITE_DROP_VTABLE SQLITE_FUNCTION SQLITE_SAVEPOINT SQLITE_RECURSIVE''').split():
        assert isinstance(getattr(asqlite3, symbol), int)

    if sys.version_info >= (3, 11):
        assert asqlite3.Blob is not None
        for symbol in (
                '''SQLITE_LIMIT_LENGTH SQLITE_LIMIT_SQL_LENGTH SQLITE_LIMIT_COLUMN
        SQLITE_LIMIT_EXPR_DEPTH SQLITE_LIMIT_COMPOUND_SELECT SQLITE_LIMIT_VDBE_OP
        SQLITE_LIMIT_FUNCTION_ARG SQLITE_LIMIT_ATTACHED SQLITE_LIMIT_LIKE_PATTERN_LENGTH
        SQLITE_LIMIT_VARIABLE_NUMBER SQLITE_LIMIT_TRIGGER_DEPTH SQLITE_LIMIT_WORKER_THREADS
                ''').split():
            assert isinstance(getattr(asqlite3, symbol), int)

    if sys.version_info >= (3, 12):
        assert asqlite3.LEGACY_TRANSACTION_CONTROL is not None


def test_asqlite3_version():
    assert asqlite3_version_str == '.'.join(str(part) for part in asqlite3_version)


@pytest.mark.skipif(sys.version_info >= (3, 14), reason='requires Python < 3.14')
def test_deprecated(recwarn):
    assert not recwarn
    assert asqlite3.version is not None
    assert asqlite3.version_info is not None
    if sys.version_info >= (3, 12):
        assert len(recwarn) == 2
    else:
        assert not recwarn
