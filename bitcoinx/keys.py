# Copyright (c) 2016-2018, Neil Booth
#
# All rights reserved.
#
# The MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

'''Cryptographic key functions.'''

import secp256k1


__all__ = ('shared_secret', 'secp256k1Error')


class secp256k1Error(Exception):
    pass


# Returns a shared secret in the form of an elliptic curve public key
def shared_secret(our_priv_key, their_pub_key, deterministic_key):
    try:
        our_priv2_key = our_priv_key.tweak_add(deterministic_key)
        their_pub2_key = their_pub_key.tweak_add(deterministic_key)
        return their_pub2_key.tweak_mul(our_priv2_key)
    except Exception as e:
        raise secp256k1Error(*e.args)
