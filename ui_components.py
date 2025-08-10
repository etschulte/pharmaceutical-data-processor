import customtkinter as ctk
import tkinter as tk
import pandas as pd
from tkinter import filedialog
from typing import Callable, Optional


class FileSelectionPanel(ctk.CTkFrame):
    """Combined file selection panel with aligned inputs"""

    def __init__(self, parent, file_change_callback: Optional[Callable] = None):
        super().__init__(parent)
        self.file_change_callback = file_change_callback

        # Configure grid
        self.grid_columnconfigure(1, weight=1)

        # Input file selection
        input_label = ctk.CTkLabel(self, text="Input File:", font=ctk.CTkFont(weight="bold"))
        input_label.grid(row=0, column=0, sticky="w", padx=(10, 10), pady=5)

        self.input_entry = ctk.CTkEntry(self, width=400, placeholder_text="Select Excel file...")
        self.input_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=5)

        input_btn = ctk.CTkButton(self, text="Browse", command=self._browse_input, width=100)
        input_btn.grid(row=0, column=2, pady=5)

        # Output directory selection
        output_label = ctk.CTkLabel(self, text="Output Directory:", font=ctk.CTkFont(weight="bold"))
        output_label.grid(row=1, column=0, sticky="w", padx=(10, 10), pady=5)

        self.output_entry = ctk.CTkEntry(self, width=400, placeholder_text="Select output directory...")
        self.output_entry.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=5)

        output_btn = ctk.CTkButton(self, text="Browse", command=self._browse_output, width=100)
        output_btn.grid(row=1, column=2, pady=5)

        # Store paths
        self.input_path = ""
        self.output_path = ""

    def _browse_input(self):
        path = filedialog.askopenfilename(
            title="Select Excel File",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        if path:
            self.input_path = path
            self.input_entry.delete(0, "end")
            self.input_entry.insert(0, path)
            if self.file_change_callback:
                self.file_change_callback(path)

    def _browse_output(self):
        path = filedialog.askdirectory(title="Select Output Directory")
        if path:
            self.output_path = path
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, path)

    def get_input_path(self) -> str:
        return self.input_path or self.input_entry.get()

    def get_output_path(self) -> str:
        return self.output_path or self.output_entry.get()


class FileSelector(ctk.CTkFrame):
    """Reusable file selector component"""

    def __init__(self, parent, label_text: str, placeholder: str, file_mode: str = "file"):
        super().__init__(parent)
        self.file_mode = file_mode
        self.selected_path = ""

        # Configure grid
        self.grid_columnconfigure(1, weight=1)

        # Label
        self.label = ctk.CTkLabel(self, text=label_text, font=ctk.CTkFont(weight="bold"))
        self.label.grid(row=0, column=0, sticky="w", padx=(0, 10))

        # Entry
        self.entry = ctk.CTkEntry(self, width=400, placeholder_text=placeholder)
        self.entry.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        # Browse button
        self.browse_btn = ctk.CTkButton(self, text="Browse", command=self._browse, width=100)
        self.browse_btn.grid(row=0, column=2)

    def _browse(self):
        if self.file_mode == "file":
            path = filedialog.askopenfilename(
                title="Select Excel File",
                filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
            )
        else:  # directory
            path = filedialog.askdirectory(title="Select Directory")

        if path:
            self.selected_path = path
            self.entry.delete(0, "end")
            self.entry.insert(0, path)

    def get_path(self) -> str:
        return self.selected_path

    def set_path(self, path: str):
        self.selected_path = path
        self.entry.delete(0, "end")
        self.entry.insert(0, path)


