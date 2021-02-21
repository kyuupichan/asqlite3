# Copyright (c) 2018-2021, Neil Booth
#
# All rights reserved.
#
# Licensed under the the Open BSV License version 3; see LICENCE for details.
#

'''Bitcoin script interpreter.'''

__all__ = (
    'InterpreterError', 'InterpreterPolicy', 'InterpreterLimits', 'InterpreterState',
    'InterpreterFlags',
)


import operator
from enum import IntEnum
from functools import partial

import attr

from .consts import (
    LOCKTIME_THRESHOLD, SEQUENCE_FINAL, SEQUENCE_LOCKTIME_DISABLE_FLAG,
    SEQUENCE_LOCKTIME_MASK, SEQUENCE_LOCKTIME_TYPE_FLAG, UINT32_MAX, UINT64_MAX, INT32_MAX,
)
from .consts import INT64_MAX
from .errors import (
    InterpreterError, NumEqualVerifyFailed,
    StackSizeTooLarge, MinimalEncodingError, InvalidPublicKeyEncoding,
    ScriptTooLarge, TooManyOps, MinimalIfError, DivisionByZero, NegativeShiftCount,
    InvalidPushSize, DisabledOpcode, UnbalancedConditional, InvalidStackOperation,
    VerifyFailed, OpReturnError, InvalidOpcode, InvalidSplit,
    InvalidNumber, InvalidOperandSize, EqualVerifyFailed, InvalidSignature, NullFailError,
    InvalidPublicKeyCount, NullDummyError, UpgradeableNopError, LockTimeError, PushOnlyError,
    CheckSigVerifyFailed, CheckMultiSigVerifyFailed, InvalidSignatureCount, CleanStackError,
)
from .hashes import ripemd160, hash160, sha1, sha256, double_sha256
from .limited_stack import LimitedStack
# pylint:disable=E0611
from .script import (
    Script, ScriptIterator, Ops, OP_16, OP_IF, OP_ENDIF, OP_RETURN,
    int_to_item, item_to_int, minimal_push_opcode, is_item_minimally_encoded, minimal_encoding,
    cast_to_bool
)
from .signature import Signature, SigHash, SigEncoding


bool_items = [b'', b'\1']


@attr.s(slots=True)
class Condition:
    '''Represents an open condition block whilst executing.'''
    opcode = attr.ib()       # OP_IF or OP_NOTIF
    execute = attr.ib()      # True or False; flips on OP_ELSE
    seen_else = attr.ib()    # True or False


@attr.s(slots=True)
class InterpreterPolicy:
    '''Miner policy rules.

    Generally fixed over the node session and apply to non-consensus post-genesis
    transactions for e.g. mempool acceptance.

    Consensus rules determine what is accepted in a block and are looser.
    '''
    # In bytes, e.g. 10_000_000
    max_script_size = attr.ib()
    # In bytes, e.g. 256
    max_script_num_length = attr.ib()
    # In bytes, e.g. 10_000_000
    max_stack_memory_usage = attr.ib()
    # e.g. 1_000_000
    max_ops_per_script = attr.ib()
    # e.g. 64
    max_pubkeys_per_multisig = attr.ib()


@attr.s(slots=True)
class InterpreterLimits:
    '''Limits to apply to a particular invocation of the interpreter.  Use the from_policy()
    method to initialize appropriately for a given miner policy and context.'''

    # Class constants
    MAX_SCRIPT_SIZE_BEFORE_GENESIS = 10_000
    MAX_SCRIPT_SIZE_AFTER_GENESIS = UINT32_MAX    # limited by P2P message size
    MAX_SCRIPT_NUM_LENGTH_BEFORE_GENESIS = 4
    MAX_SCRIPT_NUM_LENGTH_AFTER_GENESIS = 750_000
    MAX_SCRIPT_ELEMENT_SIZE_BEFORE_GENESIS = 520
    MAX_STACK_ELEMENTS_BEFORE_GENESIS = 1_000
    MAX_STACK_MEMORY_USAGE_AFTER_GENESIS = INT64_MAX
    MAX_OPS_PER_SCRIPT_BEFORE_GENESIS = 500
    MAX_OPS_PER_SCRIPT_AFTER_GENESIS = UINT32_MAX
    MAX_PUBKEYS_PER_MULTISIG_BEFORE_GENESIS = 20
    MAX_PUBKEYS_PER_MULTISIG_AFTER_GENESIS = UINT32_MAX

    # Attributes
    script_size = attr.ib()
    script_num_length = attr.ib()
    stack_memory_usage = attr.ib()
    ops_per_script = attr.ib()
    pubkeys_per_multisig = attr.ib()
    item_size = attr.ib()
    is_utxo_after_genesis = attr.ib()

    @classmethod
    def max_script_size_rule(cls, policy, is_genesis_enabled, is_consensus):
        '''Implements the max script size rule.'''
        if is_genesis_enabled:
            if is_consensus:
                return cls.MAX_SCRIPT_SIZE_AFTER_GENESIS
            return policy.max_script_size
        return cls.MAX_SCRIPT_SIZE_BEFORE_GENESIS

    @classmethod
    def max_script_num_length_rule(cls, policy, is_utxo_after_genesis, is_consensus):
        '''Implements the max script memory usage rule.'''
        if is_utxo_after_genesis:
            if is_consensus:
                return cls.MAX_SCRIPT_NUM_LENGTH_AFTER_GENESIS
            return policy.max_script_num_length
        return cls.MAX_SCRIPT_NUM_LENGTH_BEFORE_GENESIS

    @classmethod
    def max_stack_memory_usage_rule(cls, policy, is_utxo_after_genesis, is_consensus):
        '''Implements the max script memory usage rule.'''
        if is_utxo_after_genesis:
            if is_consensus:
                return cls.MAX_STACK_MEMORY_USAGE_AFTER_GENESIS
            return policy.max_stack_memory_usage
        # Before genesis other stricter limitations applied so this can be infinite
        return INT64_MAX

    @classmethod
    def max_ops_per_script_rule(cls, policy, is_genesis_enabled, is_consensus):
        '''Implements the max script size rule.'''
        if is_genesis_enabled:
            if is_consensus:
                return cls.MAX_OPS_PER_SCRIPT_AFTER_GENESIS
            return policy.max_ops_per_script
        return cls.MAX_OPS_PER_SCRIPT_BEFORE_GENESIS

    @classmethod
    def max_pubkeys_per_multisig_rule(cls, policy, is_utxo_after_genesis, is_consensus):
        '''Implements the rule re maximum public keys in an OP_CHECKMULTISIG[VERIFY].'''
        if is_utxo_after_genesis:
            if is_consensus:
                return cls.MAX_PUBKEYS_PER_MULTISIG_AFTER_GENESIS
            return policy.max_pubkeys_per_multisig
        return cls.MAX_PUBKEYS_PER_MULTISIG_BEFORE_GENESIS

    @classmethod
    def max_item_size_rule(cls, is_utxo_after_genesis):
        # No limit for post-genesis UTXOs
        if is_utxo_after_genesis:
            return UINT64_MAX
        else:
            return cls.MAX_SCRIPT_ELEMENT_SIZE_BEFORE_GENESIS

    @classmethod
    def from_policy(cls, policy, is_genesis_enabled, is_utxo_after_genesis, is_consensus):
        if is_utxo_after_genesis and not is_genesis_enabled:
            raise ValueError('cannot have a UTXO after genesis if genesis is not enabled')
        return cls(
            cls.max_script_size_rule(policy, is_genesis_enabled, is_consensus),
            cls.max_script_num_length_rule(policy, is_utxo_after_genesis, is_consensus),
            cls.max_stack_memory_usage_rule(policy, is_utxo_after_genesis, is_consensus),
            cls.max_ops_per_script_rule(policy, is_genesis_enabled, is_consensus),
            cls.max_pubkeys_per_multisig_rule(policy, is_utxo_after_genesis, is_consensus),
            cls.max_item_size_rule(is_utxo_after_genesis),
            is_utxo_after_genesis,
        )


