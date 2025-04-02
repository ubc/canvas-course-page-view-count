# Canvas Course Page View Count

This tool retrieves the daily page view counts for each student in specified courses and outputs the data to CSV files.

## Features

- Extract daily page view statistics for all students in Canvas courses
- Search for courses by name or specify course IDs directly
- Process multiple courses concurrently with multithreading
- Automatic pagination for handling large data sets
- Proper rate limiting to avoid API throttling

## Requirements

- Python 3.6+
- Canvas API access token with appropriate permissions
- Canvas instance with analytics data available

## Setup

### 1. Clone the Repository

### 2. Create a Virtual Environment

#### On Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

#### On macOS/Linux:

```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

Once your virtual environment is activated (you should see `(venv)` at the beginning of your command prompt), install the required packages:

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the root directory of the project with the following variables:

```
CANVAS_API_KEY=your_canvas_api_token_here
CANVAS_BASE_URL=https://your-institution.instructure.com/api/v1
```

## Usage

### Basic Usage

```bash
python index.py
```

This will search for all courses in the root account and process them.

### Command Line Arguments

```
--subaccount SUBACCOUNT   Canvas subaccount ID (default: "self" for root account)
--search SEARCH           Search term to filter courses
--output-dir OUTPUT_DIR   Directory to save output files (default: output)
--threads THREADS         Number of concurrent threads (default: 3)
--course-ids COURSE_IDS   Specific course IDs to process (overrides search)
```

### Examples

#### Process specific courses:

```bash
python index.py --course-ids 1234 5678
```

#### Search for courses with a keyword:

```bash
python index.py --search "Spring 2025"
```

#### Process courses in a specific subaccount:

```bash
python index.py --subaccount 10 --search "Spring"
```

#### Customize output directory:

```bash
python index.py --output-dir "analytics_data"
```

#### Set number of concurrent processes:

```bash
python index.py --threads 5
```

## Output

For each course processed, a CSV file will be created in the output directory with the naming pattern `{course_id}_{course_name}_activity.csv`.

The CSV contains the following columns:
- `student_id`: Canvas user ID of the student
- `student_name`: Name of the student
- `date`: Date of activity in ISO format (YYYY-MM-DD)
- `page_views`: Number of page views on that date

## Troubleshooting

### API Access Issues

If you encounter errors related to API access:

1. Ensure your Canvas API token has the necessary permissions
2. Verify that the Canvas Base URL is correct and includes `/api/v1` at the end
3. Check that you have access to the courses you're trying to process

### Rate Limiting

The script includes built-in rate limiting, but if you still encounter rate limit errors:

1. Decrease the number of concurrent threads
2. Add additional delay between requests by modifying the `time.sleep(0.2)` value in the `make_request` function

### Missing Analytics Data

If you're not seeing any analytics data for students:

1. Verify that analytics are enabled for your Canvas instance
2. Check if you have the appropriate permissions to access analytics data

## Roll up the page views by day
The `process_into_page_views_by_day.py` script will process the CSVs to roll up the views by day instead of by hour.

```bash
python process_into_page_views_by_day.py output --output_dir processed
```

## License

This project is licensed under the AGPL-3.0 license.
