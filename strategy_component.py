import json
import tkinter as tk
import typing
import tkmacosx as tkmac

import json

from styling import *
from scrollable_frame import ScrollableFrame
from binance_futures import BinanceFuturesClient
from bitmex import BitmexClient

from strategies import TechnicalStrategy, BreakoutStrategy
from utils import *

from database import WorkspaceData

if typing.TYPE_CHECKING:
    from root_component import Root

class StrategyEditor (tk.Frame):
    def __init__(self, root: "Root", binance: BinanceFuturesClient, bitmex: BitmexClient, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.root = root

        self.db = WorkspaceData()

        self._valid_integer = self.register(check_integer_format)
        self._valid_float = self.register(check_float_format)

        self._exchanges = {"Binance": binance, "Bitmex": bitmex}

        self._all_contracts = []
        self._all_timeframes = ["1m", "5m", "15m", "30m", "1h", "4h"]

        # Populate _all_contracts
        for exchange, client in self._exchanges.items():
            for symbol, contract in client.contracts.items():
                self._all_contracts.append(symbol + "_" + exchange.capitalize())

        self._commands_frame = tk.Frame(self, bg=BG_COLOR)
        self._commands_frame.pack(side=tk.TOP)

        self._table_frame = tk.Frame(self, bg=BG_COLOR)
        self._table_frame.pack(side=tk.TOP)

        self._add_button = tkmac.Button(self._commands_frame, text="Add strategy", font=GLOBAL_FONT,
                                     command=self._add_strategy_row, bg=BG_COLOR_2, fg=FG_COLOR, borderless=True)
        self._add_button.pack(side=tk.TOP)

        # Refers to the widgets in the table body
        self.body_widgets = dict()

        # Headers that will be on the first row
        # Update: added headers in _base_params
        # self._headers = ["Strategy", "Contract", "Timeframe", "Balance %", "TP %", "SL %"]

        self._headers_frame = tk.Frame(self._table_frame, bg=BG_COLOR)

        self.additional_parameters = dict()
        self._extra_input = dict()

        # Dictionary to describe each of the widgets to add and put it in a list
        self._base_params = [
            {"code_name": "strategy_type", "widget": tk.OptionMenu, "data_type": str,
             "values": ["Technical", "Breakout"], "width": 7, "header": "Strategy"},
            {"code_name": "contract", "widget": tk.OptionMenu, "data_type": str, "values": self._all_contracts
             , "width": 15, "header": "  Contract"},
            {"code_name": "timeframe", "widget": tk.OptionMenu, "data_type": str, "values": self._all_timeframes
                , "width": 15, "header": "                  Timeframe"},
            {"code_name": "balance_pct", "widget": tk.Entry, "data_type": float, "width": 18, "header": "                          Balance %"},
            {"code_name": "take_profit", "widget": tk.Entry, "data_type": float, "width": 14, "header": "                           TP %"},
            {"code_name": "stop_loss", "widget": tk.Entry, "data_type": float, "width": 14, "header": "                          SL %"},
            # Configure additional parameters
            {"code_name": "parameters", "widget": tk.Button, "data_type": float, "text": "Parameters",
             "bg": BG_COLOR_2, "command": self._show_popup, "header": "", "width": 70},
            # Activate strategy
            {"code_name": "activation", "widget": tk.Button, "data_type": float, "text": "OFF",
             "bg": "darkred", "command": self._switch_strategy, "header": "", "width": 30},
            # Delete current row
            {"code_name": "delete", "widget": tk.Button, "data_type": float, "text": "X",
             "bg": "darkred", "command": self._delete_row, "header": "", "width": 30},

        ]

        # List of dictionary to describe additional parameters depending on strategy chosen
        self.extra_params = {
            "Technical": [
                {"code_name": "rsi_length", "name": "RSI Periods", "widget": tk.Entry, "data_type": int},
                {"code_name": "ema_fast", "name": "MACD Fast Length", "widget": tk.Entry, "data_type": int},
                {"code_name": "ema_slow", "name": "MACD Slow Length", "widget": tk.Entry, "data_type": int},
                {"code_name": "ema_signal", "name": "MACD Signal Length", "widget": tk.Entry, "data_type": int},
            ],
            "Breakout": [
                {"code_name": "min_volume", "name": "Minimum Volume", "widget": tk.Entry, "data_type": float},
            ]

        }

        # Loop through headers to create widgets dynamically
        for idx, h in enumerate(self._base_params):
            header = tk.Label(self._headers_frame, text=h['header'], bg=BG_COLOR, fg=FG_COLOR, font=GLOBAL_FONT,
                              width=h['width'], bd=1, relief=tk.FLAT)
            header.grid(row=0, column=idx, padx=2)

        header = tk.Label(self._headers_frame, text="", bg=BG_COLOR, fg=FG_COLOR, font=GLOBAL_FONT,
                          width=8, bd=1, relief=tk.FLAT)
        header.grid(row=0, column=len(self._base_params), padx=2)

        self._headers_frame.pack(side=tk.TOP, anchor="nw")

        self._body_frame = ScrollableFrame(self._table_frame, bg=BG_COLOR, height=250)
        self._body_frame.pack(side=tk.TOP, fill=tk.X, anchor="nw")

        # Creates keys of the dictionary in the loop so that self.headers can be reused
        for h in self._base_params:
            self.body_widgets[h['code_name']] = dict()
            if h['code_name'] in ["strategy_type", "contract", "timeframe"]:
                self.body_widgets[h['code_name'] + "_var"] = dict()

        # Starts at 1 because row is 0 is occupied
        self._body_index = 1

        self._load_workspace()

    # Add new row of widgets that are defined in self._base_params lsit and align with the headers
    # Mac and Windows has an effect on the layout and how it may appear when the user is running the application
    def _add_strategy_row(self):
        b_index = self._body_index

        for col, base_param in enumerate(self._base_params):
            code_name = base_param['code_name']
            if base_param['widget'] == tk.OptionMenu:
                self.body_widgets[code_name + "_var"][b_index] = tk.StringVar()
                self.body_widgets[code_name + "_var"][b_index].set(base_param['values'][0])
                self.body_widgets[code_name][b_index] = tk.OptionMenu(self._body_frame.sub_frame,
                                                                      self.body_widgets[code_name + "_var"][b_index],
                                                                      *base_param['values']) # * will unpack the list
                self.body_widgets[code_name][b_index].config(width=base_param['width'],
                                                             bd=-1, indicatoron=0, highlightthickness=False, font=GLOBAL_FONT)

            elif base_param['widget'] == tk.Entry:
                self.body_widgets[code_name][b_index] = tk.Entry(self._body_frame.sub_frame, justify=tk.CENTER,
                                                                 font=GLOBAL_FONT, bd=0, highlightthickness=False,
                                                                 width=base_param['width'])

                # Modify the widget depending on if want an integer or floating number as data type
                if base_param['data_type'] == int:
                    self.body_widgets[code_name][b_index].config(validate='key', validatecommand=(self._valid_integer, "%P"))
                elif base_param['data_type'] == float:
                    self.body_widgets[code_name][b_index].config(validate='key', validatecommand=(self._valid_float, "%P"))

            elif base_param['widget'] == tk.Button:
                self.body_widgets[code_name][b_index] = tkmac.Button(self._body_frame.sub_frame, text=base_param['text'],
                                            bg=base_param['bg'], fg=FG_COLOR, font=GLOBAL_FONT, width=base_param['width'], borderless=True,
                                            command=lambda frozen_command=base_param['command']: frozen_command(b_index))
            else:
                continue

            self.body_widgets[code_name][b_index].grid(row=b_index, column=col, padx=2)

        self.additional_parameters[b_index] = dict()

        for strat, params in self.extra_params.items():
            for param in params:
                self.additional_parameters[b_index][param['code_name']] = None



        self._body_index += 1

    # Delete row of the widgets
    def _delete_row(self, b_index: int):
        for element in self._base_params:
            # Access each of the 9 columns and access row that is clicked with b_index to remove it from the interface
            self.body_widgets[element['code_name']][b_index].grid_forget()

            # Delete element from body_widgets dictionary
            del self.body_widgets[element['code_name']][b_index]


    # Show popup with additional parameters, specific to the strategy selected
    def _show_popup(self, b_index: int):

        # Coordinates of button that was clicked
        x = self.body_widgets["parameters"][b_index].winfo_rootx()
        y = self.body_widgets["parameters"][b_index].winfo_rooty()

        self._popup_window = tk.Toplevel(self)
        self._popup_window.wm_title("Parameters")

        self._popup_window.config(bg=BG_COLOR)
        self._popup_window.attributes("-topmost", "true")
        self._popup_window.grab_set()

        self._popup_window.geometry(f"+{x-80}+{y+30}")

        strat_selected = self.body_widgets['strategy_type_var'][b_index].get()

        row_nb = 0

        for param in self.extra_params[strat_selected]:
            code_name = param['code_name']

            temp_label = tk.Label(self._popup_window, bg=BG_COLOR, fg=FG_COLOR, text=param['name'], font=BOLD_FONT)
            temp_label.grid(row=row_nb, column=0)

            # Every time an entry box is created, reference the entry widget to the extra_input dictionary
            # access self._extra_input[code_name] in another method
            if param['widget'] == tk.Entry:
                self._extra_input[code_name] = tk.Entry(self._popup_window, bg=BG_COLOR_2, justify=tk.CENTER, fg=FG_COLOR,
                                      insertbackground=FG_COLOR, highlightthickness=False)

                if param['data_type'] == int:
                    self._extra_input[code_name].config(validate='key', validatecommand=(self._valid_integer, "%P"))
                elif param['data_type'] == float:
                    self._extra_input[code_name].config(validate='key', validatecommand=(self._valid_float, "%P"))

                if self.additional_parameters[b_index][code_name] is not None:
                    # Entry widget is empty when data is inserted so insert(tk.END...) vs tk(0...) doesn't matter
                    self._extra_input[code_name].insert(tk.END, str(self.additional_parameters[b_index][code_name]))
            else:
                continue

            self._extra_input[code_name].grid(row=row_nb, column=1)

            row_nb += 1

        # Validation Button
        validation_button = tkmac.Button(self._popup_window, text="Validate", bg=BG_COLOR_2, fg=FG_COLOR,
                                      command=lambda: self._validate_parameters(b_index), borderless=True)
        validation_button.grid(row=row_nb, column=0, columnspan=2)

    # Keep track of the parameters set in the popup window and close the window
    def _validate_parameters(self, b_index: int):
        strat_selected = self.body_widgets['strategy_type_var'][b_index].get()

        # Loops through parameters, get values, and stores them
        for param in self.extra_params[strat_selected]:
            code_name = param['code_name']

            if self._extra_input[code_name].get() == "":
                self.additional_parameters[b_index][code_name] = None
            else:
                self.additional_parameters[b_index][code_name] = param['data_type'](self._extra_input[code_name].get())

        self._popup_window.destroy()

    # Called when the ON/OFF button is clicked. Collects historical data, thus causing a small delay
    def _switch_strategy(self, b_index: int):
        # Activate/deactivate strategy
        # When activated, check that no parameters are forgotten

        for param in ["balance_pct", "take_profit", "stop_loss"]:
            if self.body_widgets[param][b_index].get() == "":
                self.root.logging_frame.add_log(f"Missing {param} parameter")
                return

        strat_selected = self.body_widgets['strategy_type_var'][b_index].get()

        for param in self.extra_params[strat_selected]:
            if self.additional_parameters[b_index][param['code_name']] is None:
                self.root.logging_frame.add_log(f"Missing {param['code_name']} parameter")
                return

        symbol = self.body_widgets['contract_var'][b_index].get().split("_")[0]
        timeframe = self.body_widgets['timeframe_var'][b_index].get()
        exchange = self.body_widgets['contract_var'][b_index].get().split("_")[1]

        contract = self._exchanges[exchange].contracts[symbol]

        balance_pct = float(self.body_widgets['balance_pct'][b_index].get())
        take_profit = float(self.body_widgets['take_profit'][b_index].get())
        stop_loss = float(self.body_widgets['stop_loss'][b_index].get())

        if self.body_widgets['activation'][b_index].cget("text") == "OFF":
            # Activate strategy
            if strat_selected == "Technical":
                new_strategy = TechnicalStrategy(self._exchanges[exchange], contract, exchange, timeframe, balance_pct, take_profit, stop_loss,
                                                 self.additional_parameters[b_index])
            elif strat_selected == "Breakout":
                new_strategy = BreakoutStrategy(self._exchanges[exchange], contract, exchange, timeframe, balance_pct, take_profit, stop_loss,
                                                 self.additional_parameters[b_index])
            else:
                return

            # Get historical data when initializing strategy
            new_strategy.candles = self._exchanges[exchange].get_historical_candles(contract, timeframe)

            if len(new_strategy.candles) == 0:
                self.root.logging_frame.add_log(f"No historical data retrieved for {contract.symbol}")
                return

            if exchange == "Binance":
                self._exchanges[exchange].subscribe_channel([contract], "aggTrade")

            self._exchanges[exchange].strategies[b_index] = new_strategy

            # Other buttons will be deactivated to prevent user from changing values while strategy is running
            for param in self._base_params:
                code_name = param['code_name']

                if code_name != "activation" and "_var" not in code_name:
                    self.body_widgets[code_name][b_index].config(state=tk.DISABLED)

            self.body_widgets["activation"][b_index].config(bg="darkgreen", text="ON")
            self.root.logging_frame.add_log(f"{strat_selected} strategy on {symbol} / {timeframe} started")
        else:
            # Deactivate strategy
            del self._exchanges[exchange].strategies[b_index]

            for param in self._base_params:
                code_name = param['code_name']

                if code_name != "activation" and "_var" not in code_name:
                    self.body_widgets[code_name][b_index].config(state=tk.NORMAL)

            self.body_widgets['activation'][b_index].config(bg="darkred", text="OFF")
            self.root.logging_frame.add_log(f"{strat_selected} strategy on {symbol} / {timeframe} stopped")

    # Load data from the database and add them to the rows
    def _load_workspace(self):
        data = self.db.get("strategies")

        for row in data:
            self._add_strategy_row()
            # -1 because everytime a new row is added since self._body_index is incremented at the end of the method it's in
            b_index = self._body_index - 1

            for base_param in self._base_params:
                code_name = base_param['code_name']

                if base_param['widget'] == tk.OptionMenu and row[code_name] is not None:
                    self.body_widgets[code_name + "_var"][b_index].set(row[code_name])
                elif base_param['widget'] == tk.Entry and row[code_name] is not None:
                    self.body_widgets[code_name][b_index].insert(tk.END, row[code_name])

            extra_params = json.loads(row['extra_params'])

            for param, value in extra_params.items():
                if value is not None:
                    self.additional_parameters[b_index][param] = value


