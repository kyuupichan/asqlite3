from os import urandom

from coincurve import PrivateKey
import pytest

from bitcoinx.hashes import sha256
from bitcoinx.keys import *

order = int('0xFFFFFFFF_FFFFFFFF_FFFFFFFF_FFFFFFFE_'
            'BAAEDCE6_AF48A03B_BFD25E8C_D0364141', 16)


def test_shared_secret():
    privkeys = [PrivateKey() for n in range(2)]
    pubkeys = [privkey.public_key for privkey in privkeys]

    message = urandom(12)
    det_key = sha256(message)
    ss1 = shared_secret(privkeys[0], pubkeys[1], det_key)
    ss2 = shared_secret(privkeys[1], pubkeys[0], det_key)
    assert ss1 == ss2


def test_shared_secret_bad():
    one = (1).to_bytes(32, 'big')
    two = (2).to_bytes(32, 'big')
    minus_one = (order - 1).to_bytes(32, 'big')

    one_privkey = PrivateKey(one)
    two_privkey = PrivateKey(two)

    shared_secret(one_privkey, one_privkey.public_key, one)
    # Fails in privkey.add
    with pytest.raises(ValueError):
        shared_secret(one_privkey, two_privkey.public_key, minus_one)

    # Fails in pubkey.add
    with pytest.raises(ValueError):
        shared_secret(two_privkey, one_privkey.public_key, minus_one)
