# Copyright (c) Collab and contributors.
# See LICENSE for details.

import logging


logger = logging.getLogger(__name__)


class ATParser(object):
    """
    An AT (Hayes command) parser based on a subset of the ITU-T V.250 standard.

    Conformant with the subset of V.250 required for implementation of the
    Bluetooth Headset and Handsfree Profiles, as per Bluetooth SIP
    specifications. Also implements some V.250 features not required by
    Bluetooth - such as chained commands.

    Command handlers are registered with an :py:class:`ATParser` instance.
    These handlers are invoked when command lines are processed by the
    :py:func:`ATParser.process` method.

    The :py:class:`ATParser` object accepts a new command line to parse
    via its :py:func:`process` method. It breaks each command line into one or
    more commands. Each command is parsed for name, type, and (optional)
    arguments, and an appropriate external handler method is called through
    the :py:class:`ATCommandHandler` interface.

    The command types are:

    - **Basic** Command. For example ``"ATDT1234567890"``. Basic command names are
      a single character (e.g. ``"D"``), and everything following this character is
      passed to the handler as a string argument (e.g. ``"T1234567890"``).
    - **Action** Command. For example ``"AT+CIMI"``. The command name is ``"CIMI"``, and
      there are no arguments for action commands.
    - **Read** Command. For example ``"AT+VGM?"``. The command name is ``"VGM"``, and there
      are no arguments for get commands.
    - **Set** Command. For example ``"AT+VGM=14"``. The command name is ``"VGM"``, and
      there is a single integer argument in this case. In the general case
      there can be zero or more arguments (comma delimited) each of integer
      or string type.
    - **Test** Command. For example ``"AT+VGM=?"``. No arguments.

    In V.250 the last four command types are known as Extended Commands, and
    they are used heavily in Bluetooth for example.

    Basic commands cannot be chained in this implementation. For Bluetooth
    headset/handsfree use this is acceptable, because they only use the basic
    commands ATA and ATD, which are not allowed to be chained. For general V.250
    use we would need to improve this class to allow Basic command chaining -
    however it's tricky to get right because there is no delimiter for Basic
    command chaining.

    Extended commands can be chained. For example::

      AT+VGM?;+VGM=14;+CIMI

    This is equivalent to::

      AT+VGM?
      AT+VGM=14
      AT+CIMI

    Except that only one final result code is returned (although several
    intermediate responses may be returned), and as soon as one command in the
    chain fails the rest are abandoned.

    Handlers are registered by there command name via register(Char c, ...) or
    register(String s, ...). Handlers for basic command should be registered by
    the basic command character, and handlers for Extended commands should be
    registered by string.

    References:

    - ITU-T Recommendation V.250
    - ETSI TS 127.007 (AT Command set for User Equipment, 3GPP TS 27.007)
    - Bluetooth Headset Profile Spec (K6)
    - Bluetooth Handsfree Profile Spec (HFP 1.5)
    """

    # Extended command type enumeration, only used internally
    TYPE_ACTION = 0   # AT+FOO
    TYPE_READ = 1     # AT+FOO?
    TYPE_SET = 2      # AT+FOO=
    TYPE_TEST = 3     # AT+FOO=?

    def __init__(self):
        self.commandHandlers = {}
        self.mLastInput = ''

    def register(self, command, handler):
        """
        Register a basic or extended command handler.

        Basic command handlers are later called via their
        ``handleBasicCommand(args)`` method.

        Extended command handlers are later called via:

        - ``handleActionCommand()``
        - ``handleGetCommand()``
        - ``handleSetCommand()``
        - ``handleTestCommand()``

        Only one method will be called for each command processed.

        :param command: Command name - a single character for basic commands or
            multiple characters for extended commands.
        :type command: str
        :param handler: Handler to register for the command.
        :type handler: :py:class:`ATCommandHandler`
        """
        logger.debug('Registering command handler {} for {}'.format(
            handler, command))

        self.commandHandlers[command] = handler

    def clean(self, data):
        """
        Strip input of whitespace and force uppercase - except sections inside
        quotes. Also fixes unmatched quotes (by appending a quote). Double
        quotes " are the only quotes allowed by V.250.

        :param data: Command string.
        :type data: str
        :rtype: str
        """
        logging.debug('Cleaning data: {}'.format(data))

        out = []
        for i in range(len(data)):
            c = data[i]
            if c == '"':
                j = data.find('"', i + 1)  # search for closing "
                if j == -1:  # unmatched ", insert one.
                    out.append(data[i:])
                    out.append('"')
                    break

                out.append(data[i:j + 1])
                i = j
            elif c != ' ':
                out.append(c.capitalize())

        return "".join(out)


    def isAtoZ(self, char):
        """
        Indicates if ``char`` is a character between A and Z.

        :param char:
        :type char: str
        :rtype: bool
        """
        return char >= 'A' and char <= 'Z'


    def findChar(self, ch, data, fromIndex):
        """
        Find a character ``ch``, ignoring quoted sections.

        Return length of ``data`` if not found.

        :param ch:
        :type ch: str
        :param data:
        :type data: str
        :param fromIndex:
        :type fromIndex: int
        """
        for i in range(fromIndex, len(data)):
            c = data[i]
            if c == '"':
                i = data.find('"', i + 1)
                if i == -1:
                    return len(data)

            elif c == ch:
                return i

        return len(data)

    def generateArgs(self, data):
        """
        Break an argument string into individual arguments (comma delimited).
        Integer arguments are turned into integers. Otherwise a string is used.

        :param data: The argument string.
        :type data: str
        :rtype: list
        """
        i = 0
        out = []
        while i <= len(data):
            j = self.findChar(',', data, i)

            arg = data[i:j]
            try:
                out.append(int(arg))
            except ValueError:
                out.append(arg)

            i = j + 1  # move past comma

        return out

    def findEndExtendedName(self, data, index):
        """
        Return the index of the end of character after the last character in
        the extended command name. Uses the V.250 spec for allowed command
        names.

        :param data: The extended command name.
        :type data: str
        :param index:
        :type index: int
        :rtype: int
        """
        for i in range(index, len(data)):
            c = data[i]

            # V.250 defines the following chars as legal extended command
            # names
            if self.isAtoZ(c):
                continue
            if c >= '0' and c <= '9':
                continue
            if c in ['!', '%', '-', '.', '/', ':', '_']:
                continue
            return i

        return len(data)

    def process(self, data):
        """
        Processes an incoming AT command line.

        This method will invoke zero or one command handler methods for each
        command in the command line.

        :param data: The AT input, without EOL delimiter (e.g. ``<CR>``).
        :type data: str
        :return: Result object for this command line. This can be
          converted to a string response with
          :py:func:`ATCommandResult.toString()`.
        :rtype: :py:class:`ATCommandResult`
        """
        logger.debug('process: {}'.format(data))

        inputData = self.clean(data)

        logger.debug('inputData: {}'.format(inputData))

        # Handle "A/" (repeat previous line)
        if inputData[0:2] == "A/":
            inputData = str(self.mLastInput)
        else:
            self.mLastInput = str(inputData)

        # Handle empty line - no response necessary
        if inputData == '':
            # Return []
            return ATCommandResult(ATCommandResult.UNSOLICITED)

        # Anything else deserves an error
        if inputData[0:2] != "AT":
            # Return ["ERROR"]
            return ATCommandResult(ATCommandResult.ERROR)

        # Ok we have a command that starts with AT. Process it
        index = 2
        result = ATCommandResult(ATCommandResult.UNSOLICITED)

        while index < len(inputData):
            c = inputData[index]

            if self.isAtoZ(c):
                # Option 1: Basic Command
                # Pass the rest of the line as is to the handler. Do not
                # look for any more commands on this line.
                args = inputData[index + 1:]
                logger.debug('args: {} - char: {} - commandHandlers: {}'.format(
                    args, c, self.commandHandlers))
                if c in self.commandHandlers:
                    result.addResult(self.commandHandlers.get(c).handleBasicCommand(args))
                    return result
                else:
                    # no handler
                    result.addResult(ATCommandResult(ATCommandResult.ERROR))
                    return result

            if c == '+':
                # Option 2: Extended Command
                # Search for first non-name character. Short-circuit if
                # we don't handle this command name.
                i = self.findEndExtendedName(inputData, index + 1)
                commandName = inputData[index:i]

                if commandName not in self.commandHandlers:
                    # no handler
                    result.addResult(ATCommandResult(ATCommandResult.ERROR))
                    return result

                handler = self.commandHandlers.get(commandName)
                logger.debug('commandName: {}, handler: {}'.format(commandName, handler))

                # Search for end of this command - this is usually the end of
                # line
                endIndex = self.findChar(';', inputData, index)

                # Determine what type of command this is.
                # Default to TYPE_ACTION if we can't find anything else
                # obvious.
                if i >= endIndex:
                    commandType = self.TYPE_ACTION
                elif inputData[i] == '?':
                    commandType = self.TYPE_READ
                elif inputData[i] == '=':
                    if (i + 1) < endIndex:
                        if inputData[i + 1] == '?':
                            commandType = self.TYPE_TEST
                        else:
                            commandType = self.TYPE_SET
                    else:
                        commandType = self.TYPE_SET
                else:
                    commandType = self.TYPE_ACTION

                # Call this command. Short-circuit as soon as a command fails
                if commandType == self.TYPE_ACTION:
                    result.addResult(handler.handleActionCommand())

                elif commandType == self.TYPE_READ:
                    result.addResult(handler.handleReadCommand())

                elif commandType == self.TYPE_TEST:
                    result.addResult(handler.handleTestCommand())

                elif commandType == self.TYPE_SET:
                    args = self.generateArgs(inputData[i + 1:endIndex])
                    result.addResult(handler.handleSetCommand(args))

                if result.getResultCode() != ATCommandResult.OK:
                    return result

                index = endIndex

            else:
                # Can't tell if this is a basic or extended command.
                # Push forwards and hope we hit something.
                index += 1

        # Finished processing (and all results were ok)
        return result


