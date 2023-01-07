# Two strategies
# One that relies on technical indicators (Technical Strategy)
# And one that is based on entering a trade when a certain price level is broken by the current price (Breakout Strategy)
# The two stragies will each inherit from this parent class

import logging
import time
from typing import *

from threading import Timer

import pandas as pd

from models import *

if TYPE_CHECKING:
    from bitmex import BitmexClient
    from binance_futures import BinanceFuturesClient

logger = logging.getLogger()

# Timeframe equivalent
TF_EQUIV = {"1m": 60, "5m": 300, "15m": 900, "30m": 1800, "1h": 3600, "4h": 14400}


class Strategy:
    def __init__(self, client: Union["BitmexClient", "BinanceFuturesClient"], contract: Contract, exchange: str, timeframe: str,
                 balance_pct: float, take_profit: float, stop_loss: float, strat_name):

        self.client = client

        self.contract = contract
        self.exchange = exchange
        self.tf = timeframe
        self.tf_equiv = TF_EQUIV[timeframe] * 1000
        self.balance_pct = balance_pct
        self.take_profit = take_profit
        self.stop_loss = stop_loss

        self.stat_name = strat_name

        self.ongoing_position = False
        self.candles: List[Candle] = []
        self.trades: List[Trade] = []
        self.logs = []

    def _add_log(self, msg: str):
        logger.info("%s", msg)
        self.logs.append({"log": msg, "displayed": False})

    # Method that parses info of the trade coming from the websocket and update the current candle based on the timestamp
    def parse_trades(self, price: float, size: float, timestamp: int) -> str:

        # Calculate differecne of current unix timestamp and timestamp of trade
        timestamp_diff = int(time.time() * 1000) - timestamp
        if timestamp_diff >= 2000:
            logger.warning("%s %s: %s milliseconds of difference between the current time and the trade time",
                           self.exchange, self.contract.symbol, timestamp_diff)

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
            
            #  Check take profit and stop loss
            for trade in self.trades:
                if trade.status == "open" and trade.entry_price is not None:
                    self._check_tp_sl(trade)

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

            logger.info("%s New candle for %s %s", self.exchange, self.contract.symbol, self.tf)

            return "new_candle"

    # Called frequently after an order has been placed until it is filled
    def _check_order_status(self, order_id):
        order_status = self.client.get_order_status(self.contract, order_id)

        # If the request is successful
        if order_status is not None:
            logger.info("%s order status: %s", self.exchange, order_status.status)

            if order_status.status == "filled":
                for trade in self.trades:
                    if trade.entry_id == order_id:
                        trade.entry_price = order_status.avg_price
                        break
                return
        t = Timer(2.0, lambda: self._check_order_status(order_id))
        t.start()

    # Open a Long or Short position based on the signal's result
    def _open_position(self, signal_result: int):

        trade_size = self.client.get_trade_size(self.contract, self.candles[-1].close, self.balance_pct)
        if trade_size is None:
            return
        # Order placement
        order_side = "buy" if signal_result == 1 else "sell"
        positon_side = "long" if signal_result == 1 else "short"


        self._add_log(f"{positon_side.capitalize()} signal on {self.contract.symbol} {self.tf}")

        order_status = self.client.place_order(self.contract, "MARKET", trade_size, order_side)

        # The request was successful and the order is placed
        if order_status is not None:
            self._add_log(f"{order_side.capitalize()} order placed on {self.exchange} | Status: {order_status.status}")

            self.ongoing_position = True

            avg_fill_price = None

            # Case when an order is placed is the order is immediately executed
            if order_status.status == "filled":
                avg_fill_price = order_status.avg_price
            else:
                t = Timer(2.0, lambda: self._check_order_status(order_status.order_id))
                t.start()

            new_trade = Trade({"time": int(time.time() * 1000), "entry_price": avg_fill_price,
                               "contract": self.contract, "strategy": self.stat_name, "side": positon_side,
                               "status": "open", "pnl": 0, "quantity": trade_size, "entry_id": order_status.order_id})

            self.trades.append(new_trade)

    # Check if take profit or stop loss has been reached based on the average price entry
    def _check_tp_sl(self, trade: Trade):
        tp_triggered = False
        sl_triggered = False

        price = self.candles[-1].close

        if trade.side == "long":
            if self.stop_loss is not None:
                if price <= trade.entry_price * (1 - self.stop_loss / 100):
                    sl_triggered = True
            if self.take_profit is not None:
                if price >= trade.entry_price * (1 + self.take_profit / 100):
                    tp_triggered = True

        elif trade.side == "short":
            if self.stop_loss is not None:
                if price >= trade.entry_price * (1 + self.stop_loss / 100):
                    sl_triggered = True
            if self.take_profit is not None:
                if price <= trade.entry_price * (1 - self.take_profit / 100):
                    tp_triggered = True

        if tp_triggered or sl_triggered:
            self._add_log(f"{'Stop loss' if sl_triggered else 'Take profit'} for {self.contract.symbol} {self.tf}")

            order_side = "SELL" if trade.side == "long" else "BUY"
            order_status = self.client.place_order(self.contract, "MARKET", trade.quantity, order_side)

            if order_status is not None:
                self._add_log(f"Exit order on {self.contract.symbol} {self.tf} placed successfully")
                trade.status = "closed"
                self.ongoing_position = False

class TechnicalStrategy(Strategy):
    def __init__(self, client, contract: Contract, exchange: str, timeframe: str, balance_pct: float, take_profit: float,
                 stop_loss: float, other_params: Dict):
        super().__init__(client, contract, exchange, timeframe, balance_pct, take_profit, stop_loss, "Technical")

        self._ema_fast = other_params['ema_fast']
        self._ema_slow = other_params['ema_slow']
        self._ema_signal = other_params['ema_signal']

        # number of candles used to create the rsi
        self._rsi_length = other_params['rsi_length']

        # Get historical data after creating strategy object

    # Calculate relative strength index
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

    # Calculate the MACD and the corresponding signal line
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


    # Calculate technical indicators and compare their values to predefined levels and decide whether to go long, short
    # or do nothing
    def _check_signal(self):
        macd_line, macd_signal = self._macd()
        rsi = self._rsi()

        # Have two indicator's data available
        # Long signal if the contract is oversold (below 30) and macd line is above macd signal line
        if rsi < 30 and macd_line > macd_signal:
            return 1
        # If the contract is overbought and macd line is below macd signal
        elif rsi > 70 and macd_line < macd_signal:
            return -1
        else:
            return 0

    # Call the method when there is a long or short signal and no ongoing trade
    # Close when a stop loss or take profit has been reached but may take some time to do so
    # Called once per candlestick to avoid always calculating indicators
    def check_trade(self, tick_type: str):
        if tick_type == "new candle" and not self.ongoing_position:
            signal_result = self._check_signal()

            if signal_result in [1, -1]:
                self._open_position(signal_result)



class BreakoutStrategy(Strategy):
    def __init__(self, client, contract: Contract, exchange: str, timeframe: str, balance_pct: float, take_profit: float,
                 stop_loss: float, other_params: Dict):
        super().__init__(client, contract, exchange, timeframe, balance_pct, take_profit, stop_loss, "Breakout")

        self._min_volume = other_params['min_volume']


    # Volume of a candle is the sum of the trade sizes that occurred during that candle.

    # Given candlestick data, check signal (indicate whether or not to enter a long or short trade or do nothing)
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

    # Called from websocket _on_message() methods
    def check_trade(self, tick_type: str):
        if not self.ongoing_position:
            signal_result = self._check_signal()

            if signal_result in [1, -1]:
                self._open_position(signal_result)