class InterpreterFlags(IntEnum):
    # Require most compact opcode for pushing stack data, and require minimal-encoding of numbers
    REQUIRE_MINIMAL_PUSH = 1 << 0
    # Top of stack on OP_IF and OP_ENDIF must be boolean.
    REQUIRE_MINIMAL_IF = 1 << 1
    # Enforces strict DER signature encoding
    REQUIRE_STRICT_DER = 1 << 2
    # Enforces low-S signatures
    REQUIRE_LOW_S = 1 << 3
    # Enforces SigHash checks and public key encoding checks
    REQUIRE_STRICT_ENCODING = 1 << 4
    # Fails script immediately if a failed signature was not null
    REQUIRE_NULLFAIL = 1 << 5
    # Fails script if the CHECKMULTISIG dummy argument is not null
    REQUIRE_NULLDUMMY = 1 << 6
    # Fails script if an upgradeable NOP is encountered
    REJECT_UPGRADEABLE_NOPS = 1 << 7
    # Set if FORKID is enabled (post BTC/BCH fork)
    ENABLE_FORKID = 1 << 8
    # If set OP_CHECKLOCKTIMEVERIFY is permitted
    ENABLE_CHECKLOCKTIMEVERIFY = 1 << 9
    # If set OP_CHECKSEQUENCEVERIFY is permitted
    ENABLE_CHECKSEQUENCEVERIFY = 1 << 10
    # If set verify_script handles P2SH outputs
    ENABLE_P2SH = 1 << 11
    # If true verify_script() requires script_sig to be PUSHDATA only
    REQUIRE_PUSH_ONLY = 1 << 12
    # If true verify_script() requires a clean stack on exit
    REQUIRE_CLEANSTACK = 1 << 13

    # New blocks must comply with these flags (but old blocks may not)
    MANDATORY_SCRIPT_VERIFY_FLAGS = (
        REQUIRE_STRICT_ENCODING | REQUIRE_LOW_S | REQUIRE_NULLFAIL | ENABLE_FORKID | ENABLE_P2SH
    )

    # Standard transactions must comply with these flags
    STANDARD_VERIFY_FLAGS = (
        MANDATORY_SCRIPT_VERIFY_FLAGS | REQUIRE_STRICT_DER | REQUIRE_MINIMAL_PUSH
        | REQUIRE_NULLDUMMY | REJECT_UPGRADEABLE_NOPS | REQUIRE_CLEANSTACK
        | ENABLE_CHECKLOCKTIMEVERIFY | ENABLE_CHECKSEQUENCEVERIFY
    )

    @classmethod
    def sanitize(cls, flags, is_utxo_after_genesis):
        '''Return sanitized flags .'''
        # Require strict encoding if FORKID is enabled
        if flags & cls.ENABLE_FORKID:
            flags |= cls.REQUIRE_STRICT_ENCODING

        # Disable CLEANSTACK check unless P2SH is enabled as the P2SH inputs would remain.
        if not (flags & cls.ENABLE_P2SH):
            flags &= ~cls.REQUIRE_CLEANSTACK

        # For post-genesis UTXOs some features are disabled
        if is_utxo_after_genesis:
            flags &= ~(cls.ENABLE_CHECKLOCKTIMEVERIFY | cls.ENABLE_CHECKSEQUENCEVERIFY
                       | cls.ENABLE_P2SH)

        return flags


