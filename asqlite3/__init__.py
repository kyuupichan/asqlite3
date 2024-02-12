from sqlite3 import (
    Row, PrepareProtocol,
    complete_statement, enable_callback_tracebacks, register_adapter, register_converter,
    Warning, Error, InterfaceError, DatabaseError, DataError, OperationalError,
    IntegrityError, InternalError, ProgrammingError, NotSupportedError,
    PARSE_COLNAMES, PARSE_DECLTYPES, SQLITE_OK, SQLITE_DENY,
    SQLITE_IGNORE, apilevel, paramstyle, sqlite_version, sqlite_version_info, threadsafety,
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
