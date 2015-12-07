# Copyright (c) Collab and contributors.
# See LICENSE for details.

"""
Tests for :py:mod:`atcmd.parser`.
"""

try:
    # py3
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

from unittest import TestCase

from atcmd.parser import ATParser, ATCommandHandler, ATCommandResult


class BasicCommandHandler(ATCommandHandler):
    def handleBasicCommand(self, arg):
        return ATCommandResult(ATCommandResult.OK)


class ExtendedCommandHandler(ATCommandHandler):
    def handleTestCommand(self):
        return ATCommandResult(ATCommandResult.OK)

    def handleActionCommand(self):
        return ATCommandResult(ATCommandResult.OK)

    def handleSetCommand(self, args):
        return ATCommandResult(ATCommandResult.OK)

    def handleReadCommand(self):
        return ATCommandResult(ATCommandResult.OK)


class ExtendedCommandHandler2(ATCommandHandler):
    def handleTestCommand(self):
        return ATCommandResult(ATCommandResult.OK)

    def handleActionCommand(self):
        return ATCommandResult(ATCommandResult.ERROR)

    def handleSetCommand(self, args):
        return ATCommandResult(ATCommandResult.OK)

    def handleReadCommand(self):
        return ATCommandResult(ATCommandResult.OK)


class BasicTest(TestCase):
    """
    The right method is being called.
    """
    def setUp(self):
        self.parser = ATParser()

    def test_basic(self):
        d = BasicCommandHandler()
        a = BasicCommandHandler()
        self.parser.register('D', d);
        self.parser.register('A', a);

        result = self.parser.process('  A T D = ? T 1 2 3  4   ')
        self.assertEqual(result.toString(), ATCommandResult.OK_STRING)


class CrazyStringsTest(TestCase):
    """
    Can handle all types of crazy strings.
    """
    def setUp(self):
        self.parser = ATParser()
        a = BasicCommandHandler()
        b = ExtendedCommandHandler()
        c= ExtendedCommandHandler2()
        self.parser.register('A', a);
        self.parser.register('+0', b);
        self.parser.register('+:', b);
        self.parser.register('+4', c)

    def test_strings(self):
        result = self.parser.process('     ')
        self.assertEqual(result.toString(), '')

        result = self.parser.process("  a T a t \"\"  1 2 3 a 4   ")
        self.assertEqual(result.toString(), ATCommandResult.OK_STRING)

        result = self.parser.process("  a T a t  \"foo BaR12Z\" 1 2 3 a 4   ")
        self.assertEqual(result.toString(), ATCommandResult.OK_STRING)

        result = self.parser.process("ATA\"")
        self.assertEqual(result.toString(), ATCommandResult.OK_STRING)

        result = self.parser.process("ATA\"a")
        self.assertEqual(result.toString(), ATCommandResult.OK_STRING)

        result = self.parser.process("ATa\" ")
        self.assertEqual(result.toString(), ATCommandResult.OK_STRING)

        result = self.parser.process("ATa\" ")
        self.assertEqual(result.toString(), ATCommandResult.OK_STRING)

        result = self.parser.process("ATA  \"one \" two \"t hr ee ")
        self.assertEqual(result.toString(), ATCommandResult.OK_STRING)

        # legal extended command names
        result = self.parser.process("AT+0")
        self.assertEqual(result.toString(), ATCommandResult.OK_STRING)

        result = self.parser.process("AT+:")
        self.assertEqual(result.toString(), ATCommandResult.OK_STRING)

        # non-AT
        result = self.parser.process("BF+A")
        self.assertEqual(result.toString(), ATCommandResult.ERROR_STRING)

        # no handler
        parser = ATParser()
        result = parser.process("ATZ")
        self.assertEqual(result.toString(), ATCommandResult.ERROR_STRING)

        # fallback action commandType
        result = self.parser.process("AT+0,")
        self.assertEqual(result.toString(), ATCommandResult.OK_STRING)

        # error result code
        result = self.parser.process("AT+4,")
        self.assertEqual(result.toString(), ATCommandResult.ERROR_STRING)


