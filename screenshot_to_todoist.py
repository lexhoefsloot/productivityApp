#!/usr/bin/env python3
import os
import base64
import json
import logging
import traceback
from flask import Flask, request, jsonify, send_from_directory, render_template_string
import requests
from anthropic import Anthropic
import httpx
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Ensure log directory exists
LOG_DIR = '/var/log/screenshot_to_todoist'
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG level
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "flask_app.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Log startup information
logger.info("Starting Screenshot to Todoist application")
logger.info(f"Python version: {os.sys.version}")
logger.info(f"Anthropic SDK Version: {anthropic.__version__}")
logger.info(f"Working directory: {os.getcwd()}")

# Check for proxy settings in environment
proxy_vars = ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']
for var in proxy_vars:
    if var in os.environ:
        logger.warning(f"Found proxy setting in environment: {var}={os.environ[var]}")

# Initialize Flask app
app = Flask(__name__, static_folder='static')

# Error handler for all exceptions
@app.errorhandler(Exception)
def handle_error(error):
    logger.error(f"Unhandled error: {str(error)}")
    logger.error(traceback.format_exc())
    error_id = os.urandom(8).hex()
    error_message = f"Error ID: {error_id}. Please check the application logs for more details."
    if isinstance(error, httpx.TimeoutException):
        return jsonify({"error": "Request timed out", "error_id": error_id}), 504
    elif isinstance(error, httpx.ConnectError):
        return jsonify({"error": "Could not connect to service", "error_id": error_id}), 502
    elif isinstance(error, anthropic.APIError):
        return jsonify({"error": f"Anthropic API error: {str(error)}", "error_id": error_id}), 502
    return jsonify({"error": str(error), "error_id": error_id}), 500

# Get API keys from environment variables
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
TODOIST_API_KEY = os.getenv("TODOIST_API_KEY")

if not ANTHROPIC_API_KEY:
    logger.error("ANTHROPIC_API_KEY is not set in environment variables")
    raise ValueError("ANTHROPIC_API_KEY is required")

if not TODOIST_API_KEY:
    logger.error("TODOIST_API_KEY is not set in environment variables")
    raise ValueError("TODOIST_API_KEY is required")

# Initialize Anthropic client with proper configuration
try:
    logger.debug("Attempting to initialize Anthropic client...")
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    logger.info("Successfully initialized Anthropic client")
except Exception as e:
    logger.error(f"Error initializing Anthropic client: {str(e)}")
    logger.error(f"Error type: {type(e).__name__}")
    logger.error(f"Traceback:\n{traceback.format_exc()}")
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

@app.route('/tester')
def tester():
    """Serve the tester.html file with proper error handling"""
    try:
        return send_from_directory(app.static_folder, 'tester.html')
    except Exception as e:
        logger.error(f"Error serving tester page: {str(e)}")
        error_id = os.urandom(8).hex()
        return render_template_string("""
            <html>
                <head>
                    <title>Error</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 40px; }
                        .error { color: #721c24; background-color: #f8d7da; padding: 20px; border-radius: 5px; }
                        .error-id { color: #666; font-size: 0.9em; margin-top: 10px; }
                    </style>
                </head>
                <body>
                    <div class="error">
                        <h2>Application Error</h2>
                        <p>{{ error_message }}</p>
                        <p class="error-id">Error ID: {{ error_id }}</p>
                    </div>
                </body>
            </html>
        """, error_message=str(e), error_id=error_id), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Enhanced health check endpoint"""
    try:
        # Check if we can create a test message with Anthropic
        client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=10,
            messages=[{
                "role": "user",
                "content": "test"
            }]
        )
        return jsonify({
            "status": "healthy",
            "anthropic": "connected",
            "version": anthropic.__version__
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "version": anthropic.__version__
        }), 500

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
        task_info, anthropic_response = analyze_image_with_claude(base64_image, mime_type)
        
        # Create task in Todoist
        logger.info(f"Creating Todoist task: {task_info}")
        todoist_response = create_todoist_task(task_info)
        
        # Return success response
        return jsonify({
            "status": "success",
            "task": task_info,
            "anthropic_response": anthropic_response,
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
            model="claude-3-sonnet-20240229",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": base64_image
                        }
                    },
                    {
                        "type": "text",
                        "text": CLAUDE_PROMPT
                    }
                ]
            }]
        )
        
        # Extract the response text
        response_text = message.content[0].text
        
        # Store the full response for debugging
        anthropic_response = {
            "model": message.model,
            "id": message.id,
            "role": message.role,
            "content": response_text,
            "usage": {
                "input_tokens": message.input_tokens,
                "output_tokens": message.output_tokens
            }
        }
        
        # Clean up the response (remove any extra text, just get the task format)
        # The response should be in the format "XY: *Task Title*"
        response_lines = response_text.strip().split('\n')
        task_info = None
        for line in response_lines:
            # Look for a line that matches our expected format
            if len(line) >= 5 and line[0].isdigit() and line[1].isdigit() and line[2:4] == ": ":
                task_info = line.strip()
                break
        
        # If we couldn't find a properly formatted line, return the whole response
        if not task_info:
            logger.warning(f"Claude response didn't match expected format: {response_text}")
            task_info = response_text.strip()
        
        return task_info, anthropic_response
        
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