class DataPreview(ctk.CTkFrame):
    """Data preview component with treeview"""

    def __init__(self, parent):
        super().__init__(parent)

        self.current_df = pd.DataFrame()  # Store current dataframe

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Title
        title = ctk.CTkLabel(self, text="Data Preview", font=ctk.CTkFont(size=16, weight="bold"))
        title.grid(row=0, column=0, pady=(10, 5), sticky="w", padx=10)

        # Setup treeview with styling
        self._setup_treeview_style()

        # Treeview
        self.tree = tk.ttk.Treeview(self)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        # Scrollbars
        v_scrollbar = tk.ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        v_scrollbar.grid(row=1, column=1, sticky="ns", pady=(0, 10))
        self.tree.configure(yscrollcommand=v_scrollbar.set)

        h_scrollbar = tk.ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        h_scrollbar.grid(row=2, column=0, sticky="ew", padx=10)
        self.tree.configure(xscrollcommand=h_scrollbar.set)

    def _setup_treeview_style(self):
        """Setup treeview styling for dark theme"""
        style = tk.ttk.Style()
        style.theme_use('clam')

        style.configure("Treeview",
                        background="#2b2b2b",
                        foreground="white",
                        fieldbackground="#2b2b2b",
                        borderwidth=0)
        style.configure("Treeview.Heading",
                        background="#1f1f1f",
                        foreground="white",
                        borderwidth=1)
        style.map('Treeview', background=[('selected', '#144870')])

    def load_from_file(self, file_path: str):
        """Load and display data from file"""
        try:
            self.current_df = pd.read_excel(file_path)
            self.display_dataframe(self.current_df, max_rows=20)
            return True, f"Loaded {len(self.current_df)} rows, {len(self.current_df.columns)} columns"
        except Exception as e:
            return False, f"Error loading file: {str(e)}"

    def display_dataframe(self, df: pd.DataFrame, max_rows: int = 20):
        """Display dataframe in the treeview"""
        # Clear existing data
        self.tree.delete(*self.tree.get_children())

        if df.empty:
            return

        # Setup columns
        self.tree["columns"] = list(df.columns)
        self.tree["show"] = "headings"

        for col in df.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor="w")

        # Insert data (limited to max_rows)
        display_df = df.head(max_rows)
        for index, row in display_df.iterrows():
            self.tree.insert("", "end", values=list(row))

    def get_current_dataframe(self) -> pd.DataFrame:
        """Get the currently loaded dataframe"""
        return self.current_df


class ProcessingControls(ctk.CTkFrame):
    """Processing controls component"""

    def __init__(self, parent, process_callback: Callable):
        super().__init__(parent)
        self.process_callback = process_callback

        # Configure grid
        self.grid_columnconfigure(1, weight=1)

        # Model selection
        model_label = ctk.CTkLabel(self, text="Model:", font=ctk.CTkFont(weight="bold"))
        model_label.grid(row=1, column=0, sticky="w", pady=10, padx=(10, 10))

        self.model_combo = ctk.CTkComboBox(
            self,
            values=["qwen3:14b", "qwen3:32b", "llama3.2:latest", "gpt-oss:20b"],
            width=200
        )
        self.model_combo.grid(row=1, column=1, sticky="w", pady=10)
        self.model_combo.set("qwen3:14b")

        # Output filename
        filename_label = ctk.CTkLabel(self, text="Output Filename:", font=ctk.CTkFont(weight="bold"))
        filename_label.grid(row=0, column=0, sticky="w", pady=10, padx=(10, 10))

        self.filename_entry = ctk.CTkEntry(self, width=200, placeholder_text="processed_data")
        self.filename_entry.grid(row=0, column=1, sticky="w", pady=10)
        self.filename_entry.insert(0, "processed_data")

        # Process button
        self.process_btn = ctk.CTkButton(
            self,
            text="🚀 Process Data",
            command=self.process_callback,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=40,
            width=200
        )
        self.process_btn.grid(row=2, column=0, columnspan=2, pady=20)

    def get_model(self) -> str:
        return self.model_combo.get()

    def get_filename(self) -> str:
        return self.filename_entry.get()

    def set_processing_state(self, processing: bool):
        if processing:
            self.process_btn.configure(state="disabled", text="Processing...")
        else:
            self.process_btn.configure(state="normal", text="🚀 Process Data")


class StatusDisplay(ctk.CTkFrame):
    """Status and progress display component"""

    def __init__(self, parent):
        super().__init__(parent)

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self, width=400)
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=10, padx=20)
        self.progress_bar.set(0)

        # Status label
        self.status_label = ctk.CTkLabel(self, text="Ready", font=ctk.CTkFont(size=12))
        self.status_label.grid(row=1, column=0, pady=5)

        # Configure grid
        self.grid_columnconfigure(0, weight=1)

    def update_progress(self, progress: float):
        """Update progress bar (0.0 to 1.0)"""
        self.progress_bar.set(progress)

    def update_status(self, status: str):
        """Update status message"""
        self.status_label.configure(text=status)

    def reset(self):
        """Reset to initial state"""
        self.progress_bar.set(0)
        self.status_label.configure(text="Ready")


