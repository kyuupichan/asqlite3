from sqlite3 import (
    Row, PrepareProtocol,
    complete_statement, enable_callback_tracebacks, register_adapter, register_converter,
    Warning, Error, InterfaceError, DatabaseError, DataError, OperationalError,
    IntegrityError, InternalError, ProgrammingError, NotSupportedError,
    PARSE_COLNAMES, PARSE_DECLTYPES, SQLITE_OK, SQLITE_DENY,
    SQLITE_IGNORE, apilevel, paramstyle, sqlite_version, sqlite_version_info, threadsafety,
    SQLITE_CREATE_INDEX, SQLITE_CREATE_TABLE, SQLITE_CREATE_TEMP_INDEX, SQLITE_CREATE_TEMP_TABLE,
    SQLITE_CREATE_TEMP_VIEW, SQLITE_CREATE_TRIGGER, SQLITE_CREATE_VIEW, SQLITE_DELETE,
    SQLITE_DROP_INDEX, SQLITE_DROP_TABLE, SQLITE_DROP_TABLE, SQLITE_DROP_TEMP_INDEX,
    SQLITE_DROP_TEMP_TABLE, SQLITE_DROP_TEMP_TRIGGER, SQLITE_DROP_TEMP_VIEW, SQLITE_DROP_TRIGGER,
    SQLITE_DROP_TEMP_VIEW, SQLITE_DROP_TRIGGER, SQLITE_DROP_VIEW, SQLITE_INSERT, SQLITE_PRAGMA,
    SQLITE_READ, SQLITE_SELECT, SQLITE_TRANSACTION, SQLITE_UPDATE, SQLITE_ATTACH, SQLITE_DETACH,
    SQLITE_ALTER_TABLE, SQLITE_REINDEX, SQLITE_ANALYZE, SQLITE_CREATE_VTABLE, SQLITE_DROP_VTABLE,
    SQLITE_FUNCTION, SQLITE_SAVEPOINT, SQLITE_RECURSIVE,
)

import sys

if sys.version_info >= (3, 11):
    from sqlite3 import (
        Blob,
    )

if sys.version_info >= (3, 12):
    from sqlite3 import (
        LEGACY_TRANSACTION_CONTROL
    )

if sys.version_info < (3, 14):
    from sqlite3 import (
        version, version_info
    )

del sys

from .asqlite3 import (
    Cursor, Connection, connect,
)

_version_str = '0.1'
_version = tuple(int(part) for part in _version_str.split('.'))