class ATCommandResult(object):
    """
    Foo.
    """
    #: Success result code
    OK = 0
    #: Error result code
    ERROR = 1
    #: Unsolicited result code
    UNSOLICITED = 2

    #: Success response string
    OK_STRING = 'OK'

    #: Error response string
    ERROR_STRING = 'ERROR'

    def __init__(self, resultCode=0, response=None):
        """
        Construct a new :py:class:`ATCommandResult` with an optional
        single line response.

        :param resultCode: One of :py:data:`OK`, :py:data:`ERROR` or
            :py:data:`UNSOLICITED`.
        :type resultCode: int
        :param response: The single line response.
        :type response:
        """
        self.mResultCode = resultCode
        self.mResponse = ''

        if response is not None:
            self.addResponse(response)

    def getResultCode(self):
        """
        :rtype: int
        """
        return self.mResultCode

    def addResponse(self, response):
        """
        Add another line to the response.

        :param response:
        :type response: str
        """
        self.mResponse = self.appendWithCrlf(self.mResponse, response)

    def addResult(self, result):
        """
        Add the given result into this :py:class:`ATCommandResult` instance.

        Used to combine results from multiple commands in a single command line
        (command chaining).

        :param result: The :py:class:`ATCommandResult` to add to this result.
        :type result: :py:class:`ATCommandResult`
        """
        logger.debug('addResult: {}'.format(result))

        if result is not None:
            self.mResponse = self.appendWithCrlf(self.mResponse,
                result.mResponse)
            self.mResultCode = result.mResultCode

    def toString(self):
        """
        Generate the string response ready to send.

        :rtype: str
        """
        result = str(self.mResponse)
        if self.mResultCode == self.OK:
            result = self.appendWithCrlf(result, self.OK_STRING)

        elif self.mResultCode == self.ERROR:
            result = self.appendWithCrlf(result, self.ERROR_STRING)

        return result

    def appendWithCrlf(self, str1, str2):
        """
        Append a string, joining with a double CRLF. Used to create multi-line
        AT command replies.
        """
        if len(str1) > 0 and len(str2) > 0:
            str1 += '\r\n\r\n'

        return str1 + str(str2)


