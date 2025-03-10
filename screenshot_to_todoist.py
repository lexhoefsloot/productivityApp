#!/usr/bin/env python3
import os
import sys
import base64
import json
import logging
import traceback
from flask import Flask, request, jsonify, send_from_directory, render_template_string
import requests
from anthropic import Anthropic
import httpx
from dotenv import load_dotenv
import io
import time

# Ensure log directory exists with proper permissions
LOG_DIR = '/var/log/screenshot_to_todoist'
try:
    os.makedirs(LOG_DIR, exist_ok=True)
    os.chmod(LOG_DIR, 0o755)
except Exception as e:
    print(f"Error creating log directory: {e}", file=sys.stderr)
    sys.exit(1)

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "flask_app.log")),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
try:
    logger.info("Loading environment variables")
    load_dotenv()
except Exception as e:
    logger.error(f"Error loading .env file: {e}")
    sys.exit(1)

# Log startup information
logger.info("Starting Screenshot to Todoist application")
logger.info(f"Python version: {sys.version}")
logger.info(f"Working directory: {os.getcwd()}")

try:
    logger.info("Importing Anthropic")
    import anthropic
    logger.info(f"Anthropic SDK Version: {anthropic.__version__}")
except Exception as e:
    logger.error(f"Error importing Anthropic: {e}")
    sys.exit(1)

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
    sys.exit(1)

if not TODOIST_API_KEY:
    logger.error("TODOIST_API_KEY is not set in environment variables")
    sys.exit(1)

# Initialize Anthropic client with proper configuration
try:
    logger.debug("Attempting to initialize Anthropic client...")
    # Check for any proxy environment variables
    for var in proxy_vars:
        if var in os.environ:
            logger.warning(f"Found proxy setting in environment: {var}={os.environ[var]}")
            # Temporarily unset any proxy variables that might interfere with Anthropic SDK
            proxy_value = os.environ.pop(var)
            logger.warning(f"Temporarily removed {var} from environment")
    
    # Initialize with just the API key
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    logger.info("Successfully initialized Anthropic client")
except Exception as e:
    logger.error(f"Error initializing Anthropic client: {str(e)}")
    logger.error(f"Error type: {type(e).__name__}")
    logger.error(f"Traceback:\n{traceback.format_exc()}")
    sys.exit(1)

