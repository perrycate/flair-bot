#!/usr/bin/env python3
import asyncio
import io
import os
import time
import unittest
from typing import Optional, Tuple
from unittest.mock import MagicMock, Mock

import discord

import cmd_setter
from storage import CmdStore

# Make sure this doesn't coincide with a sqlite db file that's really used.
TEST_DB = 'test_db_please_ignore.db'

ADMIN = 'admin-channel'

# Just to save a couple characters.
SUMMON_KEY = cmd_setter.SUMMONING_KEY
SAVE = cmd_setter.SAVE_COMMAND
RANDOM = cmd_setter.RANDOM_COMMAND
ADD_ALL = cmd_setter.ADD_ALL_COMMAND
LIST = cmd_setter.LIST_COMMAND
DELETE = cmd_setter.DELETE_COMMAND
HELP = cmd_setter.HELP_COMMAND

# TODO Testing flairs
# make self.get_guild(_) return an object that returns an object with id when get_role(id) is called
# Make helper function that returns all added roles (all times payload.member.add_roles(<objects with id>) was called)


# Contains common setup, teardown, helper methods to be used by test cases
# testing the CommandSetter Cog.
class CommandSetterTest(unittest.TestCase):
    def setUp(self):
        # Create an empty database object.
        # TEST_DB should be deleted in tearDown, but if the test was interrupted
        # it might not have been.
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
        db = CmdStore(TEST_DB)

        # Create a bot to test
        self.test_account = MagicMock(spec=discord.ClientUser)
        self.bot = MagicMock(wraps=cmd_setter.CommandSetter(
            self.test_account, db, ADMIN))

    def tearDown(self):
        # Remove our test db for cleanliness
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)

    # Sends the given message, then checks that the bot responds appropriately
    # expected_resp can be a:
    # 1. string (checks for an exact match),
    # 2. list of strings (checks that the response contains each)
    # 3. None (checks that there is not a response)
    #
    # In case #2, an empty list will succeed iff the response is not None.
    def send_check(self, message, expected_resp):
        resp, _ = self.send(message)

        if expected_resp is None:
            self.assertIsNone(expected_resp)
        elif isinstance(expected_resp, str):
            self.assertEqual(resp, expected_resp)
        elif isinstance(expected_resp, list):
            self.assertIsNotNone(
                resp,
                msg=
                f"Got no response to message with content '{message.content}'")
            self.assertContainsAll(resp, expected_resp)
        else:
            raise TypeError(f"Illegal expected response of type" /
                            "{type(expected_resp)}. Must be a string, list, or None.")

    # Triggers the bot with the given "discord.Message" (must be a Mock).
    # Returns the text of the bot's response, or None if there was no response.
    def send(self, message) -> Tuple[Optional[str], Optional[discord.File]]:
        # The real message.channel.send is an async function. Make it return a
        # future to mimic the real behavior.
        message.channel.send.return_value = empty_future()

        # Trigger the bot.
        l = asyncio.get_event_loop()
        l.run_until_complete(self.bot.on_message(message))

        # Return the response, if there was one.
        # There should be no more than 1 response.
        self.assertLessEqual(message.channel.send.call_count, 1)
        content = None
        image = None
        if message.channel.send.call_args is not None:
            # The message content is the first argument.
            content = message.channel.send.call_args.args[0]
            image = message.channel.send.call_args.kwargs.get("file", None)

        return content, image

    # Makes sure that all of the string fragments are in the given string text.
    # Is case-insensitive.
    # (Using camel case for consistency with python's testing library.)
    def assertContainsAll(self, text, fragments):
        self.assertIsNotNone(text)
        m = text.lower()
        for f in fragments:
            self.assertIn(f.lower(), m)


