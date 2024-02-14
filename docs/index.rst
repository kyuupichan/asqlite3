========
asqlite3
========

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


.. seealso::

   * :ref:`asqlite3-connection-context-manager`


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

   Open a connection to the database and start a thread to handle database requests.  This
   function is only intended to be used as part of an ``async with`` asynchronous context
   managercode block, in which case the target, **conn** below, is a `Connection`_ object:

     .. code-block:: python

        async with asqlite3.connect(filename) as conn:
            a code block

   When control leaves the block, the library closes the database connection and shuts
   down the thread cleanly, after waiting for pending operations to complete.  Note that
   leaving the block does *not* necessarily commit pending transactions.  For more
   information see sqlite3 module's documentation about Transaction Control.

   The *autocommit* argument is only present For Python versions 3.12 and later.

   See also :ref:`asqlite3-connection-context-manager`.


Module constants
================

**asqilte3** provides all constants in the **sqlite3** module, in addition to some new
ones:

.. data:: asqlite3_version_str

   A string giving the **asqlite3** version, e.g., '0.9'.

.. data:: asqlite3_version

   A tuple giving the **asqlite3** version, e.g., (0, 9).


Connection
==========

.. class:: Connection

  The ``Connection`` class wraps the Connection class of sqlite3 and provides all of its
  methods and properties.  ``Connection`` objects should be created by calling the
  :func:`connect` function.

  A connection can be used as as an asynchronous context manager, in which case the
  connection will be closed when control leaves the block via the `__aexit__` method.

  Successful entering of the context of a ``Connection`` via the `__aenter__` method
  starts a thread in which all uses of the database connection must happen - this is
  enforced by sqlite itself.  The only exception is :func:`interrupt`.

  Python 3.12 introduces the **autocommit** property of sqlite3 database connections.
  This property can only be accessed in the connection's thread, so explicit asynchronous
  :func:`autocommit_get` and :func:`autocommit_set` methods must be used to access this
  property.

  Python 3.13 deprecates the use of named arguments for some of these methods, intending
  to remove their support in Python 3.15.  Being a new library, **asqlite3** does not
  support the deprecated method signatures.

  .. method:: cursor(factory=Cursor)
      :async:

  .. method:: commit()
      :async:

  .. method:: rollback()
      :async:

  .. method:: close()
      :async:

  .. method:: execute(sql, parameters=(), /)
        :async:

  .. method:: executemany(sql, parameters, /)
        :async:

  .. method:: executescript(sql_script, /)
        :async:

  .. method:: create_function(name, narg, func, /, *, deterministic=False)
        :async:

  .. method:: create_aggregate(name, narg, aggregate_class, /)
        :async:

  .. method:: create_collation(name, callable, /)
        :async:

  .. method:: set_authorizer(authorizer_callback, /)
        :async:

  .. method:: set_progress_handler(handler, /, n)
        :async:

  .. method:: set_trace_callback(trace_callback, /)
        :async:

  .. method:: backup(target, *, pages=-1, progress=None, name="main", sleep=0.250)
        :async:

  .. method:: iterdump()
        :async:

        Returns an asynchronous iterator which can be used as follows:

        .. code-block::

           async for line in await conn.iterdump():
               print(line)

        See also :func:`iterdump_sync`.

  .. method:: iterdump_sync()
        :async:

        Returns a synchronous iterator.  As the iterator accesses the database connection,
        it must be used via a call to :func:`schedule`.  For example:

        .. code-block::

           def print_lines(lines):
               for line in lines:
                   print(line)

           sync_iter = await conn.iterdump_sync()
           await conn.schedule(print_lines, sync_iter)

  .. method:: schedule(func, *args, **kwargs)

        Schedule the synchronous function ``func`` to run in the thread of the database
        connection, passing it the given arguments.  Returns a future, which can be
        **await**-ed if the caller wishes to wait for the invocation to complete before
        continuing.

  .. method:: interrupt()

        Note this method is synchronous.

  The following methods are available if loadable extension support is compiled into
  Python's sqlite3 module:

  .. method:: enable_load_extension(enable)
        :async:

  .. method:: load_extension(path)
        :async:

  The following methods are available in Python versions 3.11 and later:

  .. method:: create_window_function(name, num_params, aggregate_class, /):
        :async:

  .. method:: blobopen(table, column, row, /, *, readonly=False, name='main')
        :async:

  .. method:: serialize(*, name='main')
        :async:

  .. method:: deserialize(data, /, *, name='main')
        :async:

  .. method:: getlimit(category, /)
        :async:

  .. method:: setlimit(category, limit, /)
        :async:

  The following methods are available in Python versions 3.12 and later:

  .. method:: getconfig(op, /)
        :async:

  .. method:: setconfig(op, enable=True, /)
        :async:

  .. method:: autocommit_get()
        :async:

        Return the **autocommit** property of the underlying sqlite3 connection.

  .. method:: autocommit_set(value)
        :async:

        Set the **autocommit** property of the underlying sqlite3 connection.

  .. property:: isolation_level

  .. property:: in_transaction

  .. property:: row_factory

  .. property:: text_factory

  .. property:: total_changes


