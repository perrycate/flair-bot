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

# Just to save a couple characters.
SUMMON_KEY = main.SUMMONING_KEY
SAVE = main.SAVE_COMMAND
RANDOM = main.RANDOM_COMMAND
ADD_ALL = main.ADD_ALL_COMMAND
DELETE = main.DELETE_COMMAND
HELP = main.HELP_COMMAND


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
    # When we do that, add test for random-add-all vs random-addall bug.

    def test_save_and_delete(self):
        # Save a command.
        r = self.send(
            message(f"{SAVE} test I say something now", ADMIN_CHANNEL))
        self.assertContainsAll(r, [f"{SUMMON_KEY}test", "I say something now"])

        # Trigger it, make sure we get the response we want.
        r = self.send(message(f"{SUMMON_KEY}test"))
        self.assertEqual(r, "I say something now")

    def test_overwrite(self):
        iterations = 20

        # Save a command and overwrite it multiple times
        for i in range(20):
            self.send(message(f"{SAVE} test {i}", ADMIN_CHANNEL))

        # Trigger it, make sure we get the last response.
        r = self.send(message(f'{SUMMON_KEY}test'))
        self.assertEqual(r, f"{iterations-1}")

    def test_delete(self):
        # Save a command.
        r = self.send(
            message(f"{SAVE} test I say something else", ADMIN_CHANNEL))
        self.assertIsNotNone(r)

        # Delete it.
        r = self.send(message(f"{DELETE} test", ADMIN_CHANNEL))
        self.assertContainsAll(r, ["test"])

        # Make sure the bot does not respond to it
        r = self.send(message(f"{SUMMON_KEY}test"))
        self.assertIsNone(r)

    def test_save_only_works_in_admin_channel(self):
        # Make sure our save request is ignored.
        r = self.send(message(f"{SAVE} test I say something else"))
        self.assertIsNone(r)

    def test_delete_only_works_in_admin_channel(self):
        # Save a command.
        r = self.send(message(f"{SAVE} test I say something", ADMIN_CHANNEL))
        self.assertIsNotNone(r)

        # Delete it, but in a non-admin channel.
        r = self.send(message(f"{DELETE} test"))
        self.assertIsNone(r)

        # Make sure the bot still responds
        r = self.send(message(f"{SUMMON_KEY}test"))
        self.assertEqual(r, "I say something")

    def test_ignores_unset_commands(self):
        # Use of the same "test" command name we use in the other tests is
        # intentional. Consider it a bonus sanity check to make sure we're
        # properly resetting the database between every test.
        self.assertIsNone(self.send(message(f"{SUMMON_KEY}test")))


class TestRandomCommands(BaseTest):
    def test_only_works_in_admin_channel(self):
        # Attempt to trigger the random command in a non-admin channel.
        r = self.send(message(f"{RANDOM} test an arbitrary response."))
        self.assertIsNone(r)

        self.assertIsNone(self.send((message(f"{SUMMON_KEY}test"))))

    def test_responds_randomly(self):
        # Save 3 possible responses to the "test" command.
        self.assertContainsAll(self._save_random(
            "test", "response 1"), ["test", "response 1"])
        self.assertContainsAll(self._save_random(
            "test", "response 2"), ["test", "response 2"])
        self.assertContainsAll(self._save_random(
            "test", "response 3"), ["test", "response 3"])

        # Count the occurrences of each response.
        totals = {"1": 0, "2": 0, "3": 0}
        for i in range(100):
            r = self.send(message(f"{SUMMON_KEY}test"))
            n = r.split()[1]
            totals[n] += 1

        # Check each command got called at least a decent bit.
        # We don't want our assumptions to be too strict since we're (poorly)
        # dealing with randomness.
        self.assertGreater(totals["1"], 10)
        self.assertGreater(totals["2"], 10)
        self.assertGreater(totals["3"], 10)

    def test_add_all(self):
        # Save 4 possible responses to the "test" command.
        self._save_random("test", "1")
        self.assertIsNotNone(
            self.send(message(f"{ADD_ALL} test 2 3\n4", ADMIN_CHANNEL)))

        # Count the occurrences of each response.
        totals = {"1": 0, "2": 0, "3": 0, "4": 0}
        for i in range(100):
            r = self.send(message(f"{SUMMON_KEY}test"))
            totals[r] += 1

        # Check each command got called at least a decent bit.
        # We don't want our assumptions to be too strict since we're (poorly)
        # dealing with randomness.
        self.assertGreater(totals["1"], 10)
        self.assertGreater(totals["2"], 10)
        self.assertGreater(totals["3"], 10)
        self.assertGreater(totals["4"], 10)

    def test_attempt_overwrite_to_single(self):
        # Attempt to overwrite a random command with a single command.
        self._save_random("test", "arbitrary response")
        self._save_random("test", "different arbitrary response")
        r = self.send(
            message(f"{SAVE} test a different arbitrary response", ADMIN_CHANNEL))

        # Should have failed with an error telling the user to delete it first.
        self.assertContainsAll(r, ["Sorry", f"{DELETE} test"])

        # Could be either response
        self.assertIn("arbitrary response",
                      self.send(message(f"{SUMMON_KEY}test")))

    def test_overwrite_to_random(self):
        # Turn a single command into a random command.
        self.send(message(f"{SAVE} test response 1", ADMIN_CHANNEL))
        r = self._save_random("test", "response 2")

        totals = {"1": 0, "2": 0}
        for i in range(100):
            r = self.send(message(f"{SUMMON_KEY}test"))
            n = r.split()[1]
            totals[n] += 1

        self.assertGreater(totals["1"], 10)
        self.assertGreater(totals["2"], 10)

    def test_delete(self):
        self._save_random("test", "arbitrary response 1")
        self._save_random("test", "arbitrary response 2")

        self.assertIsNotNone(
            self.send(message(f"{DELETE} test", ADMIN_CHANNEL)))

        # We should not respond, since we deleted it.
        self.assertIsNone(self.send(message("{}test", main.SUMMONING_KEY)))

    # Yes, I'm that lazy

    def _save_random(self, command, msg):
        return self.send(message(f"{RANDOM} {command} {msg}", ADMIN_CHANNEL))


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
    m.channel = MagicMock(spec=discord.TextChannel)
    m.author = MagicMock(spec=discord.abc.User)

    m.content = text
    m.channel.name = channel
    m.author.name = "arbitrary_user"
    return m


if __name__ == '__main__':
    unittest.main()