class ProcessingSummary(ctk.CTkFrame):
    """Processing summary component showing statistics"""

    def __init__(self, parent):
        super().__init__(parent)

        # Configure grid
        self.grid_columnconfigure((0, 1), weight=1)

        # Title
        title = ctk.CTkLabel(self, text="Processing Summary", font=ctk.CTkFont(size=16, weight="bold"))
        title.grid(row=0, column=0, columnspan=2, pady=(10, 15), sticky="w", padx=10)

        # Left column stats
        self.rows_processed_label = ctk.CTkLabel(self, text="Rows Processed: --", font=ctk.CTkFont(size=12))
        self.rows_processed_label.grid(row=1, column=0, sticky="w", padx=10, pady=2)

        self.processing_time_label = ctk.CTkLabel(self, text="Processing Time: --", font=ctk.CTkFont(size=12))
        self.processing_time_label.grid(row=2, column=0, sticky="w", padx=10, pady=2)

        self.chunks_label = ctk.CTkLabel(self, text="Chunks Processed: --", font=ctk.CTkFont(size=12))
        self.chunks_label.grid(row=3, column=0, sticky="w", padx=10, pady=2)

    def update_summary(self,
                       rows_processed: int,
                       processing_time: float,
                       chunks_processed: int,
                       result_df: pd.DataFrame):
        """Update summary with processing results"""

        # Basic processing stats
        self.rows_processed_label.configure(text=f"Rows Processed: {rows_processed:,}")
        self.processing_time_label.configure(text=f"Processing Time: {processing_time / 60:.1f} minutes")
        self.chunks_label.configure(text=f"Chunks Processed: {chunks_processed}")

        # if not result_df.empty:
        #     try:
        #         # Convert to numeric for calculations
        #         result_df_numeric = result_df.copy()
        #         for col in ['Daily Frequency', 'Dose', 'Duration']:
        #             result_df_numeric[col] = pd.to_numeric(result_df_numeric[col], errors='coerce')
        #
        #         # Calculate averages
        #         avg_dose = result_df_numeric['Dose'].mean()
        #         avg_frequency = result_df_numeric['Daily Frequency'].mean()
        #
        #         # Calculate success rate (non-zero values)
        #         non_zero_doses = (result_df_numeric['Dose'] > 0).sum()
        #         success_rate = (non_zero_doses / len(result_df_numeric)) * 100 if len(result_df_numeric) > 0 else 0
        #
        #
        #     except Exception as e:
        #         print(f"Error calculating summary stats: {e}")
        #         self.avg_dose_label.configure(text="Avg Dose: Error")
        #         self.avg_frequency_label.configure(text="Avg Frequency: Error")
        #         self.success_rate_label.configure(text="Success Rate: Error")
        # else:
        #     self.avg_dose_label.configure(text="Avg Dose: No data")
        #     self.avg_frequency_label.configure(text="Avg Frequency: No data")
        #     self.success_rate_label.configure(text="Success Rate: No data")

    def reset(self):
        """Reset all summary values"""
        self.rows_processed_label.configure(text="Rows Processed: --")
        self.processing_time_label.configure(text="Processing Time: --")
        self.chunks_label.configure(text="Chunks Processed: --")
        # self.avg_dose_label.configure(text="Avg Dose: --")
        # self.avg_frequency_label.configure(text="Avg Frequency: --")
        # self.success_rate_label.configure(text="Success Rate: --")


class SettingsPanel(ctk.CTkFrame):
    """Settings panel component"""

    def __init__(self, parent):
        super().__init__(parent)

        # Configure grid
        self.grid_columnconfigure(1, weight=1)

        # Appearance mode setting
        appearance_label = ctk.CTkLabel(self, text="Appearance:", font=ctk.CTkFont(weight="bold"))
        appearance_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        self.appearance_combo = ctk.CTkComboBox(
            self,
            values=["System", "Dark", "Light"],
            command=self._change_appearance_mode,
            width=120
        )
        self.appearance_combo.grid(row=0, column=1, padx=20, pady=10, sticky="w")
        self.appearance_combo.set("Dark")

    def _change_appearance_mode(self, mode: str):
        """Change appearance mode"""
        ctk.set_appearance_mode(mode)
