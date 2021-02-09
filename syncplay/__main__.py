#!/usr/bin/env python3

import logging

from . import ep_server

def main():
    logging.basicConfig(level=logging.INFO)
    ep_server.main()

if __name__ == '__main__':
    main()
