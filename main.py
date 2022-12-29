import logging

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

    binance = BinanceFuturesClient("b83cef8f8b8ac8775fdd177d9c6839151464b504411e43c2dec129a4589983f8",
                                   "8ef2a26264aba2b227df4e4f164e1e465bf08557e043743e78e26388d01e1eb0", True)
    bitmex = BitmexClient("fr_40LtGGuXM6HhTc_stDKvj", "YUcJK1qlBY8hRxiMvKyDVRx9JXZBFdHmx-QRDUqfEXPmbO2W", True)

    root = Root(binance, bitmex)
    root.mainloop()
