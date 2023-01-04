# Two strategies
# One that relies on technical indicators (Technical Strategy)
# And one that is based on entering a trade when a certain price level is broken by the current price (Breakout Strategy)
# The two stragies will each inherit from this parent class

import logging
from typing import *
from models import *

logger = logging.getLogger()

# Timeframe equivalent
TF_EQUIV = {"1m": 60, "5m": 300, "15m": 900, "30m": 1800, "1h": 3600, "4h": 14400}


class Strategy:
    def __init__(self, contract: Contract, exchange: str, timeframe: str, balance_pct: float, take_profit: float,
                 stop_loss: float):

        self.contract = contract
        self.exchange = exchange
        self.tf = timeframe
        self.tf_equiv = TF_EQUIV[timeframe] * 1000
        self.balance_pct = balance_pct
        self.take_profit = take_profit
        self.stop_loss = stop_loss

        self.candles: List[Candle] =[]

    # Method that parses info of the trade and decide to update the current candle
    def parse_trades(self, price: float, size: float, timestamp: int) -> str:
        # 3 cases: 1. Update the same current candle, 2. new candle, 3. new candle + missing candle

        last_candle = self.candles[-1]

        # Same candle (if timestamp of the trade is less than last candle plus the timeframe equivalent -
        # means it is on the same candle)
        if timestamp < last_candle.timestamp + self.tf_equiv:
            # If on the same candle, a consequence of a new trade is that the trade price will now be the last price of
            # the candle until a new one comes or until the end of the candle.
            last_candle.close = price
            last_candle.volume += size

            # Trade price can be the new high or new low so...
            if price > last_candle.high:
                last_candle.high = price
            elif price < last_candle.low:
                last_candle.low = price

            return "same_candle"

        # Missing candle(s)
        elif timestamp >= last_candle.timestamp + 2 * self.tf_equiv:

            missing_candles = int((timestamp - last_candle.timestamp) / self.tf_equiv) - 1

            logger.info("%s missing %s candles for %s %s (%s %s)", self.exchange, missing_candles, self.contract.symbol,
                        self.tf, timestamp, last_candle.timestamp)

            # Add the number of missing candles to the candles list
            for missing in range(missing_candles):
                new_ts = last_candle.timestamp + self.tf_equiv
                candle_info = {'ts': new_ts, 'open': last_candle.close, 'high': last_candle.close,
                               'low': last_candle.close, 'close': last_candle.close, 'volume': 0}
                new_candle = Candle(candle_info, self.tf, "parse_trade")

                self.candles.append(new_candle)

                last_candle = new_candle

            new_ts = last_candle.timestamp + self.tf_equiv
            candle_info = {'ts': new_ts, 'open': price, 'high': price, 'low': price, 'close': price, 'volume': size}
            new_candle = Candle(candle_info, self.tf, "parse_trade")

            self.candles.append(new_candle)

            return "new_candle"


        # New Candle
        elif timestamp >= last_candle.timestamp + self.tf_equiv:
            new_ts = last_candle.timestamp + self.tf_equiv
            candle_info = {'ts': new_ts, 'open': price, 'high': price, 'low': price, 'close': price, 'volume': size}
            new_candle = Candle(candle_info, self.tf, "parse_trade")

            self.candles.append(new_candle)

            logger.info("%s New candle for %s%s", self.exchange,self.contract.symbol, self.tf)

            return "new_candle"

class TechnicalStrategy(Strategy):
    def __init__(self, contract: Contract, exchange: str, timeframe: str, balance_pct: float, take_profit: float,
                 stop_loss: float, other_params: Dict):
        super().__init__(contract, exchange, timeframe, balance_pct, take_profit, stop_loss)

        self._ema_fast = other_params['ema_fast']
        self._ema_slow = other_params['ema_slow']
        self._ema_signal = other_params['ema_signal']

        # Get historical data after creating strategy object


class BreakoutStrategy(Strategy):
    def __init__(self, contract: Contract, exchange: str, timeframe: str, balance_pct: float, take_profit: float,
                 stop_loss: float, other_params: Dict):
        super().__init__(contract, exchange, timeframe, balance_pct, take_profit, stop_loss)

        self._min_volume = other_params['min_volume']

    # Have candlestick data, method checks signal (indicate whether or not to enter a long or short trade or do nothing)
    # For long signal return 1, for short signal -1, and for no signal return 0
    def _check_signal(self) -> int:
        # Only need candles and do not need to compute an indicator
        if self.candles[-1].close > self.candles[-2].high and self.candles[-1].volume > self._min_volume:
            return 1

        elif self.candles[-1].close < self.candles[-2].low and self.candles[-1].volume > self._min_volume:
            return -1

        else:
            return 0

        # if self.candles[-2].high < self.candles[-3].high and self.candles[-2].low > self.candles[-3].low:
        #     if self.candles[-1].close > self.candles[-3].high:
        #         # Upside breakout
        #     elif self.candles[-1].close < self.candles[-3].low:
        #         # Downside breakout





