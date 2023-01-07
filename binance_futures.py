import logging
import requests
import time
import typing

from urllib.parse import urlencode

import hmac
import hashlib

import websocket
import json

import threading

from models import *

from strategies import TechnicalStrategy, BreakoutStrategy

logger = logging.getLogger()


class BinanceFuturesClient:
    def __init__(self, public_key: str, secret_key: str, testnet: bool):
        if testnet:
            self._base_url = "https://testnet.binancefuture.com"
            self._wss_url = "wss://stream.binancefuture.com/ws"
        else:
            self._base_url = "https://fapi.binance.com"
            self._wss_url = "wss://fstream.binance.com/ws"

        self._public_key = public_key
        self._secret_key = secret_key

        self._headers = {'X-MBX-APIKEY': self._public_key}

        # Instance variable containing dictionary of contracts and balances
        self.contracts = self.get_contracts()
        self.balances = self.get_balances()

        self.prices = dict()

        # After the strategy object is created and historical candles have been fetched, store strategies in each connector
        self.strategies: typing.Dict[int, typing.Union[TechnicalStrategy, BreakoutStrategy]] = dict()

        self.logs = []

        self._ws_id = 1
        self.ws: websocket.WebSocketApp
        self.reconnect = True

        t = threading.Thread(target=self._start_ws)
        t.start()

        logger.info("Binance Futures Client successfully initialized")

    # Add a log to the list in order for it to be picked by the update_ui() method of the root component
    def _add_log(self, msg: str):
        logger.info("%s", msg)
        self.logs.append({"log": msg, "displayed": False})

    # Generate a signature with the HMAC-256 algorithm
    def _generate_signature(self, data: typing.Dict) -> str:
        return hmac.new(self._secret_key.encode(), urlencode(data).encode(), hashlib.sha256).hexdigest()

    # Handle requests to the REST API and errors
    def _make_request(self, method: str, endpoint: str, data: typing.Dict):
        if method == "GET":
            try:
                response = requests.get(self._base_url + endpoint, params=data, headers=self._headers)
            except Exception as e:
                logger.error("Connection error while making %s request to %s: %s", method, endpoint, e)
                return None

        elif method == "POST":
            try:
                response = requests.post(self._base_url + endpoint, params=data, headers=self._headers)
            except Exception as e:
                logger.error("Connection error while making %s request to %s: %s", method, endpoint, e)
                return None

        elif method == "DELETE":
            try:
                response = requests.delete(self._base_url + endpoint, params=data, headers=self._headers)
            except Exception as e:
                logger.error("Connection error while making %s request to %s: %s", method, endpoint, e)
                return None
        else:
            raise ValueError()

        if response.status_code == 200:
            return response.json()
        else:
            logger.error("Error while making %s request to %s: %s (error code %s)",
                         method, endpoint, response.json(), response.status_code)
            return None

    #  Get list of symbols (contracts) on the exchange in order to display it on the OptionMenus in the UI
    def get_contracts(self) -> typing.Dict[str, Contract]:
        exchange_info = self._make_request("GET", "/fapi/v1/exchangeInfo", dict())

        contracts = dict()

        if exchange_info is not None:
            for contract_data in exchange_info['symbols']:
                if contract_data['marginAsset'] != "BUSD":
                    contracts[contract_data['symbol']] = Contract(contract_data, "binance")

        return contracts

    # Get list of the most recent candlesticks for any given symbol (contract) and interval
    def get_historical_candles(self, contract: Contract, interval: str) -> typing.List[Candle]:
        data = {
        'symbol': contract.symbol,
        'interval': interval,
        'limit': 1000
        }

        raw_candles = self._make_request("GET", "/fapi/v1/klines", data)

        candles = []

        if raw_candles is not None:
            for c in raw_candles:
                candles.append(Candle(c, interval, "binance"))

        return candles

    # Get current bid and ask price for any symbol/contract, to display in the Watchlist.
    def get_bid_ask(self, contract: Contract) -> typing.Dict[str, float]:
        data = {
        'symbol': contract.symbol
        }
        ob_data = self._make_request("GET", "/fapi/v1/ticker/bookTicker", data)

        if ob_data is not None:
            if contract.symbol not in self.prices:
                self.prices[contract.symbol] = {'bid': float(ob_data['bidPrice']), 'ask': float(ob_data['askPrice'])}
            else:
                self.prices[contract.symbol]['bid'] = float(ob_data['bidPrice'])
                self.prices[contract.symbol]['ask'] = float(ob_data['askPrice'])

            return self.prices[contract.symbol]

    # Get current balance of account
    def get_balances(self) -> typing.Dict[str, Balance]:
        data = {
        'timestamp': int(time.time() * 1000)
        }
        data['signature'] = self._generate_signature(data)

        balances = dict()

        account_data = self._make_request("GET", "/fapi/v1/account", data)

        if account_data is not None:
            for a in account_data['assets']:
                balances[a['asset']] = Balance(a, "binance")

        return balances

    #  Place an order - depending on the order_type, price and tif arguments are not necessary
    def place_order(self, contract: Contract, order_type: str, quantity: float, side: str, price=None, tif=None) -> OrderStatus:
        data = {
        'symbol': contract.symbol,
        'side': side.upper(),
        'quantity': round(round(quantity / contract.lot_size) * contract.lot_size, 8),
        'type': order_type
        }

        if price is not None:
            data['price'] = round(round(price / contract.tick_size) * contract.tick_size, 8)

        if tif is not None:
            data['timeInForce'] = tif

        data['timestamp'] = int(time.time() * 1000)
        data['signature'] = self._generate_signature(data)

        order_status = self._make_request("POST", "/fapi/v1/order", data)

        if order_status is not None:
            order_status = OrderStatus(order_status, "binance")

        return order_status

    # Cancel order
    def cancel_order(self, contract: Contract, order_id: int) -> OrderStatus:

        data = {
        'orderId': order_id,
        'symbol': contract.symbol,
        'timestamp': int(time.time() * 1000)
        }
        data['signature'] = self._generate_signature(data)

        order_status = self._make_request("DELETE", "/fapi/v1/order", data)

        # If cancel order call was successful, replace order_status variable by OrderStatus object
        if order_status is not None:
            order_status = OrderStatus(order_status, "binance")

        return order_status

    # Get status of an order
    def get_order_status(self, contract: Contract, order_id: int) -> OrderStatus:

        data = {
        'timestamp': int(time.time() * 1000),
        'symbol': contract.symbol,
        'orderId': order_id
        }
        data['signature'] = self._generate_signature(data)


        # An error might be sent depending on market conditions because Binance does this to optimize
        # their internal engine on days when the market fluctuates a lot. Otherwise this should still work.
        order_status = self._make_request("GET", "/fapi/v1/order", data)

        if order_status is not None:
            order_status = OrderStatus(order_status, "binance")

        return order_status

    # Infinite loop (run in a Thread) which reopens the websocket connection in case it drops
    def _start_ws(self):
        self.ws = websocket.WebSocketApp(self._wss_url, on_open=self._on_open, on_close=self._on_close,
                                         on_error=self._on_error, on_message=self._on_message)

        while True:
            # Reconnect websocket connection if disconnected
            try:
                if self.reconnect:
                    self.ws.run_forever()
                else:
                    break
            except Exception as e:
                logger.error("Binance error in run_forever() method: %s", e)
            time.sleep(2)

    def _on_open(self, ws):
        logger.info("Binance connection opened")

        self.subscribe_channel(list(self.contracts.values()), "bookTicker")

    # Called when the connection drops
    def _on_close(self, ws):
        logger.warning("Binance Websocket connection closed")

    # Called in case of an error
    def _on_error(self, ws, msg: str):
        logger.error("Binance connection error: %s", msg)

    # The websocket updates of the channels subscribed go through this callback method
    def _on_message(self, ws, msg: str):

        data = json.loads(msg)

        if "e" in data:
            if data['e'] == "bookTicker":

                symbol = data['s']

                if symbol not in self.prices:
                    self.prices[symbol] = {'bid': float(data['b']), 'ask': float(data['a'])}
                else:
                    self.prices[symbol]['bid'] = float(data['b'])
                    self.prices[symbol]['ask'] = float(data['a'])

                # PNL Calculation
                try:
                    for b_index, strat in self.strategies.items():
                        if strat.contract.symbol == symbol:
                            for trade in strat.trades:
                                if trade.status == "open" and trade.entry_price is not None:
                                    if trade.side == "long":
                                        trade.pnl = (self.prices[symbol]['bid'] - trade.entry_price) * trade.quantity
                                    elif trade.side == "short":
                                        trade.pnl = (trade.entry_price - self.prices[symbol]['ask']) * trade.quantity
                except RuntimeError as e:
                    logger.error("Error while looping through the Binance strategies: %s", e)



            if data['e'] == "aggTrade":
                symbol = data['s']

                # Loop through strategies
                for key, strat in self.strategies.items():
                    if strat.contract.symbol == symbol:
                        res = strat.parse_trades(float(data['p']), float(data['q']), data['T'])
                        strat.check_trade(res)

    # Class method to subscribe to a channel to receive market data
    # If the list is bigger than 300 symbols the subscription will most likely fail
    def subscribe_channel(self, contracts: typing.List[Contract], channel: str):
        data = {
        'method': "SUBSCRIBE",
        'params': []
        }

        for contract in contracts:
            data['params'].append(contract.symbol.lower() + "@" + channel)
        data['id'] = self._ws_id

        try:
            self.ws.send(json.dumps(data))
        except Exception as e:
            logger.error("Websocket error while subscribing to %s %s updates: %s", len(contracts), channel, e)

        self._ws_id += 1

    # Calculate the trade size based on the percentage of the balance to use (defined in the strategy component)
    def get_trade_size(self, contract: Contract, price: float, balance_pct: float):

        balance = self.get_balances()
        if balance is not None:
            if 'USDT' in balance:
                balance = balance['USDT'].wallet_balance
            else:
                return None
        else:
            return None

        # Gives USDT amount to invest, dividing by price gives quantity
        trade_size = (balance * balance_pct / 100) / price

        trade_size = round(round(trade_size / contract.lot_size) * contract.lot_size, 8)

        logger.info("Binance Futures current USDT balance = %s, trade size = %s", balance, trade_size)

        return trade_size

