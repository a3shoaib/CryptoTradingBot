# Two strategies
# One that relies on technical indicators (Technical Strategy)
# And one that is based on entering a trade when a certain price level is broken by the current price (Breakout Strategy)
# The two stragies will each inherit from this parent class

import logging
from typing import *

import pandas as pd

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

        # number of candles used to create the rsi
        self._rsi_length = other_params['rsi_length']

        # Get historical data after creating strategy object

    # Relative strength index
    def _rsi(self):
        close_list = []
        for candle in self.candles:
            close_list.append(candle.close)
            # Candles can be represented as time series (each row is a timestamp, and columns represent open, high,
            # low and close price--> use Panda library

        closes = pd.Series(close_list)
        # RSI formula
        # dropna() to remove the first value of the list after the diff method has been applied because the variations
        # can be calculated once you have at least two values. First line of the series won't have any value
        delta = closes.diff().dropna()

        up, down = delta.copy(), delta.copy()
        # Filter rows under 0 to keep the gains, set losses to 0
        up[up < 0] = 0
        down[down > 0] = 0
        # When average gains of up side is calculated, it will take only close price that have
        # increased compared to the close price before

        avg_gains = up.ewm(com=(self._rsi_length - 1), min_periods=self._rsi_length).mean()
        avg_loss = down.abs().ewm(com=(self._rsi_length - 1), min_periods=self._rsi_length).mean()

        rs = avg_gains / avg_loss

        rsi = 100 - 100 / (1 + rs)
        rsi = rsi.round(2)

        # Return candle before current one like macd
        return rsi.iloc[-2]
    def _macd(self) -> Tuple[float, float]:
        # 4 steps to calculate macd (moving average convergance divergance):
        # 1. Fast EMA calculation, 2. Slow EMA calculation, 3. Fast EMA - Slow EMA (subtract), 4. EMA on the result of 3.
        # Slow EMA will use more candles than the fast one -> slow because slope will change more slowly
        # EMA is exponential moving average
        # After each step, obtain a list of EMA's, where each EMA corresponds to each candlestick that has been recorded

        close_list = []
        for candle in self.candles:
            close_list.append(candle.close)
            # Candles can be represented as time series (each row is a timestamp, and columns represent open, high,
            # low and close price--> use Panda library

        closes = pd.Series(close_list)

        ema_fast = closes.ewm(span=self._ema_fast).mean()
        ema_slow = closes.ewm(span=self._ema_slow).mean()

        macd_line = ema_fast - ema_slow
        macd_signal = macd_line.ewm(span=self._ema_signal).mean()

        # -2 and not -1 since -1 represents new candle, not the one that was just finished
        return macd_line.iloc[-2], macd_signal.iloc[-2]

    def _check_signal(self):
        macd_line, macd_signal = self._macd()
        rsi = self._rsi()

        print(rsi, macd_line, macd_signal)

        # Have two indicator's data available
        # Long signal if the contract is oversold (below 30) and macd line is above macd signal line
        if rsi < 30 and macd_line > macd_signal:
            return 1
        # If the contract is overbought and macd line is below macd signal
        elif rsi > 70 and macd_line < macd_signal:
            return -1
        else:
            return 0







class BreakoutStrategy(Strategy):
    def __init__(self, contract: Contract, exchange: str, timeframe: str, balance_pct: float, take_profit: float,
                 stop_loss: float, other_params: Dict):
        super().__init__(contract, exchange, timeframe, balance_pct, take_profit, stop_loss)

        self._min_volume = other_params['min_volume']


    # Volume of a candle is the sum of the trade sizes that occurred during that candle.

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