class InterpreterState:
    '''Things that vary per evaluation, typically because they're a function of the
    transaction input.'''

    def __init__(self, limits, *, flags=0, tx=None, input_index=-1, value=-1):
        self.limits = limits
        self.flags = InterpreterFlags.sanitize(flags, limits.is_utxo_after_genesis)
        self.tx = tx
        self.input_index = input_index
        self.value = value
        self.reset()

    def reset(self):
        # These are updated by the interpreter whilst running
        self.stack = LimitedStack(self.limits.stack_memory_usage)
        self.alt_stack = self.stack.make_child_stack()
        self.conditions = []
        self.execute = False
        self.iterator = None
        self.finished = False
        self.op_count = 0
        self.non_top_level_return_after_genesis = False

    def bump_op_count(self, bump):
        self.op_count += bump
        if self.op_count > self.limits.ops_per_script:
            raise TooManyOps(f'op count exceeds the limit of {self.limits.ops_per_script:,d}')

    def require_stack_depth(self, depth):
        if len(self.stack) < depth:
            raise InvalidStackOperation(f'stack depth {len(self.stack)} less than required '
                                        f'depth of {depth}')

    def require_alt_stack(self):
        if not self.alt_stack:
            raise InvalidStackOperation('alt stack is empty')

    def validate_item_size(self, size):
        '''Enforces the limit on stack item size.'''
        if size > self.limits.item_size:
            raise InvalidPushSize(f'item length {size:,d} exceeds the limit '
                                  f'of {self.limits.item_size:,d} bytes')

    def validate_minimal_push_opcode(self, op, item):
        if self.flags & InterpreterFlags.REQUIRE_MINIMAL_PUSH:
            expected_op = minimal_push_opcode(item)
            if op != expected_op:
                raise MinimalEncodingError(f'item not pushed with minimal opcode {expected_op}')

    def validate_stack_size(self):
        '''Enforces the limits on combined stack size.

        For post-genesis UTXOs the limit is instead on stack memory usage.
        '''
        if self.limits.is_utxo_after_genesis:
            return
        stack_size = len(self.stack) + len(self.alt_stack)
        limit = InterpreterLimits.MAX_STACK_ELEMENTS_BEFORE_GENESIS
        if stack_size > limit:
            raise StackSizeTooLarge(f'combined stack size exceeds the limit of {limit:,d} items')

    def validate_number_length(self, size, *, limit=None):
        if limit is None:
            limit = self.limits.script_num_length
        if size > limit:
            raise InvalidNumber(f'number of length {size:,d} bytes exceeds the limit '
                                f'of {limit:,d} bytes')

    def to_number(self, item, *, length_limit=None):
        self.validate_number_length(len(item), limit=length_limit)

        if (self.flags & InterpreterFlags.REQUIRE_MINIMAL_PUSH
                and not is_item_minimally_encoded(item)):
            raise MinimalEncodingError(f'number is not minimally encoded: {item.hex()}')

        return item_to_int(item)

    def validate_pubkey_count(self, count):
        limit = self.limits.pubkeys_per_multisig
        if not 0 <= count <= limit:
            raise InvalidPublicKeyCount(f'number of public keys, {count:,d}, in multi-sig check '
                                        f'lies outside range 0 <= count <= {limit:d}')

    def validate_signature(self, sig_bytes):
        '''Raise the InvalidSignature exception if the signature does not meet the requirements of
        self.flags.
        '''
        if not sig_bytes:
            return

        if self.flags & (InterpreterFlags.REQUIRE_STRICT_DER | InterpreterFlags.REQUIRE_LOW_S
                         | InterpreterFlags.REQUIRE_STRICT_ENCODING):
            kind = Signature.analyze_encoding(sig_bytes)
            if not kind & SigEncoding.STRICT_DER:
                raise InvalidSignature('signature does not follow strict DER encoding')

            if self.flags & InterpreterFlags.REQUIRE_LOW_S and not kind & SigEncoding.LOW_S:
                raise InvalidSignature('signature has high S value')

        if self.flags & InterpreterFlags.REQUIRE_STRICT_ENCODING:
            sighash = SigHash.from_sig_bytes(sig_bytes)
            if not sighash.is_defined():
                raise InvalidSignature('undefined sighash type')
            if sighash.has_forkid() and not (self.flags & InterpreterFlags.ENABLE_FORKID):
                raise InvalidSignature('sighash must not use FORKID')
            if not sighash.has_forkid() and (self.flags & InterpreterFlags.ENABLE_FORKID):
                raise InvalidSignature('sighash must use FORKID')

    def validate_pubkey(self, pubkey_bytes):
        '''Raise the InvalidPublicKeyEncoding exception if the public key is not a standard
        compressed or uncompressed encoding and REQUIRE_STRICT_ENCODING is flagged.'''
        if self.flags & InterpreterFlags.REQUIRE_STRICT_ENCODING:
            length = len(pubkey_bytes)
            if length == 33 and pubkey_bytes[0] in {2, 3}:
                return
            if length == 65 and pubkey_bytes[0] == 4:
                return
            raise InvalidPublicKeyEncoding('invalid public key encoding')

    def validate_nullfail(self, sig_bytes):
        '''Fail immediately if a failed signature was not null.'''
        if self.flags & InterpreterFlags.REQUIRE_NULLFAIL and sig_bytes:
            raise NullFailError('signature check failed on a non-null signature')

    def validate_nulldummy(self):
        '''Fail if the multisig duumy pop isn't an empty stack item.'''
        if self.flags & InterpreterFlags.REQUIRE_NULLDUMMY and self.stack[-1]:
            raise NullDummyError('multisig dummy argument was not null')

    def cleanup_script_code(self, sig_bytes, script_code):
        '''Return script_code with signatures deleted if pre-BCH fork.'''
        sighash = SigHash.from_sig_bytes(sig_bytes)
        if self.flags & InterpreterFlags.ENABLE_FORKID or sighash.has_forkid():
            return script_code
        else:
            return script_code.find_and_delete(Script() << sig_bytes)

    def check_sig(self, sig_bytes, pubkey_bytes, script_code):
        '''Check a signature.  Returns True or False.'''
        if not sig_bytes or not self.tx:
            return False
        from .keys import PublicKey
        try:
            pubkey = PublicKey.from_bytes(pubkey_bytes)
        except ValueError:
            return False

        # Split out to a normalized DER signature and the sighash
        der_sig, sighash = Signature.split_and_normalize(sig_bytes)
        message_hash = self.tx.signature_hash(self.input_index, self.value, script_code, sighash)

        return pubkey.verify_der_signature(der_sig, message_hash, hasher=None)

    def validate_locktime(self, locktime):
        # Are the lock times comparable?
        if (locktime < LOCKTIME_THRESHOLD) ^ (self.tx.locktime < LOCKTIME_THRESHOLD):
            raise LockTimeError('locktimes are not comparable')
        # Numeric comparison
        if locktime > self.tx.locktime:
            raise LockTimeError(f'locktime {locktime:,d} not reached')
        if self.tx.inputs[self.input_index].sequence == SEQUENCE_FINAL:
            raise LockTimeError('transaction input is final')

    def validate_sequence(self, sequence):
        # If this flag is set it behaves as a NOP
        if sequence & SEQUENCE_LOCKTIME_DISABLE_FLAG:
            return
        # Is BIP68 triggered?
        if 0 <= self.tx.version < 2:
            raise LockTimeError('transaction version is under 2')
        txin_seq = self.tx.inputs[self.input_index].sequence
        if txin_seq & SEQUENCE_LOCKTIME_DISABLE_FLAG:
            raise LockTimeError('transaction index sequence is disabled')
        mask = SEQUENCE_LOCKTIME_TYPE_FLAG | SEQUENCE_LOCKTIME_MASK
        sequence &= mask
        txin_seq &= mask
        if (sequence < SEQUENCE_LOCKTIME_TYPE_FLAG) ^ (txin_seq < SEQUENCE_LOCKTIME_TYPE_FLAG):
            raise LockTimeError('sequences are not comparable')
        if sequence > txin_seq:
            raise LockTimeError(f'masked sequence number {sequence:,d} not reached')

    def handle_upgradeable_nop(self, op):
        '''Raise on upgradeable nops if the flag is set.'''
        if self.flags & InterpreterFlags.REJECT_UPGRADEABLE_NOPS:
            raise UpgradeableNopError(f'encountered upgradeable NOP {op.name}')

    def evaluate_script(self, script):
        '''Evaluate a script and update state.'''
        if len(script) > self.limits.script_size:
            raise ScriptTooLarge(f'script length {len(script):,d} exceeds the limit of '
                                 f'{self.limits.script_size:,d} bytes')

        # pylint:disable=W0201
        self.op_count = 0
        self.non_top_level_return_after_genesis = False
        self.iterator = ScriptIterator(script)

        for op, item in self.iterator.ops_and_items():
            # Check pushitem size first
            if item is not None:
                self.validate_item_size(len(item))

            self.execute = (all(condition.execute for condition in self.conditions)
                            and (not self.non_top_level_return_after_genesis or op == OP_RETURN))

            # Pushitem and OP_RESERVED do not count towards op count.
            if op > OP_16:
                self.bump_op_count(1)

            # Some op codes are disabled.  For pre-genesis UTXOs these were an error in
            # unevaluated branches; for post-genesis UTXOs only if evaluated.
            if op in {Ops.OP_2MUL, Ops.OP_2DIV} and (self.execute or
                                                     not self.limits.is_utxo_after_genesis):
                raise DisabledOpcode(f'{Ops(op).name} is disabled')

            if self.execute and item is not None:
                self.validate_minimal_push_opcode(op, item)
                self.stack.append(item)
            elif self.execute or OP_IF <= op <= OP_ENDIF:
                op_handlers[op](self)
                if self.finished:
                    return

            self.validate_stack_size()

        if self.conditions:
            raise UnbalancedConditional(f'unterminated {self.conditions[-1].opcode.name} '
                                        'at end of script')

    def verify_script(self, script_sig, script_pubkey):
        '''Return the result of evaluating the scripts.'''
        if self.flags & InterpreterFlags.REQUIRE_PUSH_ONLY and not script_sig.is_push_only():
            raise PushOnlyError('script_sig is not pushdata only')

        is_P2SH = (self.flags & InterpreterFlags.ENABLE_P2SH) and script_pubkey.is_P2SH()

        self.evaluate_script(script_sig)
        if is_P2SH:
            stack_copy = self.stack.make_copy()
        self.evaluate_script(script_pubkey)
        if not self.stack or not cast_to_bool(self.stack[-1]):
            return False

        # Additional validation for P2SH transactions
        if is_P2SH:
            if not script_sig.is_push_only():
                raise PushOnlyError('P2SH script_sig is not pushdata only')
            self.stack.restore_copy(stack_copy)
            pubkey_script = Script(self.stack.pop())
            self.evaluate_script(pubkey_script)
            if not self.stack or not cast_to_bool(self.stack[-1]):
                return False

        if self.flags & InterpreterFlags.REQUIRE_CLEANSTACK and len(self.stack) != 1:
            raise CleanStackError('stack is not clean')

        return True


