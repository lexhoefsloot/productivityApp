#!/usr/bin/env python3
"""
Test script for Screenshot to Todoist API integrations
This script tests the Claude Vision API and Todoist API integrations
"""

import os
import sys
import base64
import argparse
import anthropic
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get API keys from environment variables
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
TODOIST_API_KEY = os.getenv("TODOIST_API_KEY")

# Claude prompt for task analysis
CLAUDE_PROMPT = """
Below is an image of a task. Please analyze the image and determine the task's title in no more than 5-7 words. Also, estimate the required time to complete this task and express it in a two-digit format where the first digit is the number of hours and the second digit is the number of tens of minutes (e.g., '02' means 0 hours and 20 minutes). Return your answer strictly in the following format:

XY: *Title of Task*

For example, if the task takes 20 minutes and is 'Buy groceries', you should output:
02: Buy groceries

Now, please analyze the following image and provide the result.
"""

def test_claude_api(image_path):
    """Test the Claude Vision API integration"""
    print("Testing Claude Vision API...")
    
    if not ANTHROPIC_API_KEY:
        print("Error: ANTHROPIC_API_KEY not found in .env file")
        return False
    
    try:
        # Initialize Anthropic client
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        # Read the image file
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()
        
        # Convert image to base64
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        # Determine MIME type based on file extension
        mime_type = "image/jpeg"  # Default
        if image_path.lower().endswith(".png"):
            mime_type = "image/png"
        elif image_path.lower().endswith(".gif"):
            mime_type = "image/gif"
        elif image_path.lower().endswith(".webp"):
            mime_type = "image/webp"
        
        # Call Claude Vision API
        print("Sending image to Claude Vision API...")
        message = client.messages.create(
            model="claude-3-7-sonnet-20250219",  # Use the latest Claude model with vision capabilities
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": base64_image,
                            },
                        },
                        {
                            "type": "text",
                            "text": CLAUDE_PROMPT
                        }
                    ],
                }
            ],
        )
        
        # Extract the response text
        response_text = message.content[0].text
        print(f"Claude response: {response_text}")
        
        # Clean up the response (remove any extra text, just get the task format)
        # The response should be in the format "XY: *Task Title*"
        response_lines = response_text.strip().split('\n')
        task_info = None
        for line in response_lines:
            # Look for a line that matches our expected format
            if len(line) >= 5 and line[0].isdigit() and line[1].isdigit() and line[2:4] == ": ":
                task_info = line.strip()
                break
        
        if task_info:
            print(f"Extracted task info: {task_info}")
            return task_info
        else:
            print("Warning: Could not extract task info in the expected format")
            return response_text.strip()
        
    except Exception as e:
        print(f"Error testing Claude API: {str(e)}")
        return False

def test_todoist_api(task_info):
    """Test the Todoist API integration"""
    print("\nTesting Todoist API...")
    
    if not TODOIST_API_KEY:
        print("Error: TODOIST_API_KEY not found in .env file")
        return False
    
    try:
        # Todoist API endpoint
        url = "https://api.todoist.com/rest/v2/tasks"
        
        # Headers with authentication
        headers = {
            "Authorization": f"Bearer {TODOIST_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Task data
        data = {
            "content": task_info,
            "due_string": "today"  # Default due date is today
        }
        
        # Make the request to create the task
        print(f"Creating Todoist task: {task_info}")
        response = requests.post(url, headers=headers, json=data)
        
        # Check if the request was successful
        if response.status_code == 200:
            print("Todoist task created successfully!")
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"Error creating Todoist task: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Error testing Todoist API: {str(e)}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Test Claude Vision and Todoist API integrations")
    parser.add_argument("image_path", help="Path to the image file to test")
    parser.add_argument("--skip-todoist", action="store_true", help="Skip Todoist API test")
    
    args = parser.parse_args()
    
    # Check if the image file exists
    if not os.path.isfile(args.image_path):
        print(f"Error: Image file not found: {args.image_path}")
        sys.exit(1)
    
    # Test Claude Vision API
    task_info = test_claude_api(args.image_path)
    
    if not task_info:
        print("Claude Vision API test failed")
        sys.exit(1)
    
    # Test Todoist API if not skipped
    if not args.skip_todoist:
        success = test_todoist_api(task_info)
        
        if not success:
            print("Todoist API test failed")
            sys.exit(1)
    
    print("\nAll tests completed successfully!")

if __name__ == "__main__":
    main() 