Cursor objects
==============

.. class:: Cursor

  The ``Cursor`` class is an asynchronous wrapper of the Cursor class of sqlite3, and
  provides all its methods and properties.  ``Cursor`` objects should be created by
  calling the :func:`cursor` method on an asqlite :class:`Connection` object.

  A cursor object can be used as as an asynchronous context manager, in which case the
  cursor will be closed when control leaves the block via the ``__aexit__`` method.

  A cursor can be used as as an asynchronous iterator.  In such cases, rows are fetched
  :attr:`arraysize` rows at a time.

  The following methods are asyncronous versions of the underlying sqlite3 ``Cursor``
  methods.  The properties, except for :attr:`connection` and :attr:`sqlite3_connection`,
  pass through to the underlying sqlite3 ``Cursor``.  Refer to the Python sqlite3
  documentation for more details.

  .. method:: close()
        :async:

  .. method:: execute(sql, parameters=(), /)
        :async:

  .. method:: executemany(sql, parameters, /)
        :async:

  .. method:: executescript(sql_script, /)
        :async:

  .. method:: fetchall()
        :async:

  .. method:: fetchmany(size=cursor.arraysize)
        :async:

  .. method:: fetchone()
        :async:

  .. property:: arraysize

  .. property:: connection

     Returns an asqlite3 :class:`Connection` object.

  .. property:: sqlite3_connection

     Returns the underlying sqlite3 Connection object.

  .. property:: description

  .. property:: lastrowid

  .. property:: rowcount

  .. property:: row_factory


.. _asqlite3-connection-context-manager:


How to use the connection context manager
=========================================

Just like for the **sqlite3** module, a :class:`Connection` object can be used as a
context manager that automatically commits or rolls back open transactions when leaving
the body of the context manager.  If the body of the ``async with`` statement finishes
without exceptions, the transaction is committed.  If this commit fails, or if the block
body raises an uncaught exception, the transaction is rolled back.  If the underlying
connection's :attr:`autocommit` attribute is ``False``, a new transaction is implicitly
opened after committing or rolling back.

If there is no open transaction upon leaving the body of the ``async with`` statement, or
if :attr:`autocommit` is ``True``, the context manager does nothing.

For example:

  .. code-block::

     async with connect(filename) as conn:
          async with conn:
              # Start transaction 1
              await conn.execute('CREATE TABLE T(x)')
              await conn.executemany('INSERT INTO T VALUES(?)', ((n, ) for n in range(10)))

          # transaction 1 is now committed

          async with conn:
              # Start transaction 2
              ....

**Note** that the context manager neither implicitly opens a new transaction nor closes
the connection.


Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