#
# Control
#
def handle_NOP(_state):
    pass


def handle_IF(state, op):
    execute = False
    if state.execute:
        state.require_stack_depth(1)
        top = state.stack[-1]
        if state.flags & InterpreterFlags.REQUIRE_MINIMAL_IF:
            if state.stack[-1] not in bool_items:
                raise MinimalIfError('top of stack not True or False')
        state.stack.pop()
        execute = cast_to_bool(top)
        if op == Ops.OP_NOTIF:
            execute = not execute
    state.conditions.append(Condition(op, execute, False))


def handle_ELSE(state):
    top_condition = state.conditions[-1] if state.conditions else None
    # Only one ELSE is allowed per condition block after genesis
    if not top_condition or (top_condition.seen_else and state.limits.is_utxo_after_genesis):
        raise UnbalancedConditional('unexpected OP_ELSE')
    top_condition.execute = not top_condition.execute
    top_condition.seen_else = True


def handle_ENDIF(state):
    # Only one ELSE is allowed per condition block after genesis
    if not state.conditions:
        raise UnbalancedConditional('unexpected OP_ENDIF')
    state.conditions.pop()


def handle_VERIF(state, op):
    # Post-genesis UTXOs permit OP_VERIF and OP_NOTVERIF in unexecuted branches
    if state.limits.is_utxo_after_genesis and not state.execute:
        return
    invalid_opcode(state, op)