# Claude prompt for task analysis
CLAUDE_PROMPT = """
Below is a screenshot of something that needs to be turned into a task that I need to do and I want to add to my todo list. Please analyze the image and determine the task's title in no more than 5-7 words. Also, estimate the required time to complete this task and express it in a two-digit format where the first digit is the number of hours and the second digit is the number of tens of minutes (e.g., '02' means 0 hours and 20 minutes). Return your answer strictly in the following format:

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
    4. Create task in Todoist with image attachment
    5. Return result
    
    Query parameter:
    - debug: If set to 'true', returns detailed debug information
    """
    try:
        # Check if in debug mode
        debug_mode = request.args.get('debug', 'false').lower() == 'true' or request.form.get('debug', 'false').lower() == 'true'
        
        # Check if the request contains an image
        if 'image' not in request.files:
            logger.error("No image file in request")
            return jsonify({"error": "No image file provided"}), 400
        
        image_file = request.files['image']
        logger.info(f"Received image: {image_file.filename}, type: {image_file.content_type}, size: {request.content_length} bytes")
        
        # Get additional file metadata if provided
        file_name = request.form.get('file_name', image_file.filename)
        file_type = request.form.get('file_type', image_file.content_type)
        file_size = request.form.get('file_size')
        
        logger.debug(f"File metadata: name={file_name}, type={file_type}, size={file_size or 'unknown'}")
        
        # Read the image data as bytes
        image_data = image_file.read()
        logger.info(f"Read {len(image_data)} bytes of image data")
        
        # Store the original image data for file attachment
        original_image_data = image_data
        
        # Convert image to base64 for Claude
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        # Get the image MIME type
        mime_type = image_file.content_type or "image/jpeg"  # Default to JPEG if not specified
        
        # Call Claude Vision API
        logger.info("Calling Claude Vision API")
        task_info, anthropic_response = analyze_image_with_claude(base64_image, mime_type)
        
        # Create task in Todoist with the original image data
        logger.info(f"Creating Todoist task: {task_info}")
        logger.debug(f"Image data type: {type(original_image_data)}, length: {len(original_image_data)} bytes")
        todoist_response = create_todoist_task(task_info, original_image_data, mime_type)
        
        # Check if file attachment was successful
        file_attached = "file_attachment" in todoist_response
        logger.info(f"File attachment status: {'SUCCESS' if file_attached else 'FAILED'}")
        
        # Extract the title from the task (remove any time estimate at the beginning if present)
        task_title = task_info
        if ": " in task_info and len(task_info) >= 5 and task_info[0].isdigit() and task_info[1].isdigit():
            task_title = task_info[4:].strip()
        
        # Prepare response data
        if debug_mode:
            # Return detailed response for debugging
            response_data = {
                "status": "success",
                "task": task_info,
                "title": task_title,
                "anthropic_response": anthropic_response,
                "todoist_response": todoist_response,
                "task_created": True,
                "file_attached": file_attached,
                "diagnostics": {
                    "image_size": len(original_image_data),
                    "mime_type": mime_type,
                    "file_name": file_name,
                    "has_todoist_key": bool(TODOIST_API_KEY),
                    "todoist_key_length": len(TODOIST_API_KEY) if TODOIST_API_KEY else 0
                }
            }
            
            # Add file attachment info if available
            if file_attached:
                response_data["file_attachment"] = todoist_response.get("file_attachment", {})
                response_data["attachment_details"] = {
                    "comment_id": todoist_response["file_attachment"].get("id"),
                    "task_id": todoist_response["id"]
                }
        else:
            # Return simplified response for regular use
            response_data = {
                "status": "success",
                "title": task_title,
                "task_created": True,
                "file_attached": file_attached
            }
            
        return jsonify(response_data), 200
        
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
                "input_tokens": message.usage.input_tokens,
                "output_tokens": message.usage.output_tokens
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

