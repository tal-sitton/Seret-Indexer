import logging
import os

import requests

import edb_main
import seret_main
from db import DB

headers = {
    'User-Agent': 'Mozilla/5.0',
}


def setup_logger():
    # log to file
    file_handler = logging.FileHandler('log.log', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    # log to console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                        handlers=[file_handler, console_handler], encoding='utf-8')


def main():
    db = DB(logging.root)
    setup_logger()
    db.create_index()
    session = requests.Session()
    session.headers = headers
    if os.environ.get('CI'):  # Only set proxy in CI
        session.proxies = {'http': "127.0.0.1:8118", 'https': "127.0.0.1:8118"}
    seret_main.main(db, session)
    edb_main.main(db, session)


if __name__ == '__main__':
    main()
