# Copyright (c) 2019-2021, Neil Booth
#
# All rights reserved.
#
# Licensed under the the Open BSV License version 3; see LICENCE for details.
#

'''Miscellaneous functions.'''

__all__ = (
    'be_bytes_to_int', 'le_bytes_to_int',
    'int_to_be_bytes', 'int_to_le_bytes', 'CONTEXT'
)

import os
from functools import partial

from electrumsv_secp256k1 import create_context


CONTEXT = create_context()
package_dir = os.path.dirname(os.path.realpath(__file__))

# bitcoinx uses this.  Permits easy replacement for testing corner cases (tests/utils.py)
urandom = os.urandom

# Converts big-endian bytes to an integer
be_bytes_to_int = partial(int.from_bytes, byteorder='big')
le_bytes_to_int = partial(int.from_bytes, byteorder='little')


def int_to_be_bytes(value, size=None):
    '''Converts an integer to a big-endian sequence of bytes'''
    if size is None:
        size = (value.bit_length() + 7) // 8
    return value.to_bytes(size, 'big')


def int_to_le_bytes(value, size=None):
    '''Converts an integer to a big-endian sequence of bytes'''
    if size is None:
        size = (value.bit_length() + 7) // 8
    return value.to_bytes(size, 'little')


def chunks(items, size):
    '''Break up items, an iterable, into chunks of length size.'''
    for i in range(0, len(items), size):
        yield items[i: i + size]


def data_file_path(*parts):
    '''Return the path to a file in the data/ directory.'''
    return os.path.join(package_dir, "data", *parts)


# Method decorator.  To be used for calculations that will always deliver the same result.
# The method cannot take any arguments and should be accessed as an attribute.
class cachedproperty:

    def __init__(self, f):
        self.f = f

    def __get__(self, obj, type_):
        obj = obj or type_
        value = self.f(obj)
        setattr(obj, self.f.__name__, value)
        return value
