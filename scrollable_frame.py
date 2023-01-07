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
        self.sub_frame.bind("<Enter>", self._activate_mousewheel)
        self.sub_frame.bind("<Leave>", self._deactivate_mousewheel)

        # nw is northwest, (0,0) are the coordinates of the frame from the top left position
        self.canvas.create_window((0, 0), window=self.sub_frame, anchor="nw")

        self.canvas.configure(yscrollcommand=self.vsb.set)

        # Parent window is a frame
        self.canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.vsb.pack(side=tk.RIGHT, fill=tk.Y)

    # Create canvas content
    def _on_frame_configure(self, event: tk.Event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    # Activate the mousewheel when mouse enters the canvas sub frame
    def _activate_mousewheel(self, event: tk.Event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    # Dectivate the mousewheel when mouse leaves the canvas sub frame
    def _deactivate_mousewheel(self, event: tk.Event):
        self.canvas.unbind_all("<MouseWheel>")

    # Scroll the content in the canvas when the MouseWheel is called.
    def _on_mousewheel(self, event: tk.Event):
        self.canvas.yview_scroll(int(-1 * event.delta), "units")