class ATCommandHandler(object):
    """
    Bar.
    """
    def handleBasicCommand(self, arg):
        """
        Handle Basic command ``"ATA"``.

        These are single letter commands such as ATA and ATD. Anything following
        the single letter command (``'A'`` and ``'D'`` respectively) will be
        passed as ``'arg'``.

        For example, ``'ATDT1234'`` would result in the call
        ``handleBasicCommand('T1234')``.

        :param arg: Everything following the basic command character.
        :type arg: str
        :return: The result of this command.
        """
        return ATCommandResult(ATCommandResult.ERROR)

    def handleActionCommand(self):
        """
        Handle Actions command ``"AT+FOO"``.

        Action commands are part of the Extended command syntax, and are
        typically used to signal an action on ``"FOO"``.

        :return The result of this command.
        """
        return ATCommandResult(ATCommandResult.ERROR)

    def handleReadCommand(self):
        """
        Handle Read command ``"AT+FOO?"``.

        Read commands are part of the Extended command syntax, and are
        typically used to read the value of ``"FOO"``.

        :return The result of this command.
        """
        return ATCommandResult(ATCommandResult.ERROR)

    def handleSetCommand(self, args):
        """
        Handle Set command ``"AT+FOO=..."``.

        Set commands are part of the Extended command syntax, and are
        typically used to set the value of "FOO". Multiple arguments can be
        sent. For example::

          AT+FOO=[<arg1>[,<arg2>[,...]]]

        Each argument will be either numeric (int) or string.
        :py:func:`handleSetCommand` is passed a generic Object[] array in which each
        element will be an Integer (if it can be parsed with parseInt()) or
        String.

        Missing arguments ``",,"`` are set to empty strings.

        :param args: List of string and/or integers. There will always be at
          least one element in this list.
        :type args: list
        :return: The result of this command.
        """
        return ATCommandResult(ATCommandResult.ERROR)

    def handleTestCommand(self):
        """
        Handle Test command ``"AT+FOO=?"``.

        Test commands are part of the Extended command syntax, and are typically
        used to request an indication of the range of legal values that ``"FOO"``
        can take.

        By default an OK result is returned to indicate that this command is at
        least recognized.

        :return: The result of this command.
        """
        return ATCommandResult(ATCommandResult.OK)
