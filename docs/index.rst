===========
py-asqlite3
===========

An asynchronous wrapper for sqlite3.  The library wraps the entirety of sqlite3 (as
provided on your system) for every version of Python since Python 3.8.

The current version is |release|.

The project is hosted on `GitHub <https://github.com/kyuupichan/asqlite3/>`_.  and uses
Azure Pipelines for continuous integration.


Author and License
==================

The code was written by Neil Booth.  Python version at least 3.8 is required.

The code is released under the `MIT Licence
<https://github.com/kyuupichan/asqlite3/LICENCE>`_.


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

=========
Reference
=========

.. module:: asqlite3

Refer to the Python **sqlite3** documentation for full details of functions, constants and
methods; this documentation only covers points specific to **asqlite3**.


Module functions
================

.. function:: connect(database, *, timeout=5.0, detect_types=0, isolation_level='DEFERRED', \
                      check_same_thread=True, factory=sqlite3.Connection, cached_statements=128, \
                      uri=False, autocommit=sqlite3.LEGACY_TRANSACTION_CONTROL)
   :async:

   Open a connection to an SQLite database and return a `Connection`_ object.

   Note that the *autocommit* argument is only present For Python versions 3.12 and later.


Module constants
================

**asqilte3** provides all constants in the **sqlite3** module, in addition to some
relating only to aslite3.

.. data:: asqlite3_version_str

   A string giving the **asqlite3** version, e.g., '0.9'.

.. data:: asqlite3_version

   A tuple giving the **asqlite3** version, e.g., (0, 9).


Connection
==========

The ``Connection`` class wraps the Connection class of sqlite3 and provides all its
methods and properties.  ``Connection`` objects should be created by calling the
:func:`connect` function.

A connection can be used as as an asynchronous context manager, in which case the
connection will be closed when control leaves the block via the `__aexit__` method.

Successful creation of a `Connection` starts a thread in which all database interactions
using the connection must happen - this is enforced by sqlite itself.


Cursor
======

The Cursor class wraps the Cursor class of sqlite3 and provides all its methods and
properties.  Cursor objects should be created by calling the cursor() method on an asqlite
Connection object.

Cursor can be used as as an asynchronous context manager, in which case the cursor will be
closed when control leaves the block via the `__aexit__` method.

A cursor can be used as as an asynchronous iterator.  In such cases, rows are fetched
arraysize rows at a time.


Methods
-------

The following methods, with the exception of ``connection`` and ``sqlite3_connection`` are
asyncronous versions of the underlying **sqlite3** ``Cursor`` methods.  Except where
documented below, refer to the Python sqlite3 documentation for more details.

.. method:: Cursor.close()
      :async:

.. method:: Cursor.execute(sql, parameters=(), /)
      :async:

.. method:: Cursor.executemany(sql, parameters, /)
      :async:

.. method:: Cursor.executescript(sql_script, /)
      :async:

.. method:: Cursor.fetchall()
      :async:

.. method:: Cursor.fetchmany(size=cursor.arraysize)
      :async:

.. method:: Cursor.fetchone()
      :async:

.. property:: Cursor.arraysize

.. property:: Cursor.connection

   Returns an asqlite3 Connection object.

.. property:: Cursor.sqlite3_connection

   Returns the underlying sqlite3 Connection object.

.. property:: Cursor.description

.. property:: Cursor.lastrowid

.. property:: Cursor.rowcount

.. property:: Cursor.row_factory


Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
