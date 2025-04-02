import os
import csv
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import time
import argparse
from dotenv import load_dotenv

def make_request(base_url: str, headers: Dict[str, str], endpoint: str,
                params: Optional[Dict[str, Any]] = None, timeout: int = 30) -> List[Dict[str, Any]]:
    """
    Make a GET request to the Canvas API with automatic pagination.

    Args:
        base_url: Canvas API base URL
        headers: Request headers including authorization
        endpoint: API endpoint
        params: Query parameters
        timeout: Request timeout in seconds

    Returns:
        List of response items
    """
    url = f"{base_url}/{endpoint}"
    original_params = params or {}
    current_params = original_params.copy()  # Create a copy to modify

    all_items = []
    page_count = 0

    while url:
        try:
            page_count += 1
            # For logging, show the base URL and some key parameters if present
            log_url = url.split('?')[0]
            param_log = []
            if 'start_time' in current_params:
                param_log.append(f"start_time={current_params['start_time']}")
            if 'end_time' in current_params:
                param_log.append(f"end_time={current_params['end_time']}")
            if 'search_term' in current_params:
                param_log.append(f"search_term={current_params['search_term']}")
            if param_log:
                print(f"Requesting page {page_count}: {log_url} with {', '.join(param_log)}")
            else:
                print(f"Requesting page {page_count}: {log_url}")

            response = requests.get(url, headers=headers, params=current_params, timeout=timeout)
            response.raise_for_status()

            # Check if response is empty
            content = response.text
            if not content.strip():
                print(f"Warning: Empty response received from {url}")
                break

            # Try to parse the JSON
            try:
                data = response.json()
                items = data if isinstance(data, list) else [data]
                all_items.extend(items)
                print(f"Received {len(items)} items from page {page_count}")
            except ValueError as e:
                print(f"Error parsing JSON from {url}: {str(e)}")
                print(f"Response content (first 200 chars): {content[:200]}")
                raise

            # Check for pagination
            links = response.links if hasattr(response, 'links') else {}
            next_link = links.get('next', {}).get('url')

            # If we have a next page, set the URL but clear params since they're included in the URL
            if next_link:
                url = next_link
                current_params = {}  # Clear params for next request
            else:
                break

        except requests.exceptions.Timeout:
            print(f"Request timed out for {url}")
            print("Continuing to next request...")
            break
        except requests.exceptions.RequestException as e:
            print(f"Request error for {url}: {str(e)}")
            raise

        # Rate limiting to avoid API throttling
        time.sleep(0.2)

    return all_items

def get_courses_by_search(base_url: str, headers: Dict[str, str],
                         subaccount_id: str, search_term: str = None) -> List[Dict[str, Any]]:
    """
    Get courses by searching in a specific subaccount.

    Args:
        base_url: Canvas API base URL
        headers: Request headers
        subaccount_id: Canvas subaccount ID (use 'self' for the root account)
        search_term: Optional search term to filter courses

    Returns:
        List of courses matching the search criteria
    """
    params = {
        "per_page": 100,
        "include[]": ["term"]  # Include term information
    }

    # Add search term if provided
    if search_term:
        params["search_term"] = search_term

    endpoint = f"accounts/{subaccount_id}/courses"
    return make_request(base_url, headers, endpoint, params)

def get_course(base_url: str, headers: Dict[str, str], course_id: int) -> Dict[str, Any]:
    """
    Get course details.

    Args:
        base_url: Canvas API base URL
        headers: Request headers
        course_id: Canvas course ID

    Returns:
        Course details dictionary
    """
    result = make_request(base_url, headers, f"courses/{course_id}")

    # Handle different response types
    if not result:
        raise ValueError(f"No data returned for course {course_id}")

    # If we got a list, take the first item
    if isinstance(result, list):
        if not result:
            raise ValueError(f"Empty list returned for course {course_id}")
        return result[0]

    # If we got a dictionary, return it directly
    if isinstance(result, dict):
        return result

    # If we got something else (like a string), raise an error
    raise TypeError(f"Unexpected response type for course {course_id}: {type(result)}, value: {str(result)[:100]}")

def get_course_students(base_url: str, headers: Dict[str, str], course_id: int) -> List[Dict[str, Any]]:
    """
    Get all students in a course.

    Args:
        base_url: Canvas API base URL
        headers: Request headers
        course_id: Canvas course ID

    Returns:
        List of student details
    """
    return make_request(
        base_url,
        headers,
        f"courses/{course_id}/users",
        {"enrollment_type[]": "student", "per_page": 100}
    )

def get_student_activity(base_url: str, headers: Dict[str, str],
                       course_id: int, student_id: int, timeout: int = 60) -> Dict[str, Any]:
    """
    Get activity analytics for a student in a course.

    Args:
        base_url: Canvas API base URL
        headers: Request headers
        course_id: Canvas course ID
        student_id: Canvas user ID
        timeout: Request timeout in seconds

    Returns:
        Dictionary containing activity data
    """
    result = make_request(
        base_url,
        headers,
        f"courses/{course_id}/analytics/users/{student_id}/activity",
        timeout=timeout
    )

    # The result might be a list with one item or directly a dictionary
    if isinstance(result, list) and result:
        return result[0]
    return result

