import asyncio
import sqlite3

import pytest

from asqlite3 import *


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
                assert await cursor.execute('SELECT * FROM T')
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
                    result = await cursor.executescript(sql_script='')
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

    def test_fetchmany(self, size=None):
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

    def test_arraysize(self):
        async def test():
            async with connect(':memory:') as conn:
                cursor = await conn.cursor()
                assert cursor.arraysize == cursor._cursor.arraysize
                cursor.arraysize = 123
                assert cursor._cursor.arraysize == 123

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
                params = ((1, ), (2, ))
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
                cursor.row_factory = sqlite3.Row
                assert cursor.row_factory is sqlite3.Row
                assert cursor._cursor.row_factory is sqlite3.Row

        asyncio.run(test())


class TestConnection:

    def test_connect(self):
        async def test():
            async with connect(':memory:') as conn:
                pass

        asyncio.run(test())

    def test_execute(self):
        async def test():
            async with connect(':memory:') as conn:
                cursor = await conn.execute('SELECT 1, 5')
                assert await cursor.fetchone() == (1, 5)

        asyncio.run(test())
