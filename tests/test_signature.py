import pytest

from bitcoinx import pack_byte, be_bytes_to_int, Script
from bitcoinx.signature import *
from bitcoinx.signature import MISSING_SIG_BYTES


def test_exceptions():
    assert issubclass(InvalidSignatureError, ValueError)


# List of (der_sig, compact_sig)
serialization_testcases = [
    (bytes.fromhex('30450221008dc02fa531a9a704f5c01abdeb58930514651565b42abf94f6ad1565d0ad'
                   '6785022027b1396f772c696629a4a09b01aed2416861aeaee05d0ff4a2e6fdfde73ec84d'),
     bytes.fromhex('8dc02fa531a9a704f5c01abdeb58930514651565b42abf94f6ad1565d0ad6785'
                   '27b1396f772c696629a4a09b01aed2416861aeaee05d0ff4a2e6fdfde73ec84d')),
]


@pytest.mark.parametrize("der_sig,compact_sig", serialization_testcases)
def test_der_signature_to_compact(der_sig, compact_sig):
    assert der_signature_to_compact(der_sig) == compact_sig


@pytest.mark.parametrize("der_sig,compact_sig", serialization_testcases)
def test_compact_signature_to_der(der_sig, compact_sig):
    assert compact_signature_to_der(compact_sig) == der_sig


def test_compact_signature_to_der_bad():
    with pytest.raises(InvalidSignatureError):
        compact_signature_to_der(bytes(63))
    with pytest.raises(InvalidSignatureError):
        compact_signature_to_der('a' * 64)


class TestSigHash:

    def test_sighashes(self):
        assert SigHash.ALL == 0x01
        assert SigHash.NONE == 0x02
        assert SigHash.SINGLE == 0x03
        assert SigHash.FORKID == 0x40
        assert SigHash.ANYONE_CAN_PAY == 0x80

    @pytest.mark.parametrize("n", range(256))
    def test_attributes(self, n):
        s = SigHash(n)
        assert s.base == (n & 0x1f)
        assert isinstance(s.base, SigHash)
        assert s.anyone_can_pay is (n >= 128)

    @pytest.mark.parametrize("n, text", (
        (0, ""),
        (1, "ALL"),
        (2, "NONE"),
        (3, "SINGLE"),
        (0x40, "FORKID"),
        (0x41, "ALL|FORKID"),
        (0x42, "NONE|FORKID"),
        (0x43, "SINGLE|FORKID"),
        (0x80, "ANYONE_CAN_PAY"),
        (0x81, "ALL|ANYONE_CAN_PAY"),
        (0x82, "NONE|ANYONE_CAN_PAY"),
        (0x83, "SINGLE|ANYONE_CAN_PAY"),
    ))
    def test_to_string(self, n, text):
        assert SigHash(n).to_string() == text


class TestSignature:

    def test_constructor(self):
        s = Signature(MISSING_SIG_BYTES)
        assert not s.is_present()
        s = Signature(serialization_testcases[0][0] + pack_byte(0x41))
        assert s.is_present()

    def test_constructor_bad(self):
        with pytest.raises(InvalidSignatureError):
            Signature(b'\x30')

    def test_eq(self):
        assert Signature(MISSING_SIG_BYTES) == MISSING_SIG_BYTES
        assert Signature(MISSING_SIG_BYTES) == Script(MISSING_SIG_BYTES)
        assert Signature(MISSING_SIG_BYTES) == Signature(MISSING_SIG_BYTES)
        assert Signature(MISSING_SIG_BYTES) == bytearray(MISSING_SIG_BYTES)
        assert Signature(MISSING_SIG_BYTES) == memoryview(MISSING_SIG_BYTES)
        assert Signature(MISSING_SIG_BYTES) != 2.5

    def test_hashable(self):
        {Signature(MISSING_SIG_BYTES)}

    def test_hex(self):
        s = Signature.from_hex('ff')
        assert s.to_hex() == 'ff'

    def test_from_der_sig(self):
        der_sig = serialization_testcases[0][0]
        s = Signature.from_der_sig(der_sig, SigHash.ALL | SigHash.FORKID)
        assert s.der_signature == der_sig
        assert s.sighash == SigHash.ALL | SigHash.FORKID

    def test_MISSING(self):
        s = Signature.MISSING
        assert bytes(s) == MISSING_SIG_BYTES
        assert not s.is_present()

    def test_bytes(self):
        der_sig = serialization_testcases[0][0]
        raw = der_sig + pack_byte(SigHash.ALL | SigHash.FORKID)
        s = Signature(raw)
        assert bytes(s) == raw
        assert s.to_bytes() == raw

    @pytest.mark.parametrize("der_sig,compact_sig", serialization_testcases)
    def test_to_compact(self, der_sig, compact_sig):
        s = Signature(der_sig + pack_byte(SigHash.ALL))
        assert s.to_compact() == compact_sig

    @pytest.mark.parametrize("der_sig,compact_sig", serialization_testcases)
    def test_r_value(self, der_sig, compact_sig):
        s = Signature(der_sig + pack_byte(SigHash.ALL))
        assert s.r_value() == be_bytes_to_int(compact_sig[:32])

    @pytest.mark.parametrize("der_sig,compact_sig", serialization_testcases)
    def test_s_value(self, der_sig, compact_sig):
        s = Signature(der_sig + pack_byte(SigHash.ALL))
        assert s.s_value() == be_bytes_to_int(compact_sig[32:])

    def test_der_signature(self):
        s = Signature(MISSING_SIG_BYTES)
        with pytest.raises(InvalidSignatureError):
            s.der_signature
        der_sig = serialization_testcases[0][0]
        s = Signature(der_sig + pack_byte(0x41))
        assert s.der_signature == der_sig

    @pytest.mark.parametrize("sighash", (0, 1, 2, 3, 42, 189))
    def test_sighash(self, sighash):
        der_sig = serialization_testcases[0][0]
        s = Signature(der_sig + pack_byte(sighash))
        assert s.sighash == sighash

    def test_sighash_bad(self):
        s = Signature(MISSING_SIG_BYTES)
        with pytest.raises(InvalidSignatureError):
            s.sighash

    @pytest.mark.parametrize("sig, text", (
        ('304402207f5ba050adff0567df3dcdc70d5059c4b8b8d2afc961d7545778a79cd125f0b8022013b3e5a'
         '87f3fa84333f222dc32c2c75e630efb205a3c58010aab92ab4254531041',
         '304402207f5ba050adff0567df3dcdc70d5059c4b8b8d2afc961d7545778a79cd125f0b8022013b3e5a'
         '87f3fa84333f222dc32c2c75e630efb205a3c58010aab92ab42545310[ALL|FORKID]'),
    ))
    def test_to_string(self, sig, text):
        assert Signature.from_hex(sig).to_string() == text
