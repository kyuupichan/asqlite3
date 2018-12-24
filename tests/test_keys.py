from os import urandom

import secp256k1
import pytest

from bitcoinx.hashes import sha256
from bitcoinx.keys import *

order = int('0xFFFFFFFF_FFFFFFFF_FFFFFFFF_FFFFFFFE_'
            'BAAEDCE6_AF48A03B_BFD25E8C_D0364141', 16)


def test_shared_secret():
    privkeys = [secp256k1.PrivateKey(urandom(32)) for n in range(2)]
    pubkeys = [privkey.pubkey for privkey in privkeys]

    message = urandom(12)
    det_key = sha256(message)
    ss1 = shared_secret(privkeys[0], pubkeys[1], det_key)
    ss2 = shared_secret(privkeys[1], pubkeys[0], det_key)
    assert ss1.serialize() == ss2.serialize()


def test_shared_secret_bad():
    one = (1).to_bytes(32, 'big')
    two = (2).to_bytes(32, 'big')
    minus_one = (order - 1).to_bytes(32, 'big')

    one_privkey = secp256k1.PrivateKey(one)
    two_privkey = secp256k1.PrivateKey(two)

    shared_secret(one_privkey, one_privkey.pubkey, one)
    # Fails in privkey.add_tweak
    with pytest.raises(secp256k1Error):
        shared_secret(one_privkey, two_privkey.pubkey, minus_one)

    # Fails in pubkey.add_tweak
    with pytest.raises(secp256k1Error):
        shared_secret(two_privkey, one_privkey.pubkey, minus_one)
