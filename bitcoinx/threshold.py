# Copyright (c) 2019, Neil Booth
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

'''Threshold signatures.'''

__all__ = ('Polynomial', 'PublicKeyPolynomial')


from .keys import PrivateKey, PublicKey, CURVE_ORDER
from .misc import int_to_be_bytes


# Each participant has a group identity public key, known by all participants
# That gives each participant an index from 1 to j, threshold of k <= j


class Polynomial:
    '''A polynomial a0 + a1.x + ... + an.x^n.'''

    def __init__(self, coeffs):
        '''Create a polynomial from coefficients a0 ... an.

        n >= 1 is the threshold.
        '''
        if not all(isinstance(coeff, int) for coeff in coeffs):
            raise TypeError('polynomial coefficients must be integers')
        if not coeffs:
            raise ValueError('at least one coefficient is required')
        if not all(0 < coeff < CURVE_ORDER for coeff in coeffs):
            raise ValueError('polynomial coefficients out of range')
        self.coeffs = coeffs

    def threshold(self):
        return len(self.coeffs) - 1

    @classmethod
    def from_secret_and_threshold(cls, secret, threshold):
        coeffs = [secret]
        coeffs.extend(PrivateKey.from_random().to_int() for n in range(threshold))
        return cls(coeffs)

    def eval_at(self, h):
        '''Evaluate the polynomial at x=h, an integer.

        Raises ValueError in an intermediate result is zero.

        Done for each other participant's index h, except our own.'''
        if not isinstance(h, int):
            raise TypeError('h must be an integer')
        if not 0 < h < CURVE_ORDER:
            raise ValueError('h is out of range')
        coeffs = reversed(self.coeffs)
        result = next(coeffs)
        for coeff in coeffs:
            result = ((h * result) + coeff) % CURVE_ORDER
        if result == 0:
            raise ValueError('polynomial evaluates to zero')
        return result

    def coeffs_to_pubkeys(self):
        # returns [anG, ..., a0G]
        return [PrivateKey.from_int(coeff).public_key for coeff in self.coeffs]


class PublicKeyPolynomial:

    def __init__(self, coeffs):
        '''Create a polynomial from public key coefficients a0G ... anG.

        n >= 1 is the threshold.
        '''
        if not all(isinstance(coeff, PublicKey) for coeff in coeffs):
            raise TypeError('polynomial coefficients must be public keys')
        if not coeffs:
            raise ValueError('at least one public key is required')
        self.coeffs = coeffs

    def a0_G(self):
        return self.coeffs[0]

    def eval_at(self, h):
        # Evaluate the polynomial at x=h, returns 32 bytes
        # Done for each other participant's index except our own
        if not isinstance(h, int):
            raise TypeError('h must be an integer')
        if not 0 < h < CURVE_ORDER:
            raise ValueError('h is out of range')
        h = int_to_be_bytes(h, 32)
        coeffs = reversed(self.coeffs)
        result = next(coeffs)
        for coeff in coeffs:
            result = result.multiply(h).add(coeff)
        return result


# def reciprocal(a):
#     b = GROUP_ORDER_INT
#     x, last_x = 0, 1
#     while b:
#         quot, rem = divmod(a, b)
#         a, b = b, rem
#         x, last_x = last_x - quot * x, x
#     if last_x > 0:
#         return last_x
#     else:
#         return last_x + GROUP_ORDER_INT


# def interpolate(coords):
#     '''Interpolate a list of (32-bytes, Key) coordinates definiing a
#     polynomial to return the intersection point on the y-axis.
#     '''
#     result = None
#     for x, y in coords:
#         minus_x = ((GROUP_ORDER_INT - int.from_bytes(x, 'big'))
#                    .to_bytes(32, 'big'))
#         den_prod = PrivateKey(x)
#         for a, b in coords:
#             if a != x:
#                 den_prod.multiply(a.add(minus_x), True)
#         term = y.multiply(reciprocal(den_prod.to_int()).to_bytes(32, 'big'))
#         if result is None:
#             result = term
#             product = PrivateKey(x)
#         else:
#             result.add(term)
#             product.multiply(x, True)
#     result.multiply(product, True)
#     return result
