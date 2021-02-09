import logging

from twisted.internet import reactor

from twisted.internet.endpoints import TCP4ServerEndpoint, TCP6ServerEndpoint

from syncplay.config import ConfigGetter
from syncplay.server import SyncFactory


def main():
    args = ConfigGetter.getConfig()

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

    endpoint6 = TCP6ServerEndpoint(reactor, int(args.port))

    def failed6(e):
        logging.debug(e)
        logging.error("IPv6 listening failed.")

    endpoint6.listen(factory).addErrback(failed6)

    endpoint4 = TCP4ServerEndpoint(reactor, int(args.port))

    def failed4(e):
        logging.debug(e)
        logging.error("IPv4 listening failed.")

    endpoint4.listen(factory).addErrback(failed4)

    reactor.run()


if __name__ == "__main__":
    main()
