import logging
import requests
import time
import typing

from urllib.parse import urlencode

import hmac
import hashlib

import websocket
import json

import dateutil.parser

import threading
from strategies import TechnicalStrategy, BreakoutStrategy

from models import *

logger = logging.getLogger()


class BitmexClient:
    def __init__(self, public_key: str, secret_key: str, testnet: bool):

        if testnet:
            self._base_url = "https://testnet.bitmex.com"
            self._wss_url = "wss://testnet.bitmex.com/realtime"
        else:
            self._base_url = "https://www.bitmex.com"
            self._wss_url = "wss://www.bitmex.com/realtime"

        self._public_key = public_key
        self._secret_key = secret_key

        self._ws = None

        self.contracts = self.get_contracts()
        self.balances = self.get_balances()

        self.prices = dict()

        # After the strategy object is created and historical candles have been fetched, store strategies in each connector
        self.strategies: typing.Dict[int, typing.Union[TechnicalStrategy, BreakoutStrategy]] = dict()

        self.logs = []

        t = threading.Thread(target=self._start_ws)
        t.start()

        logger.info("Bitmex Client successfully initialized")

    def _add_log(self, msg: str):
        logger.info("%s", msg)
        self.logs.append({"log": msg, "displayed": False})

    def _generate_signature(self, method: str, endpoint: str, expires: str, data: typing.Dict) -> str:

        message = method + endpoint + "?" + urlencode(data) + expires if len(data) > 0 else method + endpoint + expires
        return hmac.new(self._secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()

    def _make_request(self, method: str, endpoint: str, data: typing.Dict):

        headers = dict()
        expires = str(int(time.time()) + 5)
        headers['api-expires'] = expires
        headers['api-key'] = self._public_key
        headers['api-signature'] = self._generate_signature(method, endpoint, expires, data)

        if method == "GET":
            try:
                response = requests.get(self._base_url + endpoint, params=data, headers=headers)
            except Exception as e:
                logger.error("Connection error while making %s request to %s: %s", method, endpoint, e)
                return None

        elif method == "POST":
            try:
                response = requests.post(self._base_url + endpoint, params=data, headers=headers)
            except Exception as e:
                logger.error("Connection error while making %s request to %s: %s", method, endpoint, e)
                return None

        elif method == "DELETE":
            try:
                response = requests.delete(self._base_url + endpoint, params=data, headers=headers)
            except Exception as e:
                logger.error("Connection error while making %s request to %s: %s", method, endpoint, e)
                return None
        else:
            raise ValueError ()

        if response.status_code == 200:
            return response.json()
        else:
            logger.error("Error while making %s request to %s: %s (error code %s)",
                         method, endpoint, response.json(), response.status_code)
            return None

    def get_contracts(self) -> typing.Dict[str, Contract]:

        instruments = self._make_request("GET", "/api/v1/instrument/active", dict())

        contracts = dict()

        if instruments is not None:
            for s in instruments:
                contracts[s['symbol']] = Contract(s, "bitmex")

        return contracts

    def get_balances(self) -> typing.Dict[str, Balance]:
        data = dict()
        data['currency'] = "all"

        margin_data = self._make_request("GET", "/api/v1/user/margin", data)

        balances = dict()

        if margin_data is not None:
            for a in margin_data:
                balances[a['currency']] = Balance(a, "bitmex")

        return balances

    def get_historical_candles(self, contract: Contract, timeframe: str) -> typing.List[Candle]:
        data = dict()

        data['symbol'] = contract.symbol
        data['partial'] = True
        data['binSize'] = timeframe
        data['count'] = 500
        data['reverse'] = True

        raw_candles = self._make_request("GET", "/api/v1/trade/bucketed", data)

        candles = []

        if raw_candles is not None:
            for c in reversed(raw_candles):
                candles.append(Candle(c, timeframe, "bitmex"))

        return candles

    def place_order(self, contract: Contract, order_type: str, quantity: int, side: str, price=None, tif=None) -> OrderStatus:
        data = {
            'symbol': contract.symbol,
            'side': side.capitalize(),
            'orderQty': round(quantity / contract.lot_size) * contract.lot_size,
            'ordType': order_type.capitalize()
        }

        if price is not None:
            data['price'] = round(round(price / contract.tick_size) * contract.tick_size, 8)

        if tif is not None:
            data['timeInForce'] = tif

        order_status = self._make_request("POST", "/api/v1/order", data)

        if order_status is not None:
            order_status = OrderStatus(order_status, "bitmex")

        return order_status

    def cancel_order(self, order_id: str) -> OrderStatus:
        data = dict()
        data['orderID'] = order_id

        order_status = self._make_request("DELETE", "/api/v1/order", data)

        if order_status is not None:
            order_status = OrderStatus(order_status[0], "bitmex")

        return order_status

    def get_order_status(self, contract: Contract, order_id: str) -> OrderStatus:

        data = dict()
        data['symbol'] = contract.symbol
        data['reverse'] = True

        order_status = self._make_request("GET", "/api/v1/order", data)

        if order_status is not None:
            # order_status is a list of order status of order dictionaries related to the symbol requested above
            # and looking for a specific order ID
            for order in order_status:
                if order['orderID'] == order_id:
                    return OrderStatus(order, "bitmex")

    def _start_ws(self):
        # Starts a connection and assigns which function is called when an event occurs
        self._ws = websocket.WebSocketApp(self._wss_url, on_open=self._on_open, on_close=self._on_close,
                                         on_error=self._on_error, on_message=self._on_message)

# Reconnect websocket connection if disconnected
        while True:
            try:
                self._ws.run_forever()
            except Exception as e:
                logger.error("Bitmex error in run_forever() method: %s", e)
            time.sleep(2)

    def _on_open(self, ws):
        logger.info("Bitmex connection opened")

        self.subscribe_channel("instrument")

        # Add trades data to subscriptions
        self.subscribe_channel("trade")

    def _on_close(self, ws):
        logger.warning("Bitmex Websocket connection closed")

    def _on_error(self, ws, msg: str):
        logger.error("Bitmex connection error: %s", msg)

    def _on_message(self, ws, msg: str):

        data = json.loads(msg)

        if "table" in data:
            if data['table'] == "instrument":

                for d in data['data']:

                    symbol = d['symbol']

                    if symbol not in self.prices:
                        self.prices[symbol] = {'bid': None, 'ask': None}

                    if 'bidPrice' in d:
                        self.prices[symbol]['bid'] = d['bidPrice']
                    if 'askPrice' in d:
                        self.prices[symbol]['ask'] = d['askPrice']

                    # PNL Calculation
                    try:
                        for b_index, strat in self.strategies.items():
                            if strat.contract.symbol == symbol:
                                for trade in strat.trades:
                                    if trade.status == "open" and trade.entry_price is not None:

                                        if trade.side == "long":
                                            price = self.prices[symbol]['bid']
                                        else:
                                            price = self.prices[symbol]['ask']
                                        multiplier = trade.contract.multiplier

                                        # From documentation
                                        if trade.contract.inverse:
                                            if trade.side == "long":
                                                trade.pnl = (
                                                                        1 / trade.entry_price - 1 / price) * multiplier * trade.quantity
                                            elif trade.side == "short":
                                                trade.pnl = (
                                                                        1 / price - 1 / trade.entry_price) * multiplier * trade.quantity
                                        else:
                                            if trade.side == "long":
                                                trade.pnl = (price - trade.entry_price) * multiplier * trade.quantity
                                            elif trade.side == "short":
                                                trade.pnl = (trade.entry_price - price) * multiplier * trade.quantity
                    except RuntimeError as e:
                        logger.error("Error while looping through the Bitmex strategies: %s", e)

            if data['table'] == "trade":

                for d in data['data']:

                    symbol = d['symbol']

                    # Timestamp represents time of the trade in this case
                    ts = int(dateutil.parser.isoparse(d['timestamp']).timestamp() * 1000)

                    # Loop through strategies
                    for key, strat in self.strategies.items():
                        if strat.contract.symbol == symbol:
                            res = strat.parse_trades(float(d['price']), float(d['size']), ts)
                            strat.check_trade(res)


    # Class method to subscribe to a channel to recieve market data
    def subscribe_channel(self, topic: str):
        data = dict()
        data['op'] = "subscribe"
        data['args'] = []
        data['args'].append(topic)

        try:
            self._ws.send(json.dumps(data))
        except Exception as e:
            logger.error("Websocket error while subscribing to %s: %s", topic, e)

    def get_trade_size(self, contract: Contract, price: float, balance_pct: float):

        balance = self.get_balances()
        if balance is not None:
            if 'XBt' in balance:
                balance = balance['XBt'].wallet_balance
            else:
                return None
        else:
            return None

        xbt_size = balance * balance_pct / 100

        # Number of contracts to trade

        # From bitmex documentation
        if contract.inverse:
            contracts_number = xbt_size / (contract.multiplier / price)
        elif contract.quanto:
            contracts_number = xbt_size / (contract.multiplier * price)
        # Case of linear futures, same calculation as quanto
        else:
            contracts_number = xbt_size / (contract.multiplier * price)

        logger.info("Bitmex current XBT balance = %s, contracts number = %s", balance, contracts_number)

        return int(contracts_number)