class SimpleExtendedTest(TestCase):
    """
    Support for simple extended commands.
    """
    def setUp(self):
        self.parser = ATParser()
        a = ExtendedCommandHandler()
        self.parser.register('+A', a);

    def test_strings(self):
        result = self.parser.process('AT+B')
        self.assertEqual(result.toString(), ATCommandResult.ERROR_STRING)

        result = self.parser.process('AT+A')
        self.assertEqual(result.toString(), ATCommandResult.OK_STRING)

        result = self.parser.process('AT+A=')
        self.assertEqual(result.toString(), ATCommandResult.OK_STRING)

        result = self.parser.process('AT+A=?')
        self.assertEqual(result.toString(), ATCommandResult.OK_STRING)

        result = self.parser.process('AT+A?')
        self.assertEqual(result.toString(), ATCommandResult.OK_STRING)


class ChainedCommandTest(TestCase):
    """
    Support for chained commands.
    """
    def setUp(self):
        self.parser = ATParser()
        a = BasicCommandHandler()
        b = ExtendedCommandHandler()
        c = ExtendedCommandHandler()
        self.parser.register('A', a)
        self.parser.register('+B', b)
        self.parser.register('+C', c)

    def test_strings(self):
        result = self.parser.process('AT+B100;+C')
        self.assertEqual(result.toString(), ATCommandResult.ERROR_STRING)

        result = self.parser.process('AT+C;+B')
        self.assertEqual(result.toString(), ATCommandResult.OK_STRING)


class SetCommandTest(TestCase):
    """
    Support for set commands.
    """
    def setUp(self):
        self.parser = ATParser()
        a = ExtendedCommandHandler()
        self.parser.register('+AAAA', a)

    def test_strings(self):
        result = self.parser.process('AT+AAAA=1')
        self.assertEqual(result.toString(), ATCommandResult.OK_STRING)

        result = self.parser.process('AT+AAAA=1,2,3')
        self.assertEqual(result.toString(), ATCommandResult.OK_STRING)

        result = self.parser.process('AT+AAAA=3,0,0,1')
        self.assertEqual(result.toString(), ATCommandResult.OK_STRING)

        result = self.parser.process("AT+AAAA=\"foo\",1,\"b,ar")
        self.assertEqual(result.toString(), ATCommandResult.OK_STRING)

        result = self.parser.process("AT+AAAA=")
        self.assertEqual(result.toString(), ATCommandResult.OK_STRING)

        result = self.parser.process("AT+AAAA=,")
        self.assertEqual(result.toString(), ATCommandResult.OK_STRING)

        result = self.parser.process("AT+AAAA=,,,")
        self.assertEqual(result.toString(), ATCommandResult.OK_STRING)

        result = self.parser.process("AT+AAAA=,1,,\"foo\",")
        self.assertEqual(result.toString(), ATCommandResult.OK_STRING)


class RepeatCommandTest(TestCase):
    """
    Support for repeat commands.
    """
    def setUp(self):
        self.parser = ATParser()
        a = BasicCommandHandler()
        self.parser.register('A', a)

    def test_strings(self):
        result = self.parser.process('A/')
        self.assertEqual(result.toString(), '')

        result = self.parser.process('ATA')
        self.assertEqual(result.toString(), ATCommandResult.OK_STRING)

        result = self.parser.process('A/')
        self.assertEqual(result.toString(), ATCommandResult.OK_STRING)

        result = self.parser.process('A/')
        self.assertEqual(result.toString(), ATCommandResult.OK_STRING)


class HandlerDefaultTest(TestCase):
    """
    Default values for :py:class:`ATCommandHandler`.
    """
    def test_strings(self):
        a = ATCommandHandler()
        self.assertEqual(a.handleBasicCommand('foo').toString(),
            ATCommandResult.ERROR_STRING)
        self.assertEqual(a.handleActionCommand().toString(),
            ATCommandResult.ERROR_STRING)
        self.assertEqual(a.handleReadCommand().toString(),
            ATCommandResult.ERROR_STRING)
        self.assertEqual(a.handleSetCommand('foo').toString(),
            ATCommandResult.ERROR_STRING)
        self.assertEqual(a.handleTestCommand().toString(),
            ATCommandResult.OK_STRING)


class ReturnValueTest(TestCase):
    """
    """
    def test_strings(self):
        self.parser = ATParser()

        commandResponseValue = 120
        commandName = 'F'
        commandArg = '100'

        a = ATCommandHandler()
        a.handleBasicCommand = MagicMock(return_value=ATCommandResult(
            ATCommandResult.OK, commandResponseValue))
        self.parser.register(commandName, a)

        result = self.parser.process('AT{}{}'.format(commandName, commandArg))
        a.handleBasicCommand.assert_called_with(commandArg)
        self.assertEqual(result.toString(), '120\r\n\r\nOK')
