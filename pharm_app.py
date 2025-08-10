import customtkinter as ctk
import pandas as pd
import threading
import os
import math
import time
from tkinter import messagebox

from data_processor import DataProcessor, ProcessingConfig
from ui_components import FileSelectionPanel, DataPreview, ProcessingControls, StatusDisplay, ProcessingSummary, SettingsPanel


class PharmApp:
    """Main application class"""

    def __init__(self, root):
        self.root = root
        self.root.title("CHARM Data Processor")
        self.root.geometry("900x800")

        # Initialize state
        self.processing = False
        self.output_path = ""

        # Setup UI
        self.setup_gui()

        # Setup appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

    def setup_gui(self):
        """Setup the main GUI layout"""
        # Configure root grid
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # Main scrollable frame
        main_frame = ctk.CTkScrollableFrame(self.root)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main_frame.grid_columnconfigure(0, weight=1)

        # Title
        title = ctk.CTkLabel(
            main_frame,
            text="CHARM Data Processor",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, pady=(0, 30))

        # File selection panel (aligned inputs)
        self.file_panel = FileSelectionPanel(main_frame, self.on_file_selected)
        self.file_panel.grid(row=1, column=0, sticky="ew", pady=10)

        # Processing controls (output filename above model selection)
        self.controls = ProcessingControls(main_frame, self.start_processing)
        self.controls.grid(row=2, column=0, sticky="ew", pady=10)

        # Status display
        self.status_display = StatusDisplay(main_frame)
        self.status_display.grid(row=3, column=0, sticky="ew", pady=10)

        # Data preview (shows top 20 rows automatically)
        self.data_preview = DataPreview(main_frame)
        self.data_preview.grid(row=4, column=0, sticky="nsew", pady=10)
        main_frame.grid_rowconfigure(4, weight=1)

        # Processing summary
        self.summary = ProcessingSummary(main_frame)
        self.summary.grid(row=5, column=0, sticky="ew", pady=10)

        # Output controls
        output_frame = ctk.CTkFrame(main_frame)
        output_frame.grid(row=6, column=0, sticky="ew", pady=10)

        self.open_btn = ctk.CTkButton(
            output_frame,
            text="📂 Open Output File",
            command=self.open_output_file,
            state="disabled",
            font=ctk.CTkFont(size=14)
        )
        self.open_btn.pack(pady=15)

        # Settings panel
        self.settings = SettingsPanel(main_frame)
        self.settings.grid(row=7, column=0, sticky="ew", pady=20)

    def on_file_selected(self, file_path: str):
        """Handle file selection - load and preview data"""
        success, message = self.data_preview.load_from_file(file_path)
        if success:
            self.status_display.update_status(message)
        else:
            self.status_display.update_status(message)

        # Reset summary when new file is loaded
        self.summary.reset()


    def start_processing(self):
        """Start the data processing"""
        # Validation
        input_path = self.file_panel.get_input_path()
        output_dir = self.file_panel.get_output_path()

        if not input_path or not output_dir:
            messagebox.showerror("Error", "Please select input file and output directory")
            return

        if not os.path.exists("./chroma_db"):
            messagebox.showerror("Error", "RAG database not found. Run rag_setup.py first.")
            return

        # Setup processing state
        self.processing = True
        self.controls.set_processing_state(True)
        self.status_display.update_status("Initializing...")
        self.status_display.update_progress(0)

        # Start processing thread
        thread = threading.Thread(target=self.process_data_thread)
        thread.daemon = True
        thread.start()

    def process_data_thread(self):
        """Process data in separate thread"""
        start_time = time.time()
        try:
            # Setup configuration
            model_map = {"qwen3:14b": 0, "qwen3:32b": 1, "llama3.2:latest": 2, "gpt-oss:20b": 3}
            config = ProcessingConfig(
                model_num=model_map.get(self.controls.get_model(), 0),
                chunk_size=10,
                vector_db_path="./chroma_db"
            )

            # Create processor
            processor = DataProcessor(config)

            # Process data with progress callback
            def progress_callback(status: str, progress: float = None):
                self.root.after(0, lambda: self.status_display.update_status(status))
                if progress is not None:
                    self.root.after(0, lambda: self.status_display.update_progress(progress))

            result_df = processor.process_data(
                self.file_panel.get_input_path(),
                progress_callback
            )

            # Save results
            filename = self.controls.get_filename() + ".xlsx"
            self.output_path = os.path.join(self.file_panel.get_output_path(), filename)
            processor.save_results(result_df, self.output_path)

            # Calculate processing statistics
            end_time = time.time()
            processing_time = end_time - start_time
            input_df = self.data_preview.get_current_dataframe()
            rows_processed = len(input_df)
            chunks_processed = math.ceil(rows_processed / config.chunk_size)

            # Update UI with results
            self.root.after(0, lambda: self.processing_complete(result_df, processing_time, rows_processed,
                                                                chunks_processed))

        except Exception as e:
            error_msg = f"Error during processing: {e}"
            self.root.after(0, lambda: self.processing_error(error_msg))

    def processing_complete(self, result_df: pd.DataFrame, processing_time: float, rows_processed: int, chunks_processed: int):
        """Handle processing completion"""
        self.status_display.update_progress(1.0)
        self.status_display.update_status(f"✅ Processing complete! Processed {len(result_df)} rows.")

        # Show results in preview
        self.data_preview.display_dataframe(result_df, max_rows=20)

        # Update summary with statistics
        self.summary.update_summary(rows_processed, processing_time, chunks_processed, result_df)

        # Enable output button
        self.open_btn.configure(state="normal")

        # Reset processing state
        self.processing = False
        self.controls.set_processing_state(False)

    def processing_error(self, error_msg: str):
        """Handle processing error"""
        messagebox.showerror("Processing Error", error_msg)
        self.status_display.update_status("❌ Error occurred")

        # Reset processing state
        self.processing = False
        self.controls.set_processing_state(False)

    def open_output_file(self):
        """Open the output file"""
        if self.output_path and os.path.exists(self.output_path):
            os.startfile(self.output_path)  # Windows
        else:
            messagebox.showerror("Error", "Output file not found")


def main():
    """Main entry point"""
    root = ctk.CTk()
    app = PharmApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
