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

from os import urandom
from coincurve import PrivateKey, PublicKey
from coincurve.utils import GROUP_ORDER_INT


__all__ = ('ThresholdError', 'Polynomial', 'PublicPolynomial',
           'interpolate')


class ThresholdError(Exception):
    pass


# Each participant has a group identity public key, known by all participants
# That gives each participant an index from 1 to j, threshold of k <= j


class Polynomial(object):

    def __init__(self, coeffs):
        # a(k - 1) ... a(0); reversed order.  Size of the threshold.
        self.coeffs = coeffs

    @classmethod
    def random_from_secret(cls, a0, k):
        assert k >= 1
        coeffs = [urandom(32) for n in range(k - 1)]
        coeffs.append(a0)
        return cls(coeffs)

    def eval_at(self, h):
        # Evaluate the polynomial at x=h, returns 32 bytes
        # Done for each other participant's index except our own
        coeffs = iter(self.coeffs)
        result = next(coeffs)
        multiply_by_h = PrivateKey(h.to_bytes(32, 'big')).multiply
        for coeff in coeffs:
            result = multiply_by_h(result)
            result = result.add(coeff)
            result = result.secret
        return result

    def evals_to_pubkeys(self, count):
        # Count is the threshold count required
        eval_at = self.eval_at
        return [PrivateKey(eval_at(n)).public_key for n in range(1, count + 1)]

    def coeffs_to_pubkeys(self):
        # returns [ceoff[k - 1]G, ..., ceoff[0]G]
        return [PrivateKey(coeff).public_key for coeff in self.coeffs]


class PublicPolynomial(object):

    def __init__(self, coeffs):
        self.coeffs = coeffs

    def a0_G(self):
        return self.coeffs[-1]

    def eval_at(self, h):
        # Evaluate the polynomial at x=h, returns 32 bytes
        # Done for each other participant's index except our own
        h = h.to_bytes(32, 'big')
        coeffs = iter(self.coeffs)
        result = next(coeffs)
        for coeff in coeffs:
            result = PublicKey.combine_keys([result.multiply(h), coeff])
        return result


def reciprocal(a):
    b = GROUP_ORDER_INT
    x, last_x = 0, 1
    while b:
        quot, rem = divmod(a, b)
        a, b = b, rem
        x, last_x = last_x - quot * x, x
    if last_x > 0:
        return last_x
    else:
        return last_x + GROUP_ORDER_INT


def interpolate(coords):
    '''Interpolate a list of (32-bytes, Key) coordinates definiing a
    polynomial to return the intersection point on the y-axis.
    '''
    result = None
    for x, y in coords:
        minus_x = ((GROUP_ORDER_INT - int.from_bytes(x, 'big'))
                   .to_bytes(32, 'big'))
        den_prod = PrivateKey(x)
        for a, b in coords:
            if a != x:
                den_prod.multiply(a.add(minus_x), True)
        term = y.multiply(reciprocal(den_prod.to_int()).to_bytes(32, 'big'))
        if result is None:
            result = term
            product = PrivateKey(x)
        else:
            result.add(term)
            product.multiply(x, True)
    result.multiply(product, True)
    return result
