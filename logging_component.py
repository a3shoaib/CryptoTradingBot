# Displays messages to user

import tkinter as tk
from datetime import datetime

from styling import *

# Inherits from frame widget
class Logging(tk.Frame):
    # args allows for arguments to be passed without specifying the name
    # kwargs allows for key word arguments to be passed
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.logging_text = tk.Text(self, height=10, width=60, state=tk.DISABLED, bg=BG_COLOR, fg=FG_COLOR_2,
                                    font=GLOBAL_FONT, highlightthickness=False, bd=0)
        self.logging_text.pack(side=tk.TOP)

    def add_log(self, message: str):
        self.logging_text.configure(state=tk.NORMAL)

        # 1.0 indicates that the text will be added to the beginning (before existing text)
        self.logging_text.insert("1.0", datetime.now().strftime("%a %H:%M:%S :: ") + message + "\n")

        # After adding the message, lock again
        self.logging_text.configure(state=tk.DISABLED)
