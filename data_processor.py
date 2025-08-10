"""
Data processing logic for pharmaceutical data extraction.
"""
import pandas as pd
import numpy as np
import math
from typing import Callable, Optional, List, Tuple
from dataclasses import dataclass

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_core.prompts import ChatPromptTemplate


@dataclass
class ProcessingConfig:
    """Configuration for data processing"""
    model_num: int
    chunk_size: int = 10
    vector_db_path: str = "./chroma_db"
    similarity_search_k: int = 3


class DataProcessor:
    """Handles the core data processing logic"""

    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.vectorstore = None
        self.model = None

    def choose_model(self, model_num):
        models = ["qwen3:14b", "qwen3:32b", "llama3.2:latest", "gpt-oss:20b"]
        model = ChatOllama(model=models[model_num])
        return model

    def initialize_rag_system(self):
        """Initialize the RAG system components"""

        # Initialize RAG components
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        self.vectorstore = Chroma(
            persist_directory=self.config.vector_db_path,
            embedding_function=embeddings
        )

        # Initialize model
        self.model = self.choose_model(self.config.model_num)

    def load_data(self, file_path: str) -> pd.DataFrame:
        """Load data from Excel file"""
        return pd.read_excel(file_path)

    def split_data_into_chunks(self, df: pd.DataFrame) -> List[pd.DataFrame]:
        """Split dataframe into processing chunks"""
        chunk_amount = math.ceil(len(df) / self.config.chunk_size)
        return np.array_split(df, chunk_amount)

    def process_data(self, file_path: str, progress_callback: Optional[Callable] = None) -> pd.DataFrame:
        """
        Main processing method

        Args:
            file_path: Path to input Excel file
            progress_callback: Optional callback function for progress updates

        Returns:
            Processed DataFrame with extracted data
        """
        # Initialize systems
        if progress_callback:
            progress_callback("Initializing RAG system...")
        self.initialize_rag_system()

        # Load and split data
        if progress_callback:
            progress_callback("Loading data...")
        raw_data_df = self.load_data(file_path)
        chunks = self.split_data_into_chunks(raw_data_df)

        # Process chunks
        results = []
        for i, chunk in enumerate(chunks):
            if progress_callback:
                progress = (i / len(chunks))
                progress_callback(f"Processing chunk {i + 1} of {len(chunks)}...", progress)

            try:
                result = self._process_chunk(chunk)
                results.append(result)
            except Exception as e:
                print(f"Error processing chunk {i}: {e}")
                continue

        # Parse and return results
        if progress_callback:
            progress_callback("Finalizing results...")
        return self._parse_results(results)

    def _process_chunk(self, chunk: pd.DataFrame) -> 'ChainResult':
        """Process a single chunk of data"""

        # Convert chunk to searchable text
        chunk_text = "\n".join(
            " | ".join(str(cell).replace("\n", " ") for cell in row)
            for row in chunk.values
        )

        # Get reference examples from RAG
        reference_examples = self._get_reference_examples(chunk_text)

        # Create and invoke chain
        chain = self._create_processing_chain()
        result = chain.invoke({
            "data": chunk_text,
            "reference": reference_examples,
            "prompt": self._get_extraction_prompt(),
            "format": self._get_format_instructions()
        })

        return result

    def _get_reference_examples(self, chunk_text: str) -> str:
        """Get reference examples from vector store"""
        try:
            docs = self.vectorstore.similarity_search(chunk_text, k=self.config.similarity_search_k)

            examples = []
            for doc in docs:
                metadata = doc.metadata
                example = (
                    f"Example Input: Raw Antibiotic: '{metadata.get('raw_antibiotic_name', '')}' | "
                    f"Raw Dose: '{metadata.get('raw_dose_quantity', '')}' | "
                    f"Instructions: '{metadata.get('patient_instructions', '')}'\n"
                    f"Extracted Output: "
                    f"Daily Frequency: {metadata.get('clean_frequency', 0)}, "
                    f"Dose: {metadata.get('clean_dose', 0)}mg, "
                    f"Duration: {metadata.get('clean_duration', 0)} days\n"
                )
                examples.append(example)

            return "\n".join(examples)

        except Exception as e:
            print(f"Error in similarity search: {e}")
            return "No reference data available"

    def _create_processing_chain(self):
        """Create the LLM processing chain"""


        template = """
        You are an expert pharmaceutical data analyst specializing in extracting dosage information from patient instructions.

        Here is the raw data to process: {data}
        Here are relevant reference examples from similar cases: {reference}
        Task: {prompt}
        Output format: {format}

        Important Instructions:
        - Use the reference examples to understand how similar raw data was processed
        - Extract daily frequency (how many times per day), dose amount in mg, and duration in days
        - Look for patterns in the reference examples that match your input data
        - If there is an exact match in the reference examples use that, otherwise do your best to determine what the 
          correct values are based on the other examples in the reference
        - If uncertain about any value, use 0
        - Focus on numerical extraction only
        """

        prompt = ChatPromptTemplate.from_template(template)
        return prompt | self.model

    def _get_extraction_prompt(self) -> str:
        """Get the extraction prompt"""
        return (
            "For every row in the data extract the daily frequency, dose amount in mg, and duration values in numeric values. "
            "Use the reference examples to understand the correct patterns for extraction. "
            "If there are any values you are unsure of, put a 0. /no think"
        )

    def _get_format_instructions(self) -> str:
        """Get format instructions"""
        return "Comma separated list with daily frequency, dose amount in mg, and duration values. No units. New line after every row."

    def _parse_results(self, results: List) -> pd.DataFrame:
        """Parse LLM results into final DataFrame"""
        parsed_rows = []
        for result in results:
            lines = result.content.strip().split("\n")
            for line in lines:
                values = [v.strip() for v in line.split(",")]
                if len(values) == 3:
                    parsed_rows.append(values)

        return pd.DataFrame(parsed_rows, columns=['Daily Frequency', 'Dose', 'Duration'])

    def save_results(self, df: pd.DataFrame, output_path: str):
        """Save results to Excel file"""
        df.to_excel(output_path, index=False)