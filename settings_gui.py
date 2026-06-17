from tkinter import *
from tkinter.ttk import *
from tkinter import filedialog


from func import write_config, read_config, reset_default_config

class SettingsWindow(Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Settings")

        self.output_dir = None

        self.build_gui()
        
    def build_gui(self):
        
        settings_frame = Frame(self)
        settings_frame.pack(side=LEFT)
        
        
        self.sv = StringVar()
        self.sv.trace_add('write', lambda name, index, mode, sv=self.sv:self._text_updated(self.sv))
        self.output_path_text = Entry(
            settings_frame,
            textvariable=self.sv
        )
        self.output_path_text.bind("<Return>", self._return)
        self.output_path_text.bind("<<Modified>>", self._text_updated)
        self.output_path_text.grid(column=0, row=0, padx=20, pady=20)
                
        self.output_path_btn = Button(
            settings_frame,
            text="Output Path",
            command=self._set_output_path
        )
        self.output_path_btn.grid(column=1, row=0, padx=20, pady=20)
        
        
        
        bottom_frame = Frame(self)
        # bottom_frame.pack(side=RIGHT)
        bottom_frame.pack(side=BOTTOM)
        
        self.reset_btn = Button(
            bottom_frame,
            text="Reset",
            command=self.reset_config
        )
        self.reset_btn.pack(side=LEFT)
        
        self.save_btn = Button(
            bottom_frame,
            text="Save",
            command=self.save_settings
        )
        self.save_btn.pack(padx=20, pady=20, side=RIGHT)
        
    
    def _set_output_path(self):
        directory = filedialog.askdirectory()
        self.output_path_text.delete(0, END)
        self.output_path_text.insert(0, directory)
        self.output_dir = directory
        
        self.lift()
        self.focus_force()
        
    def reset_config(self):
        reset_default_config()
        self.destroy()
        

    def save_settings(self):
        if self.output_dir is not None:
            write_config("output_path", self.output_dir)
            
        self.destroy()
        
    def _text_updated(self, event):
        self.output_dir = self.output_path_text.get()
        
        
    def _return(self, event):
        return 'break'