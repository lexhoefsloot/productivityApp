#!/bin/bash

# Screenshot to Todoist Test Script
# This script helps test the Screenshot to Todoist application

echo "=== Screenshot to Todoist Test Script ==="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install it first."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    
    # Prompt for API keys
    echo "Please enter your Anthropic API key:"
    read anthropic_key
    echo "Please enter your Todoist API key:"
    read todoist_key
    
    # Update .env file with API keys
    sed -i "s/your_anthropic_api_key_here/$anthropic_key/g" .env
    sed -i "s/your_todoist_api_key_here/$todoist_key/g" .env
    
    echo ".env file created with your API keys."
else
    echo ".env file already exists. Using existing configuration."
fi

# Create static directory if it doesn't exist
mkdir -p static

# Check if test image exists
if [ ! -f "test_image.jpg" ] && [ ! -f "test_image.png" ]; then
    echo "No test image found. Please provide a test image."
    echo "You can use any image file named 'test_image.jpg' or 'test_image.png' in the current directory."
    
    # Ask if user wants to continue without a test image
    echo "Do you want to continue without a test image? (y/n)"
    read continue_without_image
    
    if [ "$continue_without_image" != "y" ]; then
        echo "Exiting. Please add a test image and try again."
        exit 1
    fi
fi

# Start the Flask application
echo "Starting the Flask application..."
python screenshot_to_todoist.py &
app_pid=$!

# Wait for the application to start
sleep 2

# Print instructions
echo ""
echo "The application is now running at http://localhost:5000"
echo ""
echo "You can test it in the following ways:"

if [ -f "test_image.jpg" ]; then
    echo "1. Run the test script: python test_apis.py test_image.jpg"
elif [ -f "test_image.png" ]; then
    echo "1. Run the test script: python test_apis.py test_image.png"
else
    echo "1. Add a test image and run: python test_apis.py your_image.jpg"
fi

echo "2. Open http://localhost:5000 in your web browser and use the web interface"
echo "3. Use the iOS Shortcut as described in ios_shortcut_instructions.md"
echo ""
echo "Press Ctrl+C to stop the application when you're done testing."

# Wait for user to press Ctrl+C
trap "kill $app_pid; echo 'Application stopped.'; exit 0" INT
wait $app_pid 