def create_todoist_task(task_info, image_data=None, mime_type=None):
    """
    Create a task in Todoist with the given information
    If image_data is provided, attach it to the task
    """
    try:
        # Todoist API endpoint for tasks
        task_url = "https://api.todoist.com/rest/v2/tasks"
        
        # Headers with authentication
        headers = {
            "Authorization": f"Bearer {TODOIST_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Task data
        task_data = {
            "content": task_info,
            "due_string": "today"  # Default due date is today
        }
        
        # Make the request to create the task
        task_response = requests.post(task_url, headers=headers, json=task_data)
        
        # Check if the request was successful
        if task_response.status_code != 200:
            error_msg = f"Todoist API error: {task_response.status_code} - {task_response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
            
        task = task_response.json()
        logger.info(f"Task created successfully with ID: {task['id']}")
        
        # If image data is provided, upload it and attach to the task
        if image_data:
            logger.info(f"Attempting to upload image to Todoist (data length: {len(image_data)} bytes)")
            
            # Convert image_data to the correct format for upload
            # If it's already bytes, use it directly
            if isinstance(image_data, bytes):
                logger.debug("Image data is already in bytes format")
                binary_data = image_data
            # If it's base64 string, decode it
            elif isinstance(image_data, str) and ('base64' in image_data or image_data.startswith('data:')):
                logger.debug("Converting base64 string to binary data")
                # Extract the actual base64 content
                base64_content = image_data.split("base64,")[1] if "base64," in image_data else image_data
                binary_data = base64.b64decode(base64_content)
            else:
                logger.error(f"Image data is not in a recognized format: {type(image_data)}")
                return task
            
            logger.debug(f"Binary data prepared, length: {len(binary_data)} bytes, first 50 bytes: {binary_data[:50]}")
            
            # Try using the REST API first (v2)
            try:
                # REST API for file uploads
                upload_url = "https://api.todoist.com/rest/v2/attachments"
                upload_headers = {
                    "Authorization": f"Bearer {TODOIST_API_KEY}"
                }
                
                # Set a default filename and mime type if not provided
                filename = f"screenshot_{int(time.time())}.jpg"
                if not mime_type:
                    mime_type = "image/jpeg"
                
                logger.debug(f"Uploading with filename: {filename}, mime_type: {mime_type}")
                logger.debug(f"API Key validity check: {'VALID' if TODOIST_API_KEY and len(TODOIST_API_KEY) > 20 else 'INVALID'}")
                
                # Create a file-like object from the image data
                file_obj = io.BytesIO(binary_data)
                
                # Create the multipart/form-data payload
                files = {
                    'file': (filename, file_obj, mime_type)
                }
                
                # Upload the file to Todoist REST API
                logger.debug(f"Making REST API request to {upload_url} with task_id: {task['id']}")
                upload_response = requests.post(
                    upload_url, 
                    headers=upload_headers, 
                    files=files,
                    params={"task_id": task["id"]}
                )
                
                logger.debug(f"Upload response status: {upload_response.status_code}")
                logger.debug(f"Upload response body: {upload_response.text}")
                
                if upload_response.status_code in (200, 201):
                    logger.info("File uploaded successfully via REST API")
                    attachment_data = upload_response.json()
                    task["file_attachment"] = attachment_data
                    return task
                else:
                    logger.warning(f"REST API upload failed with status {upload_response.status_code}: {upload_response.text}")
                    logger.warning(f"Trying Sync API...")
            except Exception as e:
                logger.error(f"Error with REST API upload: {str(e)}", exc_info=True)
                logger.warning("Falling back to Sync API...")
            
            # If REST API failed, try the Sync API (v8)
            try:
                # Sync API for file uploads
                upload_url = "https://api.todoist.com/sync/v9/uploads/add"
                upload_headers = {
                    "Authorization": f"Bearer {TODOIST_API_KEY}"
                }
                
                # Create a file-like object from the image data
                file_obj = io.BytesIO(binary_data)
                
                # Create the multipart/form-data payload
                files = {
                    'file': (filename, file_obj, mime_type)
                }
                
                # Upload the file to Todoist Sync API
                logger.debug(f"Making Sync API request to {upload_url}")
                upload_response = requests.post(upload_url, headers=upload_headers, files=files)
                
                logger.debug(f"Sync API upload response status: {upload_response.status_code}")
                logger.debug(f"Sync API upload response body: {upload_response.text}")
                
                if upload_response.status_code != 200:
                    logger.error(f"Error uploading file with Sync API: {upload_response.status_code} - {upload_response.text}")
                    return task
                
                # Get the upload details
                upload_data = upload_response.json()
                file_url = upload_data.get("file_url")
                
                if file_url:
                    logger.info(f"File uploaded successfully via Sync API, URL: {file_url}")
                    
                    # Add a comment with the file attachment to the task
                    comment_url = "https://api.todoist.com/rest/v2/comments"
                    comment_data = {
                        "task_id": task["id"],
                        "attachment": {
                            "resource_type": "file",
                            "file_url": file_url,
                            "file_type": mime_type,
                            "file_name": upload_data.get("file_name", filename)
                        }
                    }
                    
                    logger.debug(f"Attaching file to task with comment data: {comment_data}")
                    
                    comment_response = requests.post(comment_url, headers=headers, json=comment_data)
                    
                    logger.debug(f"Comment response status: {comment_response.status_code}")
                    logger.debug(f"Comment response body: {comment_response.text}")
                    
                    if comment_response.status_code != 200:
                        logger.error(f"Error attaching file to task: {comment_response.status_code} - {comment_response.text}")
                    else:
                        logger.info("File attached to task successfully")
                        # Add comment info to the task response
                        task["file_attachment"] = comment_response.json()
                else:
                    logger.error(f"File upload succeeded but missing file_url. Response: {upload_data}")
            except Exception as e:
                logger.error(f"Error with Sync API upload: {str(e)}", exc_info=True)
        else:
            logger.warning("No image data provided, skipping file attachment")
        
        return task
            
    except Exception as e:
        logger.error(f"Error creating Todoist task: {str(e)}", exc_info=True)
        raise Exception(f"Failed to create Todoist task: {str(e)}")

if __name__ == "__main__":
    # Create the static directory if it doesn't exist
    os.makedirs('static', exist_ok=True)
    
    # Run the Flask app (for development)
    app.run(host='0.0.0.0', port=5000, debug=True) 