from sqlite3 import ProgrammingError

_version_str = '0.9'
_version = tuple(int(part) for part in _version_str.split('.'))


from .asqlite3 import Cursor, Connection, connect
