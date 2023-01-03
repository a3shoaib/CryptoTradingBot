# Two strategies
# One that relies on technical indicators (Technical Strategy)
# And one that is based on entering a trade when a certain price level is broken by the current price (Breakout Strategy)
# The two stragies will each inherit from this parent class

import logging
import typing
from typing import *
from models import *

logger = logging.getLogger()


class Strategy:
    def __init__(self, contract: Contract, exchange: str, timeframe: str, balance_pct: float, take_profit: float,
                 stop_loss: float):

        self.contract = contract
        self.exchange = exchange
        self.tf = timeframe
        self.balance_pct = balance_pct
        self.take_profit = take_profit
        self.stop_loss = stop_loss

        self.candles: List[Candle] =[]

class TechnicalStrategy(Strategy):
    def __init__(self, contract: Contract, exchange: str, timeframe: str, balance_pct: float, take_profit: float,
                 stop_loss: float, other_params: typing.Dict):
        super().__init__(contract, exchange, timeframe, balance_pct, take_profit, stop_loss)

        self._ema_fast = other_params['ema_fast']
        self._ema_slow = other_params['ema_slow']
        self._ema_signal = other_params['ema_signal']

        # Get historical data after creating strategy object


class BreakoutStrategy(Strategy):
    def __init__(self, contract: Contract, exchange: str, timeframe: str, balance_pct: float, take_profit: float,
                 stop_loss: float, other_params: typing.Dict):
        super().__init__(contract, exchange, timeframe, balance_pct, take_profit, stop_loss)

        self._min_volume = other_params['min_volume']

