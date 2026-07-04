from tkinter import *
from tkinter.ttk import *
from tkinter import filedialog


from func import write_config, read_config, reset_default_config

class SettingsWindow(Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Settings")

        self.output_dir = None
        self.input_dir = None
        self.temp_dir = None
        self.auto_select_file = BooleanVar()
        self.autosave = BooleanVar()
        self.save_on_close = BooleanVar()
        self.denoise_audio = BooleanVar()

        self.build_gui()
        
    def build_gui(self):
        settings_frame = Frame(self)
        settings_frame.pack(side=LEFT)
        
        
        # --- Output Path ---
        self.sv_output = StringVar()
        self.sv_output.trace_add('write', lambda name, index, mode, sv=self.sv_output:self._output_path_text_updated(self.sv_output))
        self.output_path_text = Entry(
            settings_frame,
            textvariable=self.sv_output
        )
        self.output_path_text.bind("<Return>", self._return)
        self.output_path_text.bind("<<Modified>>", self._output_path_text_updated)
        self.output_path_text.grid(column=0, row=0, padx=20, pady=10)
                
        self.output_path_btn = Button(
            settings_frame,
            text="Output Path",
            command=self._set_output_path
        )
        self.output_path_btn.grid(column=1, row=0, padx=20, pady=10)
        
        
        # --- Input Path ---
        self.sv_input = StringVar()
        self.sv_input.trace_add('write', lambda name, index, mode, sv=self.sv_input:self._input_path_text_updated(self.sv_input))
        self.input_path_text = Entry(
            settings_frame,
            textvariable=self.sv_input
        )
        self.input_path_text.bind("<Return>", self._return)
        self.input_path_text.bind("<<Modified>>", self._output_path_text_updated)
        self.input_path_text.grid(column=0, row=1, padx=20, pady=10)
                
        self.input_path_btn = Button(
            settings_frame,
            text="Input Path",
            command=self._set_input_path
        )
        self.input_path_btn.grid(column=1, row=1, padx=20, pady=10)
        
        # --- Temp Path ---
        
        self.sv_temp = StringVar()
        self.sv_temp.trace_add('write', lambda name, index, mode, sv=self.sv_output:self._temp_path_text_updated(self.sv_output))
        self.temp_path_text = Entry(
            settings_frame,
            textvariable=self.sv_temp
        )
        self.temp_path_text.bind("<Return>", self._return)
        self.temp_path_text.bind("<<Modified>>", self._temp_path_text_updated)
        self.temp_path_text.grid(column=0, row=2, padx=20, pady=10)
                
        self.temp_path_btn = Button(
            settings_frame,
            text="Temporary Path",
            command=self._set_output_path
        )
        self.temp_path_btn.grid(column=1, row=2, padx=20, pady=10)
        
        # --- Auto Select TickBox ---
        
        self.auto_select_file_box = Checkbutton(
            settings_frame,
            text="Automatically open 'sentences.txt' in input directory: ",
            variable=self.auto_select_file
        )
        self.auto_select_file_box.grid(column=0, row=3, padx=20, pady=10)
        
        # --- AutoSave TickBox ---
        
        self.autosave_box = Checkbutton(
            settings_frame,
            text="Automatically save files.",
            variable=self.autosave
        )
        self.autosave_box.grid(column=0, row=4, padx=20, pady=10)
        
        # --- Save on Close TickBox ---
        
        self.save_on_close_box = Checkbutton(
            settings_frame,
            text="Save files when the program closes",
            variable=self.save_on_close
        )
        self.save_on_close_box.grid(column=0, row=5, padx=20, pady=10)
        
        # --- Denoise TickBox ---
        
        self.denoise_audio_box = Checkbutton(
            settings_frame,
            text="Denoise Audio",
            variable=self.denoise_audio
        )
        self.denoise_audio_box.grid(column=0, row=6, padx=20, pady=10)
        
        # --- Save and Reset ---
        
        bottom_frame = Frame(self)
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
        
        self._fill_fields_from_config()
        
    
    def _set_output_path(self):
        directory = filedialog.askdirectory()
        self.output_path_text.delete(0, END)
        self.output_path_text.insert(0, directory)
        self.output_dir = directory
        
        self.lift()
        self.focus_force()
                
    def _set_input_path(self):
        directory = filedialog.askdirectory()
        self.input_path_text.delete(0, END)
        self.input_path_text.insert(0, directory)
        self.input_dir = directory
        
        self.lift()
        self.focus_force()
    
    def _set_temp_path(self):
        directory = filedialog.askdirectory()
        self.temp_path_text.delete(0, END)
        self.temp_path_text.insert(0, directory)
        self.temp_dir = directory
        
        self.lift()
        self.focus_force()
        
    def reset_config(self):
        reset_default_config()
        self.destroy()
        
    def save_settings(self):
        if self.output_dir is not None and self.input_dir is not None:
            write_config("output_dir", self.output_dir)
            write_config("input_dir", self.input_dir)
            write_config("auto_select_input", self.auto_select_file.get())
            write_config("autosave", self.autosave.get())
            write_config("save_on_close", self.save_on_close.get())
            write_config("temp_dir", self.temp_dir)
            write_config("denoise_audio", self.denoise_audio.get())
            
        self.destroy()
        
    def _input_path_text_updated(self, event):
        self.input_dir = self.input_path_text.get()
        
    def _output_path_text_updated(self, event):
        self.output_dir = self.output_path_text.get()
        
    def _temp_path_text_updated(self, event):
        self.temp_dir = self.temp_path_text.get()
    
    def _fill_fields_from_config(self):
        self.output_dir = read_config("output_dir")
        self.input_dir = read_config("input_dir")
        self.temp_dir = read_config("temp_dir")
        
        self.output_path_text.delete(0, END)
        self.output_path_text.insert(0, self.output_dir)
        
        self.input_path_text.delete(0, END)
        self.input_path_text.insert(0, self.input_dir)
        
        self.temp_path_text.delete(0, END)
        self.temp_path_text.insert(0, self.temp_dir)
        
        self.auto_select_file.set(read_config("auto_select_input"))
        self.autosave.set(read_config("autosave"))
        self.save_on_close.set(read_config("save_on_close"))
        self.denoise_audio.set(read_config("denoise_audio"))
        
                
        
    def _return(self, event):
        return 'break'