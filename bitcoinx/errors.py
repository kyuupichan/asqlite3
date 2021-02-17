# Copyright (c) 2021, Neil Booth
#
# All rights reserved.
#
# Licensed under the the Open BSV License version 3; see LICENCE for details.
#

'''Exception hierarchy.'''


__all__ = (
    'ScriptError', 'TruncatedScriptError', 'InterpreterError',
    'StackSizeTooLarge', 'TooManyOps', 'MinimalEncodingError',
    'ScriptTooLarge', 'MinimalIfError', 'DivisionByZero', 'NegativeShiftCount',
    'InvalidPushSize', 'DisabledOpcode', 'UnbalancedConditional', 'InvalidStackOperation',
    'VerifyFailed', 'OpReturnError', 'InvalidOpcode', 'InvalidSplit', 'ImpossibleEncoding',
    'InvalidNumber', 'InvalidOperandSize', 'EqualVerifyFailed',
    'InvalidPublicKeyEncoding', 'InvalidSignature',
)


#
# Exception Hierarchy
#


class ScriptError(Exception):
    '''Base class for script errors.'''


class TruncatedScriptError(ScriptError):
    '''Raised when a script is truncated because a pushed item is not all present.'''


class InterpreterError(ScriptError):
    '''Base class for interpreter errors.'''


class ScriptTooLarge(InterpreterError):
    '''Raised when a script is too long.'''


class TooManyOps(InterpreterError):
    '''Raised when a script contains too many operations.'''


class InvalidStackOperation(InterpreterError):
    '''Raised when an opcode wants to access items deyond the stack depth.'''


class MinimalEncodingError(InterpreterError):
    '''Raised when a stack push happens not using the minimally-encoded push operation, or
    of a non-minally-encoded number.'''


class InvalidPushSize(InterpreterError):
    '''Raised when an item size is negative or too large.'''


class ImpossibleEncoding(InterpreterError):
    '''Raised when an OP_NUM2BIN encoding will not fit in the required size.'''


class InvalidNumber(InterpreterError):
    '''Raised when an OP_BIN2NUM result exceeds the maximum number size.'''


class InvalidOperandSize(InterpreterError):
    '''Raised when the operands to a binary operator are of invalid sizes.'''


class StackSizeTooLarge(InterpreterError):
    '''Raised when the stack size it too large.'''


class DivisionByZero(InterpreterError):
    '''Raised when a division or modulo by zero is executed.'''


class MinimalIfError(InterpreterError):
    '''Raised when the top of stack is not boolean processing OP_IF or OP_NOTIF.'''


class DisabledOpcode(InterpreterError):
    '''Raised when a disabled opcode is encountered.'''


class InvalidOpcode(InterpreterError):
    '''Raised when an invalid opcode is encountered.'''


class NegativeShiftCount(InterpreterError):
    '''Raised when a shift of a negative number of bits is encountered.'''


class InvalidSplit(InterpreterError):
    '''Raised when trying to split an item at an invalid position.'''


class UnbalancedConditional(InterpreterError):
    '''Raised when a script contains unepxected OP_ELSE, OP_ENDIF conditionals, or if
    open condition blocks are unterminated.'''


class OpReturnError(InterpreterError):
    '''OP_RETURN was encountered pre-genesis.'''


class InvalidPublicKeyEncoding(InterpreterError):
    '''Raised on an invalid public key encoding when checking a signature.'''


class InvalidSignature(InterpreterError):
    '''Raised on various invalid signature encodings when checking a signature.'''


class VerifyFailed(InterpreterError):
    '''OP_VERIFY was executed and the top of stack was zero.'''


class EqualVerifyFailed(VerifyFailed):
    '''OP_EQUALVERIFY was executed and it failed.'''


class NumEqualVerifyFailed(VerifyFailed):
    '''OP_NUMEQUALVERIFY was executed and it failed.'''
