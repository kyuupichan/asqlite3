import pytest

from bitcoinx import CURVE_ORDER, PrivateKey
from bitcoinx.threshold import *


class TestPolynomial:

    def test_constructor(self):
        Polynomial([1, 1])
        Polynomial([1, CURVE_ORDER - 1])
        with pytest.raises(ValueError):
            Polynomial([])
        with pytest.raises(ValueError):
            Polynomial([1, 0])
        with pytest.raises(ValueError):
            Polynomial([-1, 1])
        with pytest.raises(ValueError):
            Polynomial([1, CURVE_ORDER])
        with pytest.raises(TypeError):
            Polynomial([1, PrivateKey.from_random()])

    @pytest.mark.parametrize("coeffs,threshold", (
        ([1,2], 1),
        (list(range(1, 11)), 9),
        ([1], 0),
    ))
    def test_threshold(self, coeffs, threshold):
        assert Polynomial(coeffs).threshold() == threshold

    def test_from_secret_and_threshold(self):
        p = Polynomial.from_secret_and_threshold(42, 8)
        assert p.threshold() == 8
        assert p.coeffs[0] == 42

    @pytest.mark.parametrize("coeffs,h,value", (
        ([1, 2, 3, 4, 5], 5, 3711),
        ([2, 1], CURVE_ORDER - 1, 1),
        ([CURVE_ORDER - 1, 5], 10, 49),
        ([4], 10, 4),
        ([4], 12, 4),
        # Test that a middle-point evaluation at 0 is OK.  This tests both term-by-term
        # evaluation and factored evaluation
        ([1, 1, 1], CURVE_ORDER - 1, 1),
    ))
    def test_eval_at(self, coeffs, h, value):
        assert Polynomial(coeffs).eval_at(h) == value

    def test_eval_at_bad(self):
        with pytest.raises(TypeError):
            Polynomial([1]).eval_at(1.0)
        with pytest.raises(ValueError):
            Polynomial([1]).eval_at(0)
        with pytest.raises(ValueError):
            Polynomial([2, 1]).eval_at(CURVE_ORDER)
        with pytest.raises(ValueError):
            Polynomial([1, 1]).eval_at(CURVE_ORDER - 1)

    def test_coeffs_to_pubkeys(self):
        coeffs = [1, 6, 3]
        pubkeys = [PrivateKey.from_int(coeff).public_key for coeff in coeffs]
        assert Polynomial(coeffs).coeffs_to_pubkeys() == pubkeys


class TestPublicKeyPolynomial:

    def test_contructor(self):
        PublicKeyPolynomial([PrivateKey.from_random().public_key])
        PublicKeyPolynomial([PrivateKey.from_int(x).public_key for x in (1, CURVE_ORDER - 1)])
        with pytest.raises(ValueError):
            PublicKeyPolynomial([])
        with pytest.raises(TypeError):
            PublicKeyPolynomial([1, PrivateKey.from_random().public_key])

    def test_a0_G(self):
        P = PrivateKey.from_random().public_key
        Q = PrivateKey.from_random().public_key
        assert PublicKeyPolynomial([P, Q]).a0_G() == P

    @pytest.mark.parametrize("coeffs,h,value", (
        ([1, 2, 3, 4, 5], 5, 3711),
        ([2, 1], CURVE_ORDER - 1, 1),
        ([CURVE_ORDER - 1, 5], 10, 49),
        ([4], 10, 4),
        ([4], 12, 4),
        # Test that a middle-point evaluation at 0 is OK.  This tests both term-by-term
        # evaluation and factored evaluation
        ([1, 1, 1], CURVE_ORDER - 1, 1),
    ))
    def test_eval_at(self, coeffs, h, value):
        public_keys = [PrivateKey.from_int(coeff).public_key for coeff in coeffs]
        value = PrivateKey.from_int(value).public_key
        assert PublicKeyPolynomial(public_keys).eval_at(h) == value
