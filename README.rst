========
asqlite3
========

An asynchronous wrapper for sqlite3.  The library wraps the entirety of sqlite3 (as
provided on your system) for every version of Python since Python 3.8.

The project uses Azure Pipelines for continuous integration.


Author and License
==================

The code was written by Neil Booth.  Python version at least 3.8 is required.

The code is released under the `MIT Licence
<https://github.com/kyuupichan/asqlite3/LICENCE>`_.


Documentation
=============

See `readthedocs <https://py-asqlite3.readthedocs.io/>`_.


Library Installation
====================

.. code-block:: bash

   $ pip install py-asqlite3


Getting Started
===============

Client example
--------------

.. code-block:: python

  import asqlite3
  import asyncio

  async def main():
      async with asqlite3.connect(':memory:') as conn:
          await conn.execute('CREATE TABLE T(x, y);')
          await conn.executemany('INSERT INTO T(x, y) VALUES(?, ?);',
                                 ((n, n * 2) for n in range(100)))
          cursor = await conn.execute('SELECT * FROM T;')
          n = 0
          # Cursors can be used as async iterators
          async for row in cursor:
              assert row == (n, n * 2)
              n += 1
          assert n == 100

  asyncio.run(main())


ChangeLog
=========


0.7.0
-----

* change behaviour of Connection context manager and document it.
* more tests


0.6.0
-----

* code cleanups and more tests.
* make close() idempotent.


0.5.0
-----

* initial release.