class TestCreateAndDeleteCommands(CommandSetterTest):
    # TODO refactor this into more table-driven tests
    # TODO add test for random-add-all vs random-addall bug.

    def test_save_and_delete(self):
        # Save a command.
        self.send_check(message(f"{SAVE} test I say something now", ADMIN),
                        [f"{SUMMON_KEY}test", "I say something now"])

        # Trigger it, make sure we get the response we want.
        self.send_check(message(f"{SUMMON_KEY}test"), "I say something now")

    def test_overwrite(self):
        iterations = 20

        # Save a command and overwrite it multiple times
        for i in range(iterations):
            self.send_check(message(f"{SAVE} test {i}", ADMIN), [])

        # Trigger it, make sure we get the last response.
        self.send_check(message(f'{SUMMON_KEY}test'), f"{iterations-1}")

    def test_delete(self):
        # Save a command.
        self.send_check(
            message(f"{SAVE} test I say something else", ADMIN), [])

        # Delete it.
        self.send_check(message(f"{DELETE} test", ADMIN), ["test"])

        # Make sure the bot does not respond to it
        self.send_check(message(f"{SUMMON_KEY}test"), None)

    def test_save_only_works_in_admin_channel(self):
        # Make sure our save request is ignored.
        self.send_check(message(f"{SAVE} test I say something else"), None)

    def test_delete_only_works_in_admin_channel(self):
        # Save a command.
        self.send_check(message(f"{SAVE} test I say something", ADMIN), [])

        # Delete it, but in a non-admin channel.
        self.send_check(message(f"{DELETE} test"), None)

        # Make sure the bot still responds
        self.send_check(message(f"{SUMMON_KEY}test"), "I say something")

    def test_rejects_invalid_input(self):
        # No content or attachment.
        self.send_check(message(f"{SAVE} test", ADMIN),
                        ["format", "keyword", "content"])

        # No keyword.
        self.send_check(message(f"{SAVE}", ADMIN),
                        ["format", "keyword", "content"])

    def test_accepts_attachment_and_no_content(self):
        # No content, but has attachment.
        msg = message(f"{SAVE} test", ADMIN)
        image = b"533190190"  # Pretend this sequence of bytes is an image lol.
        image_name = "image.png"
        _attach_image(msg, image, image_name)

        self.send_check(msg, [f"{SUMMON_KEY}test", "image"])

        # Should get the image back when the new command is triggered.
        _, returned_image = self.send(message(f"{SUMMON_KEY}test"))
        self.assertEqual(image, returned_image.fp.read())
        self.assertEqual(image_name, returned_image.filename)

    def test_accepts_attachment_and_text(self):
        # No content, but has attachment.
        msg = message(f"{SAVE} test TEXT", ADMIN)
        image = b"533190190"  # Pretend this sequence of bytes is an image lol.
        image_name = "video.mp4"
        _attach_image(msg, image, image_name)

        self.send_check(msg, [f"{SUMMON_KEY}test", "TEXT", "image"])

        # Should get the image back when the new command is triggered.
        text, returned_image = self.send(message(f"{SUMMON_KEY}test"))
        self.assertEqual(text, "TEXT")
        self.assertEqual(image, returned_image.fp.read())
        self.assertEqual(image_name, returned_image.filename)

    def test_ignores_unset_commands(self):
        # Use of the same "test" command name we use in the other tests is
        # intentional. Consider it a bonus sanity check to make sure we're
        # properly resetting the database between every test.
        self.send_check(message(f"{SUMMON_KEY}test"), None)


class TestListCommands(CommandSetterTest):
    def test_lists_commands(self):
        self.send_check(message(f"{SAVE} test1 this is a test", ADMIN), [])
        self.send_check(message(f"{SAVE} test2 this is a test", ADMIN), [])

        # Should have both added commands.
        self.send_check(message(f"{LIST}", ADMIN), ["test1", "test2"])

    def test_does_not_list_deleted_commands(self):
        self.send_check(message(f"{SAVE} test1 this is a test", ADMIN), [])
        self.send_check(message(f"{SAVE} test2 this is a test", ADMIN), [])

        # Delete one of the commands.
        self.send_check(message(f"{DELETE} test2", ADMIN), [])

        # Should still have the first command.
        self.send_check(message(f"{LIST}", ADMIN), ["test1"])

        # Should not list the second command, since it was deleted.
        r, _ = self.send(message(f"{LIST}", ADMIN))
        self.assertTrue("test2" not in r)

    def test_does_not_list_random_commands_multiple_times(self):
        self.send_check(message(f"{RANDOM} test1 this is a test", ADMIN), [])
        self.send_check(
            message(f"{RANDOM} test1 this is another test", ADMIN), [])

        # Should only include "test1" once.
        r, _ = self.send(message(f"{LIST}", ADMIN))
        self.assertEqual(r.count("test1"), 1)

    # TODO think up a decent way to test splitting up the response if too many
    # commands have been added. Right now the effort doesn't seem worth it.


