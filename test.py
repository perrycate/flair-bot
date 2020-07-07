#!/usr/bin/env python3
import unittest
import discord
import time
import asyncio
import os
from unittest.mock import MagicMock

import main
from util import Storage

# Make sure this doesn't coincide with a sqlite db file that's really used.
TEST_DB = 'test_db_please_ignore.db'

ADMIN_CHANNEL = 'admin-channel'


# Contains common setup, teardown, helper methods to be used by test cases.
class BaseTest(unittest.TestCase):
    def setUp(self):
        # Create an empty database object.
        # TEST_DB should be deleted in tearDown, but if the test was interrupted
        # it might not have been.
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
        db = Storage(TEST_DB)

        # Create a bot to test
        self.bot = main.Bot(db, ADMIN_CHANNEL)

    def tearDown(self):
        # Remove our test db for cleanliness
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)

    # Trigger the bot with the given "discord.Message" (must be a Mock).
    # Returns the text of the bot's response, or None if there was no response.
    def send(self, message):
        # The real message.channel.send is an async function. Make it return a
        # future to mimic the real behavior.
        message.channel.send.return_value = empty_future()

        # Trigger the bot.
        l = asyncio.get_event_loop()
        l.run_until_complete(self.bot.on_message(message))

        # Return the response, if there was one.
        if message.channel.send.call_args is not None:
            # The message content is the first argument.
            return message.channel.send.call_args[0][0]

    # Makes sure that all of the string fragments are in the given string text.
    # Is case-insensitive.
    # (Using camel case for consistency with python's testing library.)
    def assertContainsAll(self, text, fragments):
        m = text.lower()
        for f in fragments:
            self.assertIn(f.lower(), m)


class TestCreateAndDeleteCommands(BaseTest):
    # TODO if we ever add more cases, just refactor this into table-driven tests

    def test_save_and_delete(self):
        # Save a command.
        r = self.send(message("{} test I say something now".format(
            main.SAVE_COMMAND), ADMIN_CHANNEL))
        self.assertContainsAll(r, [
            '{}test'.format(main.SUMMONING_KEY),
            "I say something now"])

        # Trigger it, make sure we get the response we want.
        r = self.send(message('{}test'.format(main.SUMMONING_KEY)))
        self.assertEqual(r, "I say something now")

    def test_overwrite(self):
        iterations = 20

        # Save a command and overwrite it multiple times
        for i in range(20):
            self.send(message("{} test {}".format(
                main.SAVE_COMMAND, i), ADMIN_CHANNEL))

        # Trigger it, make sure we get the last response.
        r = self.send(message('{}test'.format(main.SUMMONING_KEY)))
        self.assertEqual(r, "{}".format(iterations-1))

    def test_delete(self):
        # Save a command.
        r = self.send(message("{} test I say something else".format(
            main.SAVE_COMMAND), ADMIN_CHANNEL))
        self.assertIsNotNone(r)

        # Delete it.
        r = self.send(message("{} test".format(
            main.DELETE_COMMAND), ADMIN_CHANNEL))
        self.assertContainsAll(r, ["test"])

        # Make sure the bot does not respond to it
        r = self.send(message("{}test".format(main.SUMMONING_KEY)))
        self.assertIsNone(r)

    def test_save_only_works_in_admin_channel(self):
        # Make sure our save request is ignored.
        r = self.send(
            message("{} test I say something else".format(main.SAVE_COMMAND)))
        self.assertIsNone(r)

    def test_delete_only_works_in_admin_channel(self):
        # Save a command.
        r = self.send(message("{} test I say something".format(
            main.SAVE_COMMAND), ADMIN_CHANNEL))
        self.assertIsNotNone(r)

        # Delete it, but in a non-admin channel.
        r = self.send(message("{} test".format(main.DELETE_COMMAND)))
        self.assertIsNone(r)

        # Make sure the bot still responds
        r = self.send(message("{}test".format(main.SUMMONING_KEY)))
        self.assertEqual(r, "I say something")


class TestIgnoresSelfMessages(BaseTest):
    def test_ignore_self(self):
        # Make a message the bot would normally respond to, but from itself.
        # This test might not work properly if the help command isn't working,
        # but that's ok because the admin test should fail in that case. :P
        m = message(main.HELP_COMMAND, ADMIN_CHANNEL)
        m.author = self.bot.user

        # Make sure we don't get a response.
        self.assertIsNone(self.send(m))


class TestHelp(BaseTest):
    def test_help_works_in_admin_channel(self):
        r = self.send(message(main.HELP_COMMAND, ADMIN_CHANNEL))
        self.assertContainsAll(r, ['Save', 'Use', 'Delete'])

    def test_help_doesnt_work_outside_admin_channel(self):
        self.assertIsNone(self.send(message(main.HELP_COMMAND)))


# We can set this as a return value to make mock functions behave as if they
# are async functions
def empty_future():
    f = asyncio.Future()
    f.set_result(None)
    return f


# Returns a discord message object (really a MagicMock) with the given text as content.
def message(text, channel='arbitrary-channel'):
    m = MagicMock(spec=discord.Message)
    m.author = MagicMock(spec=discord.abc.User)
    m.author.name = "arbitrary user"
    m.channel = MagicMock(spec=discord.TextChannel)

    m.content = text
    m.channel.name = channel
    return m


if __name__ == '__main__':
    unittest.main()
