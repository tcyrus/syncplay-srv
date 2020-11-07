import argparse
import os
import sys
import logging
import asyncio

from syncplay import constants
from syncplay.messages import getMessage
from syncplay.server import SyncFactory


class ConfigurationGetter:
    def getConfiguration(self):
        self._prepareArgParser()
        args = self._argparser.parse_args()

        if args.isolate_rooms is False:
            tmp = os.environ.get('SYNCPLAY_ISOLATE_ROOMS', '').lower()
            args.isolate_rooms = (tmp == 'true')
        if args.disable_ready is False:
            tmp = os.environ.get('SYNCPLAY_DISABLE_READY', '').lower()
            args.disable_ready = (tmp == 'true')
        if args.disable_chat is False:
            tmp = os.environ.get('SYNCPLAY_DISABLE_CHAT', '').lower()
            args.disable_chat = (tmp == 'true')

        if args.port is None:
            args.port = os.environ.get('SYNCPLAY_PORT', constants.DEFAULT_PORT)
        if args.password is None:
            args.password = os.environ.get('SYNCPLAY_PASSWORD')
        if args.salt is None:
            args.salt = os.environ.get('SYNCPLAY_SALT')
        if args.motd_file is None:
            args.motd_file = os.environ.get('SYNCPLAY_MOTD_FILE')
        if args.stats_db_file is None:
            args.stats_db_file = os.environ.get('SYNCPLAY_STATS_DB_FILE')
        if args.tls is None:
            args.tls = os.environ.get('SYNCPLAY_TLS_PATH')

        if args.max_chat_message_length is None:
            tmp = os.environ.get('SYNCPLAY_MAX_CHAT_MSG_LEN')
            if tmp is not None and tmp.isdigit():
                args.max_chat_message_length = int(tmp)
            else:
                args.max_chat_message_length = constants.MAX_CHAT_MESSAGE_LENGTH
        if args.max_username_length is None:
            tmp = os.environ.get('SYNCPLAY_MAX_UNAME_LEN')
            if tmp is not None and tmp.isdigit():
                args.max_username_length = int(tmp)
            else:
                args.max_username_length = constants.MAX_USERNAME_LENGTH

        return args

    def _prepareArgParser(self) -> None:
        self._argparser = argparse.ArgumentParser(
            description=getMessage("server-argument-description"),
            epilog=getMessage("server-argument-epilog")
        )
        self._argparser.add_argument('--port', metavar='port', type=str, nargs='?', help=getMessage("server-port-argument"))
        self._argparser.add_argument('--password', metavar='password', type=str, nargs='?', help=getMessage("server-password-argument"))
        self._argparser.add_argument('--isolate-rooms', action='store_true', help=getMessage("server-isolate-room-argument"))
        self._argparser.add_argument('--disable-ready', action='store_true', help=getMessage("server-disable-ready-argument"))
        self._argparser.add_argument('--disable-chat', action='store_true', help=getMessage("server-chat-argument"))
        self._argparser.add_argument('--salt', metavar='salt', type=str, nargs='?', help=getMessage("server-salt-argument"))
        self._argparser.add_argument('--motd-file', metavar='file', type=str, nargs='?', help=getMessage("server-motd-argument"))
        self._argparser.add_argument('--max-chat-message-length', metavar='maxChatMessageLength', type=int, nargs='?', help=getMessage("server-chat-maxchars-argument").format(constants.MAX_CHAT_MESSAGE_LENGTH))
        self._argparser.add_argument('--max-username-length', metavar='maxUsernameLength', type=int, nargs='?', help=getMessage("server-maxusernamelength-argument").format(constants.MAX_USERNAME_LENGTH))
        self._argparser.add_argument('--stats-db-file', metavar='file', type=str, nargs='?', help=getMessage("server-stats-db-file-argument"))
        self._argparser.add_argument('--tls', metavar='path', type=str, nargs='?', help=getMessage("server-startTLS-argument"))


async def main():
    argsGetter = ConfigurationGetter()
    args = argsGetter.getConfiguration()
    factory = SyncFactory(
        args.port,
        args.password,
        args.motd_file,
        args.isolate_rooms,
        args.salt,
        args.disable_ready,
        args.disable_chat,
        args.max_chat_message_length,
        args.max_username_length,
        args.stats_db_file,
        args.tls
    )

    server = await factory.buildProtocol()

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

