"""
RAG Setup Script for Pharmaceutical Data Extraction
Run this script once to build your vector database from the reference Excel file.
"""

import pandas as pd
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document
import os


def build_vector_db(reference_excel_path, persist_directory="./chroma_db"):
    """
    Build vector database from reference Excel with pharmaceutical data columns:
    - raw_antibiotic_name
    - raw_dose_quantity
    - patient_instructions
    - clean_antibiotic_name
    - clean_dose
    - clean_unit_of_measure
    - clean_frequency
    - clean_duration
    """

    print(f"Loading reference data from: {reference_excel_path}")

    # Load your large reference dataset
    ref_df = pd.read_excel(reference_excel_path)
    print(f"Loaded {len(ref_df)} reference rows")

    # Display column info
    print("Available columns:", list(ref_df.columns))

    # Create documents from each row
    documents = []
    valid_rows = 0

    for idx, row in ref_df.iterrows():
        try:
            # Combine relevant columns into searchable text
            content = f"Raw Antibiotic: {row.get('raw_antibiotic_name', '')} | " \
                      f"Raw Dose: {row.get('raw_dose_quantity', '')} | " \
                      f"Patient Instructions: {row.get('patient_instructions', '')} | " \
                      f"Clean Antibiotic: {row.get('clean_antibiotic_name', '')} | " \
                      f"Clean Dose: {row.get('clean_dose', '')} | " \
                      f"Unit: {row.get('clean_unit_of_measure', '')} | " \
                      f"Frequency: {row.get('clean_frequency', '')} | " \
                      f"Duration: {row.get('clean_duration', '')}"

            # Store the clean extracted values in metadata for easy retrieval
            # Convert to appropriate types and handle NaN values
            clean_dose = row.get('clean_dose', 0)
            clean_frequency = row.get('clean_frequency', 0)
            clean_duration = row.get('clean_duration', 0)

            # Convert NaN to 0 for numeric fields
            if pd.isna(clean_dose):
                clean_dose = 0
            if pd.isna(clean_frequency):
                clean_frequency = 0
            if pd.isna(clean_duration):
                clean_duration = 0

            metadata = {
                'row_id': idx,
                'raw_antibiotic_name': str(row.get('raw_antibiotic_name', '')),
                'raw_dose_quantity': str(row.get('raw_dose_quantity', '')),
                'patient_instructions': str(row.get('patient_instructions', '')),
                'clean_antibiotic_name': str(row.get('clean_antibiotic_name', '')),
                'clean_dose': float(clean_dose),
                'clean_unit_of_measure': str(row.get('clean_unit_of_measure', '')),
                'clean_frequency': float(clean_frequency),
                'clean_duration': float(clean_duration),
            }

            documents.append(Document(page_content=content, metadata=metadata))
            valid_rows += 1

        except Exception as e:
            print(f"Error processing row {idx}: {e}")
            continue

    print(f"Successfully processed {valid_rows} rows into documents")

    if not documents:
        raise ValueError("No valid documents created. Check your Excel file structure.")

    # Create embeddings and vector store
    print("Creating embeddings and building vector database...")
    embeddings = OllamaEmbeddings(model="nomic-embed-text")

    # Remove existing directory if it exists
    if os.path.exists(persist_directory):
        import shutil
        shutil.rmtree(persist_directory)
        print(f"Removed existing vector database at {persist_directory}")

    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=persist_directory
    )

    print(f"Vector database created successfully with {len(documents)} reference examples")
    print(f"Database saved to: {persist_directory}")

    return vectorstore


def test_vector_db(persist_directory="./chroma_db", test_query="amoxicillin 500mg twice daily"):
    """Test the vector database with a sample query"""

    print(f"\nTesting vector database with query: '{test_query}'")

    try:
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        vectorstore = Chroma(
            persist_directory=persist_directory,
            embedding_function=embeddings
        )

        # Search for similar examples
        docs = vectorstore.similarity_search(test_query, k=3)

        print(f"Found {len(docs)} similar examples:")
        for i, doc in enumerate(docs, 1):
            metadata = doc.metadata
            print(f"\nExample {i}:")
            print(f"  Raw: {metadata.get('raw_antibiotic_name', '')} - {metadata.get('raw_dose_quantity', '')}")
            print(f"  Instructions: {metadata.get('patient_instructions', '')}")
            print(f"  Extracted -> Freq: {metadata.get('clean_frequency', 0)}, Dose: {metadata.get('clean_dose', 0)}mg, Duration: {metadata.get('clean_duration', 0)} days")

        return True

    except Exception as e:
        print(f"Error testing vector database: {e}")
        return False


if __name__ == "__main__":
    reference_file_path = input("Enter the file path of your reference file: ")

    # Check if file exists
    if not os.path.exists(reference_file_path):
        print(f"Reference file not found: {reference_file_path}")
        print("Please update the reference_file_path variable with the correct path to your reference Excel file.")
        exit(1)

    try:
        # Build the vector database
        vectorstore = build_vector_db(reference_file_path)

        # Test the database
        test_success = test_vector_db()

        if test_success:
            print("\n✅ RAG system setup completed successfully!")
            print("You can now use the updated callingllm.py with RAG functionality.")
        else:
            print("\n❌ RAG system setup completed but testing failed.")

    except Exception as e:
        print(f"\n❌ Error setting up RAG system: {e}")
        print("Please check your reference Excel file structure and try again.")