# Watchlist is a component that streams market data

import tkinter as tk
import typing
import tkmacosx as tkmac

from models import *
from styling import *

class Watchlist (tk.Frame):
    def __init__(self, binance_contracts: typing.Dict[str, Contract], bitmex_contracts: typing.Dict[str, Contract], *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.binance_symbols = list(binance_contracts.keys())
        self.bitmex_symbols = list(bitmex_contracts.keys())

        self._commands_frame = tk.Frame(self, bg=BG_COLOR)
        self._commands_frame.pack(side=tk.TOP)

        self._table_frame = tk.Frame(self, bg=BG_COLOR)
        self._table_frame.pack(side=tk.TOP)

        self._binance_label = tk.Label(self._commands_frame, text="Binance", bg=BG_COLOR, fg=FG_COLOR, font=BOLD_FONT)
        self._binance_label.grid(row=0, column=0)

        # insertbackground is the colour of the cursor when placed onto the entry widget
        self._binance_entry = tk.Entry(self._commands_frame, fg=FG_COLOR, justify=tk.CENTER, insertbackground=FG_COLOR,
                                       bg=BG_COLOR_2, highlightthickness=False)
        # Associate keyboard action to a callback function
        self._binance_entry.bind("<Return>", self._add_binance_symbol)
        self._binance_entry.grid(row=1, column=0)

        self._bitmex_label = tk.Label(self._commands_frame, text="Bitmex", bg=BG_COLOR, fg=FG_COLOR, font=BOLD_FONT)
        self._bitmex_label.grid(row=0, column=1)

        self._bitmex_entry = tk.Entry(self._commands_frame, fg=FG_COLOR, justify=tk.CENTER, insertbackground=FG_COLOR,
                                      bg=BG_COLOR_2, highlightthickness=False)
        self._bitmex_entry.bind("<Return>", self._add_bitmex_symbol)
        self._bitmex_entry.grid(row=1, column=1)

        # Refers to the widgets in the table body
        self.body_widgets = dict()

        # Headers that will be on the first row
        self._headers = ["symbol", "exchange", "bid", "ask", "remove"]

        # Loop through headers to create widgets dynamically
        for idx, h in enumerate(self._headers):
            header = tk.Label(self._table_frame, text=h.capitalize() if h != "remove" else "", bg=BG_COLOR, fg=FG_COLOR,
                              font=BOLD_FONT)
            header.grid(row=0, column=idx)

        # Creates keys of the dictionary in the loop so that self.headers can be reused
        for h in self._headers:
            self.body_widgets[h] = dict()
            if h in ["bid", "ask"]:
                self.body_widgets[h + "_var"] = dict()

        # Starts at 1 because row is 0 is occupied
        self._body_index = 1

    def _remove_symbol(self, b_index: int):
        # Loops through columns, selects row to delete, and removes the cells
        for h in self._headers:
            self.body_widgets[h][b_index].grid_forget()
            del self.body_widgets[h][b_index]

    def _add_binance_symbol(self, event):
         # Get entry box content
        symbol = event.widget.get()

        if symbol in self.binance_symbols:
            self._add_symbol(symbol, "Binance")
            event.widget.delete(0, tk.END)

    def _add_bitmex_symbol(self, event):
        symbol = event.widget.get()

        if symbol in self.bitmex_symbols:
            self._add_symbol(symbol, "Bitmex")
            event.widget.delete(0, tk.END)

    def _add_symbol(self, symbol: str, exchange: str):
        b_index = self._body_index

        # Creates 4 variables
        self.body_widgets['symbol'][b_index] = tk.Label(self._table_frame, text=symbol, bg=BG_COLOR, fg=FG_COLOR_2,
                                                        font=GLOBAL_FONT)
        self.body_widgets['symbol'][b_index].grid(row=b_index, column=0)

        self.body_widgets['exchange'][b_index] = tk.Label(self._table_frame, text=exchange, bg=BG_COLOR, fg=FG_COLOR_2,
                                                        font=GLOBAL_FONT)
        self.body_widgets['exchange'][b_index].grid(row=b_index, column=1)

        self.body_widgets['bid_var'][b_index] = tk.StringVar()
        self.body_widgets['bid'][b_index] = tk.Label(self._table_frame, textvariable=self.body_widgets['bid_var'][b_index],
                                                     bg=BG_COLOR, fg=FG_COLOR_2, font=GLOBAL_FONT)
        self.body_widgets['bid'][b_index].grid(row=b_index, column=2)

        self.body_widgets['ask_var'][b_index] = tk.StringVar()
        self.body_widgets['ask'][b_index] = tk.Label(self._table_frame, textvariable=self.body_widgets['ask_var'][b_index],
                                                     bg=BG_COLOR, fg=FG_COLOR_2, font=GLOBAL_FONT)

        # When needed to modify values of bid and ask label from another module, access body_widgets and
        # bid_var or ask_var key and then use set() method on it
        self.body_widgets['ask'][b_index].grid(row=b_index, column=3)

        # Adds a button when a symbol is added to the watchlist
        self.body_widgets['remove'][b_index] = tkmac.Button(self._table_frame, text="X", borderless=True,
                                                     bg="darkred", fg=FG_COLOR, font=GLOBAL_FONT,
                                                     command=lambda: self._remove_symbol(b_index))
        self.body_widgets['remove'][b_index].grid(row=b_index, column=4)


        self._body_index += 1