def handle_VERIFY(state):
    # (true -- ) or (false -- false) and return
    state.require_stack_depth(1)
    if not cast_to_bool(state.stack[-1]):
        raise VerifyFailed()
    state.stack.pop()


def handle_RETURN(state):
    if state.limits.is_utxo_after_genesis:
        if state.conditions:
            # Check for invalid grammar if OP_RETURN in an if statement after genesis
            state.non_top_level_return_after_genesis = True
        else:
            # Terminate execution successfully.  The remainder of the script is ignored
            # even in the presence of unbalanced IFs, invalid opcodes etc.
            state.finished = True
    else:
        raise OpReturnError('OP_RETURN encountered')


def invalid_opcode(_state, op):
    try:
        name = Ops(op).name
    except ValueError:
        name = str(op)

    raise InvalidOpcode(f'invalid opcode {name}')


#
# Stack operations
#
def handle_TOALTSTACK(state):
    state.require_stack_depth(1)
    state.alt_stack.append(state.stack.pop())


def handle_FROMALTSTACK(state):
    state.require_alt_stack()
    state.stack.append(state.alt_stack.pop())


def handle_DROP(state):
    # (x -- )
    state.require_stack_depth(1)
    state.stack.pop()


def handle_2DROP(state):
    # (x1 x2 -- )
    state.require_stack_depth(2)
    state.stack.pop()
    state.stack.pop()


def handle_nDUP(state, n):
    # (x -- x x) or (x1 x2 -- x1 x2 x1 x2) or (x1 x2 x3 -- x1 x2 x3 x1 x2 x3)
    state.require_stack_depth(n)
    state.stack.extend(state.stack[-n:])


def handle_OVER(state):
    # (x1 x2 -- x1 x2 x1)
    state.require_stack_depth(2)
    state.stack.append(state.stack[-2])


def handle_2OVER(state):
    # (x1 x2 x3 x4 -- x1 x2 x3 x4 x1 x2)
    state.require_stack_depth(4)
    state.stack.extend(state.stack[-4: -2])


def handle_ROT(state):
    # (x1 x2 x3 -- x2 x3 x1)
    state.require_stack_depth(3)
    state.stack.append(state.stack.pop(-3))


def handle_2ROT(state):
    # (x1 x2 x3 x4 x5 x6 -- x3 x4 x5 x6 x1 x2)
    state.require_stack_depth(6)
    state.stack.extend([state.stack.pop(-6), state.stack.pop(-5)])


def handle_SWAP(state):
    # ( x1 x2 -- x2 x1 )
    state.require_stack_depth(2)
    state.stack.append(state.stack.pop(-2))


def handle_2SWAP(state):
    # (x1 x2 x3 x4 -- x3 x4 x1 x2)
    state.require_stack_depth(4)
    state.stack.extend([state.stack.pop(-4), state.stack.pop(-3)])


def handle_IFDUP(state):
    # (x - 0 | x x)
    state.require_stack_depth(1)
    last = state.stack[-1]
    if cast_to_bool(last):
        state.stack.append(last)


def handle_DEPTH(state):
    # ( -- stacksize)
    state.stack.append(int_to_item(len(state.stack)))


def handle_NIP(state):
    # (x1 x2 -- x2)
    state.require_stack_depth(2)
    state.stack.pop(-2)


def handle_TUCK(state):
    # ( x1 x2 -- x2 x1 x2 )
    state.require_stack_depth(2)
    state.stack.insert(-2, state.stack[-1])


def handle_PICK_ROLL(state, op):
    # pick: (xn ... x2 x1 x0 n - xn ... x2 x1 x0 xn)
    # roll: (xn ... x2 x1 x0 n - ... x2 x1 x0 xn)
    state.require_stack_depth(2)
    n = int(state.to_number(state.stack[-1]))
    state.stack.pop()
    depth = len(state.stack)
    if not 0 <= n < depth:
        raise InvalidStackOperation(f'{op.name} with argument {n:,d} used '
                                    f'on stack with depth {depth:,d}')
    if op == Ops.OP_PICK:
        state.stack.append(state.stack[-(n + 1)])
    else:
        state.stack.append(state.stack.pop(-(n + 1)))


#
# Bitwise logic
#
def handle_INVERT(state):
    # (x -- out)
    state.require_stack_depth(1)
    state.stack[-1] = bytes(x ^ 255 for x in state.stack[-1])


def handle_binary_bitop(state, binop):
    # (x1 x2 -- out)
    state.require_stack_depth(2)
    x1 = state.stack[-2]
    x2 = state.stack[-1]
    if len(x1) != len(x2):
        raise InvalidOperandSize('operands to bitwise operator must have same size')
    state.stack.pop()
    state.stack[-1] = bytes(binop(b1, b2) for b1, b2 in zip(x1, x2))


def handle_EQUAL(state):
    # (x1 x2 -- bool).   Bitwise equality
    state.require_stack_depth(2)
    state.stack.append(bool_items[state.stack.pop() == state.stack.pop()])


def handle_EQUALVERIFY(state):
    # (x1 x2 -- )
    handle_EQUAL(state)
    if not cast_to_bool(state.stack[-1]):
        raise EqualVerifyFailed()
    state.stack.pop()


def shift_left(value, count):
    n_bytes, n_bits = divmod(count, 8)
    n_bytes = min(n_bytes, len(value))

    def pairs(value, n_bytes):
        for n in range(n_bytes, len(value) - 1):
            yield value[n], value[n + 1]
        if n_bytes < len(value):
            yield value[-1], 0
        for n in range(n_bytes):
            yield 0, 0

    return bytes(((lhs << n_bits) & 255) + (rhs >> (8 - n_bits))
                 for lhs, rhs in pairs(value, n_bytes))


