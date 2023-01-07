# interface
import json
import tkinter as tk
from tkinter.messagebox import askquestion
import logging
import json

from bitmex import BitmexClient
from binance_futures import BinanceFuturesClient

from styling import *
from logging_component import Logging
from watchlist_component import Watchlist
from trades_component import TradesWatch
from strategy_component import StrategyEditor

logger = logging.getLogger()

# Inherits from Tkinter library
class Root(tk.Tk):
    def __init__(self, binance: BinanceFuturesClient, bitmex: BitmexClient):
        super().__init__()

        self.binance = binance
        self.bitmex = bitmex

        self.title("Crypto Trading Bot")
        self.protocol("WM_DELETE_WINDOW", self._ask_before_close)


        self.title("Crypto Trading Bot")

        self.configure(bg=BG_COLOR)

        # Create the menu, sub menu, menu commands
        # Used to prevent overloading the UI with buttons
        self.main_menu = tk.Menu(self)
        self.configure(menu=self.main_menu)

        # Menu bar shows up at the very top of the window, unlike windows that shows it on top of application
        # tearoff=False means the menu tab cannot be detached from the main menu
        self.workspace_menu = tk.Menu(self.main_menu, tearoff=False)
        self.main_menu.add_cascade(label="Workspace", menu=self.workspace_menu)
        self.workspace_menu.add_command(label="Save workspace", command=self._save_workspace)

        # Initializing frames for window
        self._left_frame = tk.Frame(self, bg=BG_COLOR)
        self._left_frame.pack(side=tk.LEFT)

        self._right_frame = tk.Frame(self, bg=BG_COLOR)
        self._right_frame.pack(side=tk.LEFT)

        self._watchlist_frame = Watchlist(self.binance.contracts, self.bitmex.contracts, self._left_frame, bg=BG_COLOR)
        self._watchlist_frame.pack(side=tk.TOP)

        self.logging_frame = Logging(self._left_frame, bg=BG_COLOR)
        self.logging_frame.pack(side=tk.TOP)

        self._strategy_frame = StrategyEditor(self, self.binance, self.bitmex, self._right_frame, bg=BG_COLOR)
        self._strategy_frame.pack(side=tk.TOP)

        # Places new component on root component
        self._trades_frame = TradesWatch(self._right_frame, bg=BG_COLOR)
        self._trades_frame.pack(side=tk.TOP)

        # Call update method once after root component is initiated
        self._update_ui()

    # Called when the user clicks closes/tries to exit the program
    # Gives control of what is to happen before closing the UI
    def _ask_before_close(self):
        result = askquestion("Confirmation", "Do you want to exit the application?")
        if result == "yes":
            self.binance.reconnect = False
            self.bitmex.reconnect = False
            self.binance.ws.close()
            self.bitmex.ws.close()

            self.destroy()


    # Checks periodically for new logs to add and updates elements of the UI
    # Called every 1500 seconds, similar to infinite loop in another class, but it runs in the same thread as .mainloop()
    def _update_ui(self):

        # Logs

        for log in self.bitmex.logs:
            if not log['displayed']:
                self.logging_frame.add_log(log['log'])
                log['displayed'] = True

        for log in self.binance.logs:
            if not log['displayed']:
                self.logging_frame.add_log(log['log'])
                log['displayed'] = True

        # Trades and logs
        for client in [self.binance, self.bitmex]:
            try:
                for b_index, strat in client.strategies.items():
                    for log in strat.logs:
                        if not log['displayed']:
                            self.logging_frame.add_log(log['log'])
                            log['displayed'] = True

                    for trade in strat.trades:
                        if trade.time not in self._trades_frame.body_widgets['symbol']:
                            self._trades_frame.add_trade(trade)

                        if trade.contract.exchange == "binance":
                            precision = trade.contract.price_decimals
                        else:
                            precision = 8 # Always in bitcoin

                        pnl_str = "{0:.{prec}f}".format(trade.pnl, prec = precision)
                        self._trades_frame.body_widgets['pnl_var'][trade.time].set(pnl_str)
                        self._trades_frame.body_widgets['status_var'][trade.time].set(trade.status.capitalize())

            except RuntimeError as e:
                logger.error("Error while looping through strategies dictionary: %s", e)


        # Watchlist prices
        # Try-except statement because if loop through dictionary while a new key is being added
        # or a key is being deleted, there will be an error
        try:
            for key, value in self._watchlist_frame.body_widgets['symbol'].items():



                symbol = self._watchlist_frame.body_widgets['symbol'][key].cget("text")
                exchange = self._watchlist_frame.body_widgets['exchange'][key].cget("text")

                if exchange == "Binance":
                    if symbol not in self.binance.contracts:
                        continue

                    # Checks if prices dictionary has a key with a symbol
                    if symbol not in self.binance.prices:
                        self.binance.get_bid_ask(self.binance.contracts[symbol])
                        continue

                    precision = self.binance.contracts[symbol].price_decimals

                    prices = self.binance.prices[symbol]

                elif exchange == "Bitmex":
                    if symbol not in self.bitmex.contracts:
                        continue

                    if symbol not in self.bitmex.prices:
                        continue

                    precision = self.bitmex.contracts[symbol].price_decimals

                    prices = self.bitmex.prices[symbol]

                else:
                    continue

                if prices['bid'] is not None:
                    price_str = "{0:.{prec}f}".format(prices['bid'], prec=precision)
                    self._watchlist_frame.body_widgets['bid_var'][key].set(price_str)

                if prices['ask'] is not None:
                    price_str = "{0:.{prec}f}".format(prices['ask'], prec=precision)
                    self._watchlist_frame.body_widgets['ask_var'][key].set(price_str)

        except RuntimeError as e:
            logger.error("Error while looping through watchlist dictionary: %s", e)


        # Only name the function, don't call it so no need for () in the end
        self.after(1500, self._update_ui)

    # Collect the current data and save it to the SQLite database so that the data can be loaded again when the user
    # starts the program
    def _save_workspace(self):
        # Watchlist
        # Create list of tuples to pass to the WorkspaceData save method
        watchlist_symbols = []
        for key, value in self._watchlist_frame.body_widgets['symbol'].items():
            symbol = value.cget("text")
            exchange = self._watchlist_frame.body_widgets['exchange'][key].cget("text")

            watchlist_symbols.append((symbol, exchange))

        self._watchlist_frame.db.save("watchlist", watchlist_symbols)

        # Use DB Browser for SQLite to visualize the database

        # Strategies
        strategies = []

        strat_widgets = self._strategy_frame.body_widgets

        for b_index in strat_widgets['contract']:

            strategy_type = strat_widgets['strategy_type_var'][b_index].get()
            contract = strat_widgets['contract_var'][b_index].get()
            timeframe = strat_widgets['timeframe_var'][b_index].get()
            balance_pct = strat_widgets['balance_pct'][b_index].get()
            take_profit = strat_widgets['take_profit'][b_index].get()
            stop_loss = strat_widgets['stop_loss'][b_index].get()

            # Store all in one column in JSON string
            extra_params = dict()

            for param in self._strategy_frame.extra_params[strategy_type]:
                code_name = param['code_name']

                # Fill JSON dictionary
                extra_params[code_name] = self._strategy_frame.additional_parameters[b_index][code_name]

            strategies.append((strategy_type, contract, timeframe, balance_pct, take_profit, stop_loss,
                               json.dumps(extra_params)))

        self._strategy_frame.db.save("strategies", strategies)

        self.logging_frame.add_log("Workspace saved")