class TestRandomCommands(CommandSetterTest):
    def test_only_works_in_admin_channel(self):
        # Attempt to trigger the random command in a non-admin channel.
        self.send_check(message(f"{RANDOM} test an arbitrary response."), None)
        self.send_check(message(f"{SUMMON_KEY}test"), None)

    def test_responds_randomly(self):
        # Save 3 possible responses to the "test" command.
        self.send_check(
            message(f"{RANDOM} test response 1", ADMIN),
            ["test", "response 1"])
        self.send_check(
            message(f"{RANDOM} test response 2", ADMIN),
            ["test", "response 2"])
        self.send_check(
            message(f"{RANDOM} test response 3", ADMIN),
            ["test", "response 3"])

        # Count the occurrences of each response.
        totals = {"1": 0, "2": 0, "3": 0}
        for i in range(100):
            r, _ = self.send(message(f"{SUMMON_KEY}test"))
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
        self.send_check(message(f"{RANDOM} test 1", ADMIN), [])
        self.send_check(message(f"{ADD_ALL} test 2 3\n4", ADMIN), [])

        # Count the occurrences of each response.
        totals = {"1": 0, "2": 0, "3": 0, "4": 0}
        for i in range(100):
            r, _ = self.send(message(f"{SUMMON_KEY}test"))
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
        self.send_check(message(f"{RANDOM} test a response", ADMIN), [])
        self.send_check(message(f"{RANDOM} test another response", ADMIN), [])

        # Attempt to overwrite a random command with a single command.
        # Should fail with an error telling the user to delete it first.
        self.send_check(
            message(f"{SAVE} test a different thingy.", ADMIN),
            ["Sorry", f"{DELETE} test"])

        # Could be either response
        self.send_check(message(f"{SUMMON_KEY}test"), ["response"])

    def test_overwrite_to_random(self):
        # Turn a single command into a random command.
        self.send_check(message(f"{SAVE} test response 1", ADMIN), [])
        self.send_check(message(f"{RANDOM} test response 2", ADMIN), [])

        totals = {"1": 0, "2": 0}
        for i in range(100):
            r, _ = self.send(message(f"{SUMMON_KEY}test"))
            n = r.split()[1]
            totals[n] += 1

        self.assertGreater(totals["1"], 10)
        self.assertGreater(totals["2"], 10)

    def test_delete(self):
        self.send_check(message(f"{RANDOM} arbitrary response 1", ADMIN), [])
        self.send_check(message(f"{RANDOM} arbitrary response 2", ADMIN), [])

        self.send_check(message(f"{DELETE} test", ADMIN), [])

        # We should not respond, since we deleted it.
        self.send_check(message("{}test", cmd_setter.SUMMONING_KEY), None)


class TestIgnoresSelfMessages(CommandSetterTest):
    def test_ignore_self(self):
        # Make a message the bot would normally respond to, but from itself.
        # This test might not work properly if the help command isn't working,
        # but that's ok because the admin test should fail in that case. :P
        m = message(cmd_setter.HELP_COMMAND, ADMIN)
        m.author = self.test_account

        # Make sure we don't get a response.
        self.send_check(m, None)


class TestHelp(CommandSetterTest):
    def test_help_works_in_admin_channel(self):
        r, _ = self.send(message(cmd_setter.HELP_COMMAND, ADMIN))
        self.assertContainsAll(r, ['Save', 'Use', 'Delete'])

    def test_help_doesnt_work_outside_admin_channel(self):
        content, image = self.send(message(cmd_setter.HELP_COMMAND))
        self.assertIsNone(content)
        self.assertIsNone(image)


# We can set this as a return value to make mock functions behave as if they
# are async functions
def empty_future():
    return future(None)


def future(value):
    f = asyncio.Future()
    f.set_result(value)
    return f


# Returns a discord message object (really a MagicMock) with the given text as content.
def message(text, channel='arbitrary-channel'):
    m = MagicMock(spec=discord.Message)
    m.channel = MagicMock(spec=discord.TextChannel)
    m.author = Mock(spec=discord.Member)

    m.content = text
    m.channel.name = channel
    m.author.name = "arbitrary_user"
    return m


# Wraps image in a "discord.Attachment", and adds it to the "discord.Message" (actually mocks).
def _attach_image(msg: discord.Message, image: bytes, filename: str='file.png'):
    file_obj = discord.File(io.BytesIO(image), filename)

    attachment = MagicMock(spec=discord.Attachment)
    attachment.to_file = MagicMock(return_value=future(file_obj))

    msg.attachments = [attachment]


if __name__ == '__main__':
    unittest.main()
