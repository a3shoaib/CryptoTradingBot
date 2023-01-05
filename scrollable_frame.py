import tkinter as tk


class ScrollableFrame(tk.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Need a widget that is scrollable and will allow for a Frame to be placed in it
        # --> canvas
        self.canvas = tk.Canvas(self, highlightthickness=0, **kwargs)
        self.vsb = tk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        # Frame that will go in canvas
        self.sub_frame = tk.Frame(self.canvas, **kwargs)

        self.sub_frame.bind("<Configure>", self._on_frame_configure)

        # nw is northwest, (0,0) are the coordinates of the frame from the top left position
        self.canvas.create_window((0, 0), window=self.sub_frame, anchor="nw")

        self.canvas.configure(yscrollcommand=self.vsb.set)

        # Parent window is a frame
        self.canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.vsb.pack(side=tk.RIGHT, fill=tk.Y)

    def _on_frame_configure(self, event: tk.Event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