def shift_right(value, count):
    n_bytes, n_bits = divmod(count, 8)
    n_bytes = min(n_bytes, len(value))

    def pairs(value, n_bytes):
        for n in range(n_bytes):
            yield 0, 0
        if n_bytes < len(value):
            yield 0, value[0]
        for n in range(len(value) - 1 - n_bytes):
            yield value[n], value[n + 1]

    return bytes(((lhs << (8 - n_bits)) & 255) + (rhs >> n_bits)
                 for lhs, rhs in pairs(value, n_bytes))


def handle_LSHIFT(state):
    # (x n -- out).   Logical bit-shift maintaining item size
    state.require_stack_depth(2)
    n = int(state.to_number(state.stack[-1]))
    if n < 0:
        raise NegativeShiftCount(f'invalid shift left of {n:,d} bits')
    state.stack.pop()
    state.stack[-1] = shift_left(state.stack[-1], n)


def handle_RSHIFT(state):
    # (x n -- out).   Logical bit-shift maintaining item size
    state.require_stack_depth(2)
    n = int(state.to_number(state.stack[-1]))
    if n < 0:
        raise NegativeShiftCount(f'invalid right left of {n:,d} bits')
    state.stack.pop()
    state.stack[-1] = shift_right(state.stack[-1], n)


#
# Numeric
#
def handle_unary_numeric(state, unary_op):
    # (x -- out)
    state.require_stack_depth(1)
    value = state.to_number(state.stack[-1])
    state.stack[-1] = int_to_item(unary_op(value))


def handle_binary_numeric(state, binary_op):
    # (x1 x2 -- out)
    state.require_stack_depth(2)
    x1 = state.to_number(state.stack[-2])
    x2 = state.to_number(state.stack[-1])
    try:
        result = binary_op(x1, x2)
    except ZeroDivisionError:
        raise DivisionByZero('division by zero' if binary_op is bitcoin_div
                             else 'modulo by zero') from None
    state.stack.pop()
    state.stack[-1] = int_to_item(result)


def handle_NUMEQUALVERIFY(state):
    # (x1 x2 -- )
    handle_binary_numeric(state, operator.eq)
    if not cast_to_bool(state.stack[-1]):
        raise NumEqualVerifyFailed('OP_NUMEQUALVERIFY failed')
    state.stack.pop()


def bitcoin_div(a, b):
    # In bitcoin script division is rounded towards zero
    result = abs(a) // abs(b)
    return -result if (a >= 0) ^ (b >= 0) else result


def bitcoin_mod(a, b):
    # In bitcoin script a % b is abs(a) % abs(b) with the sign of a.
    # Then (a % b) * b + a == a
    result = abs(a) % abs(b)
    return result if a >= 0 else -result


def logical_and(x1, x2):
    return 1 if (x1 and x2) else 0


def logical_or(x1, x2):
    return 1 if (x1 or x2) else 0


def handle_WITHIN(state):
    # (x max min -- out)    True if x is >= min and < max.
    state.require_stack_depth(3)
    x = item_to_int(state.stack[-3])
    mn = item_to_int(state.stack[-2])
    mx = item_to_int(state.stack[-1])
    state.stack.pop()
    state.stack.pop()
    state.stack[-1] = bool_items[mn <= x < mx]


#
# Crypto
#

def handle_hash(state, hash_func):
    # (x -- x x)
    state.require_stack_depth(1)
    state.stack.append(hash_func(state.stack.pop()))


def handle_CODESEPARATOR(state):
    # script_code starts after the code separator
    state.iterator.on_code_separator()


def handle_CHECKSIG(state):
    # (sig pubkey -- bool)
    state.require_stack_depth(2)
    sig_bytes = state.stack[-2]
    pubkey_bytes = state.stack[-1]
    state.validate_signature(sig_bytes)
    state.validate_pubkey(pubkey_bytes)
    script_code = state.iterator.script_code()
    script_code = state.cleanup_script_code(sig_bytes, script_code)
    is_good = state.check_sig(sig_bytes, pubkey_bytes, script_code)
    if not is_good:
        state.validate_nullfail(sig_bytes)
    state.stack.pop()
    state.stack[-1] = bool_items[is_good]


def handle_CHECKSIGVERIFY(state):
    # (sig pubkey -- )
    handle_CHECKSIG(state)
    if not cast_to_bool(state.stack[-1]):
        raise CheckSigVerifyFailed('OP_CHECKSIGVERIFY failed')
    state.stack.pop()


def handle_CHECKMULTISIG(state):
    # ([sig ...] sig_count [pubkey ...] pubkey_count -- bool)
    state.require_stack_depth(1)
    # Limit key count to 4 bytes
    key_count = state.to_number(state.stack[-1], length_limit=4)
    state.validate_pubkey_count(key_count)
    state.bump_op_count(key_count)
    # Ensure we can read sig_count, also limited to 4 bytes
    state.require_stack_depth(key_count + 2)
    sig_count = state.to_number(state.stack[-(key_count + 2)], length_limit=4)
    if not 0 <= sig_count <= key_count:
        raise InvalidSignatureCount(f'number of signatures, {sig_count:,d}, in OP_CHECKMULTISIG '
                                    f'lies outside range 0 <= count <= {key_count:,d}')

    # Ensure we have all the sigs
    item_count = key_count + sig_count + 2
    state.require_stack_depth(item_count)

    # Remove signatures for pre-BCH fork scripts
    script_code = state.iterator.script_code()
    first_sig_index = -(key_count + 3)
    for n in range(sig_count):
        script_code = state.cleanup_script_code(state.stack[first_sig_index - n], script_code)

    keys_remaining = key_count
    sigs_remaining = sig_count
    key_base_index = -(key_count + 2)
    sig_base_index = key_base_index - (sig_count + 1)
    # Loop while the remaining number of sigs to check does not exceed the remaining keys
    while keys_remaining >= sigs_remaining > 0:
        sig_bytes = state.stack[sig_base_index + sigs_remaining]
        state.validate_signature(sig_bytes)
        pubkey_bytes = state.stack[key_base_index + keys_remaining]
        state.validate_pubkey(pubkey_bytes)
        is_good = state.check_sig(sig_bytes, pubkey_bytes, script_code)
        if is_good:
            sigs_remaining -= 1
        keys_remaining -= 1

    is_good = keys_remaining >= sigs_remaining

    # Clean up the stack
    for n in range(item_count):
        # If the operation failed NULLFAIL requires all signatures be empty
        if not is_good and n >= key_count + 2:
            state.validate_nullfail(state.stack[-1])
        state.stack.pop()

    # An old CHECKMULTISIG bug consumes an extra argument.  Check it's null.
    state.require_stack_depth(1)
    state.validate_nulldummy()
    state.stack[-1] = bool_items[is_good]