def process_course(course_id: int, base_url: str, headers: Dict[str, str], output_dir: str) -> None:
    """
    Process a single course to extract activity analytics for all students.

    Args:
        course_id: Canvas course ID
        base_url: Canvas API base URL
        headers: Request headers
        output_dir: Directory to save output files
    """
    try:
        print(f"Starting to process course {course_id}...")

        # Verify API connection first
        try:
            # Get course details
            course = get_course(base_url, headers, course_id)
            if not isinstance(course, dict):
                print(f"Error: Expected course data to be a dictionary, but got {type(course)}")
                print(f"Value: {str(course)[:100]}")
                return
        except Exception as e:
            print(f"Failed to get course {course_id} details: {str(e)}")
            print("This could be due to an invalid API key, incorrect base URL, or the course doesn't exist.")
            print("Ensure your .env file has a valid CANVAS_API_KEY and verify the course ID.")
            return

        course_name = course.get("name", f"unknown-{course_id}")

        # Clean course name for filename
        safe_name = "".join(c if c.isalnum() else "_" for c in course_name)
        filename = f"{course_id}_{safe_name}_activity.csv"
        output_path = os.path.join(output_dir, filename)

        # Get all students in the course
        print(f"Fetching students for course {course_id} ({course_name})...")
        students = get_course_students(base_url, headers, course_id)
        print(f"Processing {len(students)} students for course {course_id} ({course_name})")

        # Initialize CSV file with headers
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'student_id', 'student_name', 'date', 'page_views'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            # Process each student
            for i, student in enumerate(students):
                student_id = student['id']
                student_name = f"{student.get('name', 'Unknown')}"

                print(f"Processing student {i+1}/{len(students)}: {student_name} (ID: {student_id})")

                try:
                    # Get activity analytics for this student
                    activity_data = get_student_activity(base_url, headers, course_id, student_id)

                    # Check if we have view data
                    if not activity_data or not isinstance(activity_data, dict):
                        print(f"No activity data for student {student_name} (ID: {student_id})")
                        continue

                    page_views = activity_data.get('page_views', {})

                    if not page_views:
                        print(f"No page view data for student {student_name} (ID: {student_id})")
                        continue

                    # Write page views by date to CSV
                    for date, views in page_views.items():
                        writer.writerow({
                            'student_id': student_id,
                            'student_name': student_name,
                            'date': date,
                            'page_views': views
                        })

                    print(f"Recorded {len(page_views)} hours of activity for student {student_name}")

                except Exception as e:
                    print(f"Error processing student {student_name} (ID: {student_id}): {str(e)}")
                    print("Continuing to next student...")
                    continue

        print(f"Completed course {course_id} ({course_name}). Output saved to {output_path}")

    except Exception as e:
        print(f"Error processing course {course_id}: {str(e)}")

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Canvas API page view extractor.')
    parser.add_argument('--subaccount', default='self',
                        help='Canvas subaccount ID (default: "self" for root account)')
    parser.add_argument('--search', help='Search term to filter courses')
    parser.add_argument('--output-dir', default='output',
                        help='Directory to save output files (default: output)')
    parser.add_argument('--threads', type=int, default=3,
                        help='Number of concurrent threads (default: 3)')
    parser.add_argument('--course-ids', nargs='+', type=int,
                        help='Specific course IDs to process (overrides search)')
    args = parser.parse_args()

    # Load environment variables from .env file
    load_dotenv()

    # Get API key from environment variable
    api_key = os.getenv('CANVAS_API_KEY')
    if not api_key:
        raise ValueError("CANVAS_API_KEY environment variable not set. Please create a .env file with this variable.")

    base_url = os.getenv('CANVAS_BASE_URL')
    if not base_url:
        raise ValueError("CANVAS_BASE_URL environment variable not set. Please create a .env file with this variable.")

    output_dir = args.output_dir
    num_threads = args.threads

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Set up API authentication
    headers = {"Authorization": f"Bearer {api_key}"}

    # Get course IDs - either from command line or by searching
    course_ids = []

    if args.course_ids:
        course_ids = args.course_ids
        print(f"Using {len(course_ids)} course IDs provided via command line")
    else:
        print(f"Searching for courses in subaccount {args.subaccount}" +
              (f" with search term '{args.search}'" if args.search else ""))

        # Search for courses
        courses = get_courses_by_search(base_url, headers, args.subaccount, args.search)

        if not courses:
            print("No courses found matching the search criteria.")
            return

        # Print course details and collect IDs
        print(f"Found {len(courses)} courses:")
        for i, course in enumerate(courses):
            course_id = course.get('id')
            course_name = course.get('name', 'Unknown')
            term_name = course.get('term', {}).get('name', 'Unknown term')
            print(f"{i+1}. [{course_id}] {course_name} ({term_name})")
            course_ids.append(course_id)

    if not course_ids:
        print("No course IDs to process. Exiting.")
        return

    print(f"Processing {len(course_ids)} courses...")

    # Process courses in parallel
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        process_course_partial = partial(
            process_course,
            base_url=base_url,
            headers=headers,
            output_dir=output_dir
        )
        executor.map(process_course_partial, course_ids)

    print("All courses processed!")

if __name__ == "__main__":
    main()