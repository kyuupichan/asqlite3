from os import urandom
import random

import attr
from coincurve import PrivateKey, PublicKey
import pytest

from bitcoinx.threshold import *


class Participant(object):

    def __init__(self, k, j):
        self.ephemeral_key = PrivateKey()
        self.a0 = urandom(32)
        self.polynomial = Polynomial.random_from_secret(self.a0, k)
        # Index i unused.  j values of 32 bytes each
        self.other_prv_keys = [None] * j
        # Index i unused.  j lists of k values.
        self.other_polynomials = [None] * j
        # Index i unused.  j lists of j values
        self.other_pub_vals = [None] * j

    def set_other_data(self, other_n, prv_poly_value, pub_coeffs,
                       pub_poly_values):
        self.other_prv_keys[other_n] = prv_poly_value
        self.other_polynomials[other_n] = PublicPolynomial(pub_coeffs)
        self.other_pub_vals[other_n] = pub_poly_values

    def calc_share_and_pubkey(self):
        # Calculate our share, and the shared public key
        me_n = self.other_prv_keys.index(None)
        share = PrivateKey(self.polynomial.eval_at(me_n + 1))
        for prv_key in self.other_prv_keys:
            if prv_key is not None:
                share.add(prv_key)
        pubkeys = [poly.a0_G() for poly in self.other_polynomials
                   if poly is not None]
        pubkeys.append(PrivateKey(self.a0).public_key)
        pubkey = PublicKey.combine_keys(pubkeys)
        return share, pubkey


def simulate_threshold(threshold_count, participant_count):
    k = threshold_count
    j = participant_count

    # Participants should confirm their pubkeys are distinct

    # Sorted participants
    participants = sorted([Participant(k, j) for n in range(j)],
                          key = lambda p: p.ephemeral_key.public_key.format())

    # Arbitrarily act as a random participant
    for me_n, me in enumerate(participants):
        for i, p_i in enumerate(participants):
            if  i == me_n:
                continue
            polynomial_i = p_i.polynomial
            # Each other participant sends me their poly value of me,
            # their k coeffs as pubkeys and their j evals as pubkeys
            me.set_other_data(
                i,
                polynomial_i.eval_at(me_n + 1),
                polynomial_i.coeffs_to_pubkeys(),
                polynomial_i.evals_to_pubkeys(j)
            )

        print(f'Checking consistency of data received...')
        for i, polynomial_i in enumerate(me.other_polynomials):
            if i == me_n:
                assert polynomial_i is None
                continue

            # Check pub vals
            for n, expect in enumerate(me.other_pub_vals[i]):
                evaluate = polynomial_i.eval_at(n + 1)
                assert evaluate == expect
                if n == me_n:
                    # Check my prv_val
                    assert evaluate == PrivateKey(
                        me.other_prv_keys[i]).public_key

        print(f'All checks out for {me_n}')

    print('Calculating shares:')
    for me_n, me in enumerate(participants):
        share, pubkey = me.calc_share_and_pubkey()
        print(f'Share #{me_n}: {share.secret} {pubkey.format()}')


#simulate_threshold(2, 4)

def test_interpolate():
    coords = [(x.to_bytes(32, 'big'), PrivateKey.from_int(y))
              for x, y in [(5, 7), (7, 8)]]
    print(interpolate(coords).to_int())