def handle_CHECKMULTISIGVERIFY(state):
    # (sig pubkey -- )
    handle_CHECKMULTISIG(state)
    if not cast_to_bool(state.stack[-1]):
        raise CheckMultiSigVerifyFailed('OP_CHECKMULTISIGVERIFY failed')
    state.stack.pop()


#
# Byte string operations
#

def handle_CAT(state):
    # (x1 x2 -- x1x2 )
    state.require_stack_depth(2)
    item = state.stack[-2] + state.stack[-1]
    state.validate_item_size(len(item))
    state.stack.pop()
    state.stack[-1] = item


def handle_SPLIT(state):
    # (x posiition -- x1 x2)
    state.require_stack_depth(2)
    x = state.stack[-2]
    n = int(state.to_number(state.stack[-1]))
    if not 0 <= n <= len(x):
        raise InvalidSplit(f'cannot split item of length {len(x):,d} at position {n:,d}')
    state.stack[-2] = x[:n]
    state.stack[-1] = x[n:]


def handle_NUM2BIN(state):
    # (in size -- out)  encode the value of "in" in size bytes
    state.require_stack_depth(2)
    size = int(state.to_number(state.stack[-1]))
    if size < 0 or size > INT32_MAX:
        raise InvalidPushSize(f'invalid size {size:,d} in OP_NUM2BIN operation')
    state.validate_item_size(size)
    state.stack.pop()
    state.stack[-1] = int_to_item(item_to_int(state.stack[-1]), size)


def handle_BIN2NUM(state):
    # (in -- out)    minimally encode in as a number
    state.require_stack_depth(1)
    state.stack[-1] = minimal_encoding(state.stack[-1])
    state.validate_number_length(len(state.stack[-1]))


def handle_SIZE(state):
    # ( x -- x size(x) )
    state.require_stack_depth(1)
    size = len(state.stack[-1])
    state.stack.append(int_to_item(size))


#
# Expansion
#

def handle_upgradeable_nop(state, op):
    state.handle_upgradeable_nop(op)


def handle_CHECKLOCKTIMEVERIFY(state):
    if not state.flags & InterpreterFlags.ENABLE_CHECKLOCKTIMEVERIFY:
        handle_upgradeable_nop(state, Ops.OP_NOP2)
    else:
        state.require_stack_depth(1)
        locktime = state.to_number(state.stack[-1], length_limit=5)
        if locktime < 0:
            raise LockTimeError(f'locktime {locktime:,d} is negative')
        state.validate_locktime(locktime)


def handle_CHECKSEQUENCEVERIFY(state):
    if not state.flags & InterpreterFlags.ENABLE_CHECKSEQUENCEVERIFY:
        handle_upgradeable_nop(state, Ops.OP_NOP3)
    else:
        state.require_stack_depth(1)
        sequence = state.to_number(state.stack[-1], length_limit=5)
        if sequence < 0:
            raise LockTimeError(f'sequence {sequence:,d} is negative')
        state.validate_sequence(sequence)


op_handlers = [partial(invalid_opcode, op=op) for op in range(256)]

#
# Control
#
op_handlers[Ops.OP_NOP] = handle_NOP
op_handlers[Ops.OP_VER] = partial(invalid_opcode, op=Ops.OP_VER)
op_handlers[Ops.OP_IF] = partial(handle_IF, op=Ops.OP_IF)
op_handlers[Ops.OP_NOTIF] = partial(handle_IF, op=Ops.OP_NOTIF)
op_handlers[Ops.OP_VERIF] = partial(handle_VERIF, op=Ops.OP_VERIF)
op_handlers[Ops.OP_VERNOTIF] = partial(handle_VERIF, op=Ops.OP_VERNOTIF)
op_handlers[Ops.OP_ELSE] = handle_ELSE
op_handlers[Ops.OP_ENDIF] = handle_ENDIF
op_handlers[Ops.OP_VERIFY] = handle_VERIFY
op_handlers[Ops.OP_RETURN] = handle_RETURN

#
# Stack operations
#
op_handlers[Ops.OP_TOALTSTACK] = handle_TOALTSTACK
op_handlers[Ops.OP_FROMALTSTACK] = handle_FROMALTSTACK
op_handlers[Ops.OP_DROP] = handle_DROP
op_handlers[Ops.OP_2DROP] = handle_2DROP
op_handlers[Ops.OP_DUP] = partial(handle_nDUP, n=1)
op_handlers[Ops.OP_2DUP] = partial(handle_nDUP, n=2)
op_handlers[Ops.OP_3DUP] = partial(handle_nDUP, n=3)
op_handlers[Ops.OP_OVER] = handle_OVER
op_handlers[Ops.OP_2OVER] = handle_2OVER
op_handlers[Ops.OP_2ROT] = handle_2ROT
op_handlers[Ops.OP_2SWAP] = handle_2SWAP
op_handlers[Ops.OP_IFDUP] = handle_IFDUP
op_handlers[Ops.OP_DEPTH] = handle_DEPTH
op_handlers[Ops.OP_NIP] = handle_NIP
op_handlers[Ops.OP_PICK] = partial(handle_PICK_ROLL, op=Ops.OP_PICK)
op_handlers[Ops.OP_ROLL] = partial(handle_PICK_ROLL, op=Ops.OP_ROLL)
op_handlers[Ops.OP_ROT] = handle_ROT
op_handlers[Ops.OP_SWAP] = handle_SWAP
op_handlers[Ops.OP_TUCK] = handle_TUCK

