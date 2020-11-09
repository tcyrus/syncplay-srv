#!/usr/bin/env python3
# coding:utf8

import asyncio
import logging

# import uvloop

from syncplay import ep_server

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    # uvloop.install()
    asyncio.run(ep_server.main())
