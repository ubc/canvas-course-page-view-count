import os
import pandas as pd
from datetime import datetime
import pytz
from pathlib import Path
from functools import partial
from typing import List, Dict, Any

def convert_to_vancouver_time(timestamp: str) -> datetime:
    """Convert UTC timestamp to Vancouver local time."""
    # Parse the ISO format timestamp
    dt = pd.to_datetime(timestamp)

    # If timezone not specified in string, assume UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.UTC)

    # Convert to Vancouver time zone
    vancouver_tz = pytz.timezone('America/Vancouver')
    return dt.astimezone(vancouver_tz)

def process_csv(file_path: str, output_dir: str) -> None:
    """
    Process a single CSV file:
    1. Convert timestamps to Vancouver time
    2. Group by student_id, student_name, day and sum page_views
    3. Handle empty files gracefully
    """
    # Read the CSV
    df = pd.read_csv(file_path)

    # Check if the dataframe is empty
    if df.empty:
        print(f"Warning: {os.path.basename(file_path)} is empty. Creating empty output file.")
        # Create output filename
        input_filename = os.path.basename(file_path)
        output_filename = f"processed_{input_filename}"
        output_path = os.path.join(output_dir, output_filename)

        # Create an empty file with the expected headers
        pd.DataFrame(columns=['student_id', 'student_name', 'day', 'page_views']).to_csv(output_path, index=False)
        return

    # Convert date column to Vancouver time
    df['vancouver_time'] = df['date'].apply(convert_to_vancouver_time)

    # Extract date part only (no time)
    df['day'] = df['vancouver_time'].dt.date

    # Group by student_id, student_name, and day, then sum page_views
    result = df.groupby(['student_id', 'student_name', 'day'], as_index=False)['page_views'].sum()

    # Create output filename
    input_filename = os.path.basename(file_path)
    output_filename = f"processed_{input_filename}"
    output_path = os.path.join(output_dir, output_filename)

    # Save the result
    result.to_csv(output_path, index=False)
    print(f"Processed {input_filename} -> {output_filename}")

def process_directory(input_dir: str, output_dir: str) -> None:
    """Process all CSV files in the given directory."""
    # Make output_dir a relative path if it's an absolute path
    if output_dir.startswith('/'):
        # Convert to a subdirectory of current working directory
        original_path = output_dir
        output_dir = os.path.join(os.getcwd(), output_dir.lstrip('/'))
        print(f"Changing output directory from '{original_path}' to '{output_dir}' to avoid permission issues")

    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Get all CSV files
    csv_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.csv')]

    if not csv_files:
        print(f"No CSV files found in {input_dir}")
        return

    # Process each CSV file
    for csv_file in csv_files:
        file_path = os.path.join(input_dir, csv_file)
        try:
            process_csv(file_path, output_dir)
        except Exception as e:
            print(f"Error processing {csv_file}: {str(e)}")

    print(f"All {len(csv_files)} CSV files processed successfully.")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Process CSV files with student data")
    parser.add_argument("input_dir", help="Directory containing CSV files to process")
    parser.add_argument("--output_dir", default="processed_output",
                        help="Directory for output CSV files (default: processed_output)")

    args = parser.parse_args()

    process_directory(args.input_dir, args.output_dir)