import logging
import os

from binance_futures import BinanceFuturesClient
from bitmex import BitmexClient
from root_component import Root


logger = logging.getLogger()

logger.setLevel(logging.INFO)

stream_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)s :: %(message)s')
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.INFO)

file_handler = logging.FileHandler('info.log')
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)

logger.addHandler(stream_handler)
logger.addHandler(file_handler)


if __name__ == '__main__':
    # Enter public and private keys
    binance = BinanceFuturesClient(os.environ.get('public_key_binance'),
                                   os.environ.get('private_key_binance', True))
    bitmex = BitmexClient(os.environ.get('public_key_bitmex'), os.environ.get('private_key_bitmex', True))

    root = Root(binance, bitmex)
    root.mainloop()



