# Copyright (c) 2024 Neil Booth
#
# All rights reserved.
#
# See the file "LICENCE" for information about the copyright
# and warranty status of this software.

from sqlite3 import (
    Row, PrepareProtocol,
    complete_statement, enable_callback_tracebacks, register_adapter, register_converter,
    Warning, Error, InterfaceError, DatabaseError, DataError, OperationalError,
    IntegrityError, InternalError, ProgrammingError, NotSupportedError,
    PARSE_COLNAMES, PARSE_DECLTYPES, SQLITE_OK, SQLITE_DENY,
    SQLITE_IGNORE, apilevel, paramstyle, sqlite_version, sqlite_version_info, threadsafety,
    SQLITE_CREATE_INDEX, SQLITE_CREATE_TABLE, SQLITE_CREATE_TEMP_INDEX, SQLITE_CREATE_TEMP_TABLE,
    SQLITE_CREATE_TEMP_TRIGGER, SQLITE_CREATE_TEMP_VIEW, SQLITE_CREATE_TRIGGER,
    SQLITE_CREATE_VIEW, SQLITE_DELETE, SQLITE_DROP_INDEX, SQLITE_DROP_TABLE,
    SQLITE_DROP_TEMP_INDEX, SQLITE_DROP_TEMP_TABLE, SQLITE_DROP_TEMP_TRIGGER,
    SQLITE_DROP_TEMP_VIEW, SQLITE_DROP_TRIGGER, SQLITE_DROP_VIEW, SQLITE_INSERT, SQLITE_PRAGMA,
    SQLITE_READ, SQLITE_SELECT, SQLITE_TRANSACTION, SQLITE_UPDATE, SQLITE_ATTACH, SQLITE_DETACH,
    SQLITE_ALTER_TABLE, SQLITE_REINDEX, SQLITE_ANALYZE, SQLITE_CREATE_VTABLE, SQLITE_DROP_VTABLE,
    SQLITE_FUNCTION, SQLITE_SAVEPOINT, SQLITE_RECURSIVE,
)

from sys import version_info as _sys_version_info

if _sys_version_info >= (3, 11):
    from sqlite3 import (
        Blob, SQLITE_LIMIT_LENGTH, SQLITE_LIMIT_SQL_LENGTH, SQLITE_LIMIT_COLUMN,
        SQLITE_LIMIT_EXPR_DEPTH, SQLITE_LIMIT_COMPOUND_SELECT, SQLITE_LIMIT_VDBE_OP,
        SQLITE_LIMIT_FUNCTION_ARG, SQLITE_LIMIT_ATTACHED, SQLITE_LIMIT_LIKE_PATTERN_LENGTH,
        SQLITE_LIMIT_VARIABLE_NUMBER, SQLITE_LIMIT_TRIGGER_DEPTH, SQLITE_LIMIT_WORKER_THREADS
    )


def __getattr__(name):
    '''Handles deprecated names and conditionally defined names such as SQLITE_DBCONFIG_xxx.'''
    import sqlite3

    return getattr(sqlite3, name)


from .asqlite3 import (
    Cursor, Connection, connect,
)

asqlite3_version_str = '0.7'
asqlite3_version = tuple(int(part) for part in asqlite3_version_str.split('.'))
