import tkinter as tk
import typing
import datetime

from models import *

from styling import *

class TradesWatch(tk.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Reference the widgets on each row
        self.body_widgets = dict()

        self._headers = ["time", "symbol", "exchange", "strategy", "side", "quantity", "status", "pnl"]

        self._table_frame = tk.Frame(self, bg=BG_COLOR)
        self._table_frame.pack(side=tk.TOP)

        # Loop through headers to create widgets dynamically
        for idx, h in enumerate(self._headers):
            header = tk.Label(self._table_frame, text=h.capitalize(), bg=BG_COLOR, fg=FG_COLOR,
                              font=BOLD_FONT)
            header.grid(row=0, column=idx)

        # Creates keys of the dictionary in the loop so that self.headers can be reused
        for h in self._headers:
            self.body_widgets[h] = dict()
            if h in ["status", "pnl"]:
                self.body_widgets[h + "_var"] = dict()

        # Starts at 1 because row is 0 is occupied
        self._body_index = 1

    # Used by _update_ui method in root_component class
    def add_trade(self, trade: Trade):

        b_index = self._body_index

        t_index = trade.time

        dt_str = datetime.datetime.fromtimestamp(trade.time / 1000).strftime("%b %d %H:%M")

        # Labels and string variables
        self.body_widgets['time'][t_index] = tk.Label(self._table_frame, text=dt_str, bg=BG_COLOR, fg=FG_COLOR_2,
                                                      font =GLOBAL_FONT)
        self.body_widgets['time'][t_index].grid(row=b_index, column=0)

        # Symbol
        self.body_widgets['symbol'][t_index] = tk.Label(self._table_frame, text=trade.contract.symbol, bg=BG_COLOR, fg=FG_COLOR_2,
                                                      font=GLOBAL_FONT)
        self.body_widgets['symbol'][t_index].grid(row=b_index, column=1)

        # Exchange
        self.body_widgets['exchange'][t_index] = tk.Label(self._table_frame, text=trade.contract.exchange.capitalize(),
                                                          bg=BG_COLOR, fg=FG_COLOR_2, font=GLOBAL_FONT)
        self.body_widgets['exchange'][t_index].grid(row=b_index, column=2)

        # Strategy
        self.body_widgets['strategy'][t_index] = tk.Label(self._table_frame, text=trade.strategy, bg=BG_COLOR, fg=FG_COLOR_2,
                                                      font=GLOBAL_FONT)
        self.body_widgets['strategy'][t_index].grid(row=b_index, column=3)

        # Side
        self.body_widgets['side'][t_index] = tk.Label(self._table_frame, text=trade.side.capitalize(), bg=BG_COLOR,
                                                          fg=FG_COLOR_2, font=GLOBAL_FONT)
        self.body_widgets['side'][t_index].grid(row=b_index, column=4)

        # Quantity
        self.body_widgets['quantity'][t_index] = tk.Label(self._table_frame, text=trade.quantity, bg=BG_COLOR,
                                                      fg=FG_COLOR_2, font=GLOBAL_FONT)
        self.body_widgets['quantity'][t_index].grid(row=b_index, column=5)

        # Status
        self.body_widgets['status_var'][t_index] = tk.StringVar()
        self.body_widgets['status'][t_index] = tk.Label(self._table_frame,
                                                    textvariable=self.body_widgets['status_var'][t_index], bg=BG_COLOR,
                                                    fg=FG_COLOR_2, font=GLOBAL_FONT)
        self.body_widgets['status'][t_index].grid(row=b_index, column=6)

        # PNL
        self.body_widgets['pnl_var'][t_index] = tk.StringVar()
        self.body_widgets['pnl'][t_index] = tk.Label(self._table_frame,
                                                     textvariable=self.body_widgets['pnl_var'][t_index], bg=BG_COLOR,
                                                      fg=FG_COLOR_2, font=GLOBAL_FONT)
        self.body_widgets['pnl'][t_index].grid(row=b_index, column=7)

        self._body_index += 1