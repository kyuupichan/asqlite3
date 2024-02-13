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

from sys import version_info as _sys_version_info

if _sys_version_info >= (3, 11):
    from sqlite3 import (
        Blob, SQLITE_LIMIT_LENGTH, SQLITE_LIMIT_SQL_LENGTH, SQLITE_LIMIT_COLUMN,
        SQLITE_LIMIT_EXPR_DEPTH, SQLITE_LIMIT_COMPOUND_SELECT, SQLITE_LIMIT_VDBE_OP,
        SQLITE_LIMIT_FUNCTION_ARG, SQLITE_LIMIT_ATTACHED, SQLITE_LIMIT_LIKE_PATTERN_LENGTH,
        SQLITE_LIMIT_VARIABLE_NUMBER, SQLITE_LIMIT_TRIGGER_DEPTH, SQLITE_LIMIT_WORKER_THREADS
    )

if _sys_version_info >= (3, 12):
    from sqlite3 import (
        LEGACY_TRANSACTION_CONTROL, SQLITE_DBCONFIG_DEFENSIVE, SQLITE_DBCONFIG_DQS_DDL,
        SQLITE_DBCONFIG_DQS_DML, SQLITE_DBCONFIG_ENABLE_FKEY,
        SQLITE_DBCONFIG_ENABLE_FTS3_TOKENIZER, SQLITE_DBCONFIG_ENABLE_LOAD_EXTENSION,
        SQLITE_DBCONFIG_ENABLE_QPSG, SQLITE_DBCONFIG_ENABLE_TRIGGER, SQLITE_DBCONFIG_ENABLE_VIEW,
        SQLITE_DBCONFIG_LEGACY_ALTER_TABLE, SQLITE_DBCONFIG_LEGACY_FILE_FORMAT,
        SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE, SQLITE_DBCONFIG_RESET_DATABASE,
        SQLITE_DBCONFIG_TRIGGER_EQP, SQLITE_DBCONFIG_TRUSTED_SCHEMA,
        SQLITE_DBCONFIG_WRITABLE_SCHEMA
    )

_deprecated_names = {
    'version': ((3, 12), (3, 14)),
    'version_info': ((3, 12), (3, 14)),
}


def __getattr__(name):
    versions = _deprecated_names.get(name)
    if versions:
        import sqlite3
        first, last = versions
        if first <= _sys_version_info < last:
            return getattr(sqlite3, name)

    raise AttributeError(f'module asqlite3 has no attribte {name}')


if _sys_version_info < (3, 12):
    from sqlite3 import (
        version, version_info
    )

from .asqlite3 import (
    Cursor, Connection, connect,
)

_version_str = '0.1'
_version = tuple(int(part) for part in _version_str.split('.'))