#
# Byte string operations
#
op_handlers[Ops.OP_CAT] = handle_CAT
op_handlers[Ops.OP_SPLIT] = handle_SPLIT
op_handlers[Ops.OP_NUM2BIN] = handle_NUM2BIN
op_handlers[Ops.OP_BIN2NUM] = handle_BIN2NUM
op_handlers[Ops.OP_SIZE] = handle_SIZE

#
# Bitwise logic
#
op_handlers[Ops.OP_INVERT] = handle_INVERT
op_handlers[Ops.OP_AND] = partial(handle_binary_bitop, binop=operator.and_)
op_handlers[Ops.OP_OR] = partial(handle_binary_bitop, binop=operator.or_)
op_handlers[Ops.OP_XOR] = partial(handle_binary_bitop, binop=operator.xor)
op_handlers[Ops.OP_EQUAL] = handle_EQUAL
op_handlers[Ops.OP_EQUALVERIFY] = handle_EQUALVERIFY
op_handlers[Ops.OP_LSHIFT] = handle_LSHIFT
op_handlers[Ops.OP_RSHIFT] = handle_RSHIFT

#
# Numeric
#
op_handlers[Ops.OP_1ADD] = partial(handle_unary_numeric, unary_op=lambda x: x + 1)
op_handlers[Ops.OP_1SUB] = partial(handle_unary_numeric, unary_op=lambda x: x - 1)
# OP_2MUL = 0x8d
# OP_2DIV = 0x8e
op_handlers[Ops.OP_NEGATE] = partial(handle_unary_numeric, unary_op=operator.neg)
op_handlers[Ops.OP_ABS] = partial(handle_unary_numeric, unary_op=operator.abs)
op_handlers[Ops.OP_NOT] = partial(handle_unary_numeric, unary_op=operator.not_)
op_handlers[Ops.OP_0NOTEQUAL] = partial(handle_unary_numeric, unary_op=operator.truth)
op_handlers[Ops.OP_ADD] = partial(handle_binary_numeric, binary_op=operator.add)
op_handlers[Ops.OP_SUB] = partial(handle_binary_numeric, binary_op=operator.sub)
op_handlers[Ops.OP_MUL] = partial(handle_binary_numeric, binary_op=operator.mul)
op_handlers[Ops.OP_DIV] = partial(handle_binary_numeric, binary_op=bitcoin_div)
op_handlers[Ops.OP_MOD] = partial(handle_binary_numeric, binary_op=bitcoin_mod)
op_handlers[Ops.OP_BOOLAND] = partial(handle_binary_numeric, binary_op=logical_and)
op_handlers[Ops.OP_BOOLOR] = partial(handle_binary_numeric, binary_op=logical_or)
op_handlers[Ops.OP_NUMEQUAL] = partial(handle_binary_numeric, binary_op=operator.eq)
op_handlers[Ops.OP_NUMEQUALVERIFY] = handle_NUMEQUALVERIFY
op_handlers[Ops.OP_NUMNOTEQUAL] = partial(handle_binary_numeric, binary_op=operator.ne)
op_handlers[Ops.OP_LESSTHAN] = partial(handle_binary_numeric, binary_op=operator.lt)
op_handlers[Ops.OP_GREATERTHAN] = partial(handle_binary_numeric, binary_op=operator.gt)
op_handlers[Ops.OP_LESSTHANOREQUAL] = partial(handle_binary_numeric, binary_op=operator.le)
op_handlers[Ops.OP_GREATERTHANOREQUAL] = partial(handle_binary_numeric, binary_op=operator.ge)
op_handlers[Ops.OP_MIN] = partial(handle_binary_numeric, binary_op=min)
op_handlers[Ops.OP_MAX] = partial(handle_binary_numeric, binary_op=max)
op_handlers[Ops.OP_WITHIN] = handle_WITHIN

#
# Crypto
#
op_handlers[Ops.OP_RIPEMD160] = partial(handle_hash, hash_func=ripemd160)
op_handlers[Ops.OP_SHA1] = partial(handle_hash, hash_func=sha1)
op_handlers[Ops.OP_SHA256] = partial(handle_hash, hash_func=sha256)
op_handlers[Ops.OP_HASH160] = partial(handle_hash, hash_func=hash160)
op_handlers[Ops.OP_HASH256] = partial(handle_hash, hash_func=double_sha256)
op_handlers[Ops.OP_CODESEPARATOR] = handle_CODESEPARATOR
op_handlers[Ops.OP_CHECKSIG] = handle_CHECKSIG
op_handlers[Ops.OP_CHECKSIGVERIFY] = handle_CHECKSIGVERIFY
op_handlers[Ops.OP_CHECKMULTISIG] = handle_CHECKMULTISIG
op_handlers[Ops.OP_CHECKMULTISIGVERIFY] = handle_CHECKMULTISIGVERIFY

#
# Expansion
#
for _op in (Ops.OP_NOP1, Ops.OP_NOP4, Ops.OP_NOP5, Ops.OP_NOP6, Ops.OP_NOP7,
            Ops.OP_NOP8, Ops.OP_NOP9, Ops.OP_NOP10):
    op_handlers[_op] = partial(handle_upgradeable_nop, op=_op)
op_handlers[Ops.OP_NOP2] = handle_CHECKLOCKTIMEVERIFY
op_handlers[Ops.OP_NOP3] = handle_CHECKSEQUENCEVERIFY
