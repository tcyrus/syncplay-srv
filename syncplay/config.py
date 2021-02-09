from argparse import ArgumentParser
import os
import sys


from syncplay import constants
from syncplay.messages import getMessage


class ConfigGetter:
    @staticmethod
    def getConfig():
        argparser = ConfigGetter._prepareArgParser()
        args = argparser.parse_args()

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

    @staticmethod
    def _prepareArgParser() -> ArgumentParser:
        argparser = ArgumentParser(
            description=getMessage("server-argument-description"),
            epilog=getMessage("server-argument-epilog")
        )
        argparser.add_argument('--port', metavar='port', type=str, nargs='?', help=getMessage("server-port-argument"))
        argparser.add_argument('--password', metavar='password', type=str, nargs='?', help=getMessage("server-password-argument"))
        argparser.add_argument('--isolate-rooms', action='store_true', help=getMessage("server-isolate-room-argument"))
        argparser.add_argument('--disable-ready', action='store_true', help=getMessage("server-disable-ready-argument"))
        argparser.add_argument('--disable-chat', action='store_true', help=getMessage("server-chat-argument"))
        argparser.add_argument('--salt', metavar='salt', type=str, nargs='?', help=getMessage("server-salt-argument"))
        argparser.add_argument('--motd-file', metavar='file', type=str, nargs='?', help=getMessage("server-motd-argument"))
        argparser.add_argument('--max-chat-message-length', metavar='maxChatMessageLength', type=int, nargs='?', help=getMessage("server-chat-maxchars-argument").format(constants.MAX_CHAT_MESSAGE_LENGTH))
        argparser.add_argument('--max-username-length', metavar='maxUsernameLength', type=int, nargs='?', help=getMessage("server-maxusernamelength-argument").format(constants.MAX_USERNAME_LENGTH))
        argparser.add_argument('--stats-db-file', metavar='file', type=str, nargs='?', help=getMessage("server-stats-db-file-argument"))
        argparser.add_argument('--tls', metavar='path', type=str, nargs='?', help=getMessage("server-startTLS-argument"))
        return argparser
