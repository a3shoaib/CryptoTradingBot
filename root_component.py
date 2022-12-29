# interface

import tkinter as tk

from bitmex import BitmexClient
from binance_futures import BinanceFuturesClient

from styling import *
from logging_component import Logging

# Inherits from Tkinter library
class Root(tk.Tk):
    def __init__(self, binance: BinanceFuturesClient, bitmex: BitmexClient):
        super().__init__()

        self.binance = binance
        self.bitmex = bitmex


        self.title("Crypto Trading Bot")

        self.configure(bg=BG_COLOR)

        # Initializing frames for window
        self._left_frame = tk.Frame(self, bg=BG_COLOR)
        self._left_frame.pack(side=tk.LEFT)

        self._right_frame = tk.Frame(self, bg=BG_COLOR)
        self._right_frame.pack(side=tk.LEFT)

        self._logging_frame = Logging(self._left_frame, bg=BG_COLOR)
        self._logging_frame.pack(side=tk.TOP)

        # Call update method once after root component is initiated
        self._update_ui()

    # Checks periodically for new logs to add
    def _update_ui(self):
        for log in self.bitmex.logs:
            if not log['displayed']:
                self._logging_frame.add_log(log['log'])
                log['displayed'] = True

        for log in self.binance.logs:
            if not log['displayed']:
                self._logging_frame.add_log(log['log'])
                log['displayed'] = True

        # Only name the function, don't call it so no need for () in the end
        self.after(2000, self._update_ui)

