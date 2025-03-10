#!/usr/bin/env python3
import os
import base64
import json
import logging
from flask import Flask, request, jsonify, send_from_directory
import requests
import anthropic
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("screenshot_to_todoist.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder='static')

# Get API keys from environment variables
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
TODOIST_API_KEY = os.getenv("TODOIST_API_KEY")

# Initialize Anthropic client - fix for compatibility issue
try:
    # Try the standard initialization first
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
except TypeError as e:
    if "unexpected keyword argument 'proxies'" in str(e):
        # If there's a proxies error, try without any additional parameters
        logger.warning("Detected incompatibility with Anthropic client. Using alternative initialization.")
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    else:
        # If it's a different error, re-raise it
        raise

# Claude prompt for task analysis
CLAUDE_PROMPT = """
Below is an image of a task. Please analyze the image and determine the task's title in no more than 5-7 words. Also, estimate the required time to complete this task and express it in a two-digit format where the first digit is the number of hours and the second digit is the number of tens of minutes (e.g., '02' means 0 hours and 20 minutes). Return your answer strictly in the following format:

XY: *Title of Task*

For example, if the task takes 20 minutes and is 'Buy groceries', you should output:
02: Buy groceries

Now, please analyze the following image and provide the result.
"""

@app.route('/')
def index():
    """Serve the index.html file"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "healthy"}), 200

@app.route('/process-screenshot', methods=['POST'])
def process_screenshot():
    """
    Process a screenshot image:
    1. Receive image from iOS Shortcut
    2. Send to Claude Vision API
    3. Parse response
    4. Create task in Todoist
    5. Return result
    """
    try:
        # Check if the request contains an image
        if 'image' not in request.files:
            logger.error("No image file in request")
            return jsonify({"error": "No image file provided"}), 400
        
        image_file = request.files['image']
        
        # Read the image data
        image_data = image_file.read()
        
        # Convert image to base64
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        # Get the image MIME type
        mime_type = image_file.content_type or "image/jpeg"  # Default to JPEG if not specified
        
        # Call Claude Vision API
        logger.info("Calling Claude Vision API")
        task_info = analyze_image_with_claude(base64_image, mime_type)
        
        # Create task in Todoist
        logger.info(f"Creating Todoist task: {task_info}")
        todoist_response = create_todoist_task(task_info)
        
        # Return success response
        return jsonify({
            "status": "success",
            "task": task_info,
            "todoist_response": todoist_response
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing screenshot: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

def analyze_image_with_claude(base64_image, mime_type):
    """
    Send the image to Claude Vision API and get the task information
    """
    try:
        # Create the message with the image
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
        
        # Clean up the response (remove any extra text, just get the task format)
        # The response should be in the format "XY: *Task Title*"
        response_lines = response_text.strip().split('\n')
        for line in response_lines:
            # Look for a line that matches our expected format
            if len(line) >= 5 and line[0].isdigit() and line[1].isdigit() and line[2:4] == ": ":
                return line.strip()
        
        # If we couldn't find a properly formatted line, return the whole response
        logger.warning(f"Claude response didn't match expected format: {response_text}")
        return response_text.strip()
        
    except Exception as e:
        logger.error(f"Error calling Claude API: {str(e)}", exc_info=True)
        raise Exception(f"Failed to analyze image with Claude: {str(e)}")

def create_todoist_task(task_info):
    """
    Create a task in Todoist with the given information
    """
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
        response = requests.post(url, headers=headers, json=data)
        
        # Check if the request was successful
        if response.status_code == 200:
            return response.json()
        else:
            error_msg = f"Todoist API error: {response.status_code} - {response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
            
    except Exception as e:
        logger.error(f"Error creating Todoist task: {str(e)}", exc_info=True)
        raise Exception(f"Failed to create Todoist task: {str(e)}")

if __name__ == "__main__":
    # Create the static directory if it doesn't exist
    os.makedirs('static', exist_ok=True)
    
    # Run the Flask app (for development)
    app.run(host='0.0.0.0', port=5000, debug=True) 