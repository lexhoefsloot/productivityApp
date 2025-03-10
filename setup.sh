#!/bin/bash

# Screenshot to Todoist Complete Setup Script
# This script performs all the necessary steps to set up the Screenshot to Todoist service

echo "=== Screenshot to Todoist Complete Setup ==="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install it first."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "pip3 is not installed. Please install it first."
    exit 1
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
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
    echo ".env file already exists. Skipping creation."
fi

# Create static directory if it doesn't exist
mkdir -p static

# Create systemd service file
echo "Creating systemd service file..."
cat > screenshot_to_todoist.service << EOF
[Unit]
Description=Screenshot to Todoist Service
After=network.target

[Service]
User=root
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 screenshot_to_todoist:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Ask if user wants to install the systemd service
echo "Do you want to install the systemd service? (y/n)"
read install_service

if [ "$install_service" = "y" ]; then
    echo "Installing systemd service..."
    cp screenshot_to_todoist.service /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable screenshot_to_todoist
    systemctl start screenshot_to_todoist
    echo "Systemd service installed and started."
else
    echo "Skipping systemd service installation."
fi

# Ask if user wants to install the Apache configuration
echo "Do you want to install the Apache configuration? (y/n)"
read install_apache

if [ "$install_apache" = "y" ]; then
    echo "Making the Apache installation script executable..."
    chmod +x install_apache_config.sh
    
    echo "Running the Apache installation script..."
    ./install_apache_config.sh
else
    echo "Skipping Apache configuration installation."
fi

# Test the application
echo "Would you like to test the application now? (y/n)"
read test_app

if [ "$test_app" = "y" ]; then
    # Check if the systemd service is running
    if systemctl is-active --quiet screenshot_to_todoist; then
        echo "The application is already running as a systemd service."
        echo "You can test it by visiting:"
        echo "https://lieshout.loseyourip.com/screenshot-to-todoist/"
    else
        echo "Starting the application in development mode..."
        python screenshot_to_todoist.py &
        app_pid=$!
        
        echo "Application started with PID $app_pid"
        echo "You can test it by visiting:"
        echo "http://localhost:5000/"
        echo "Press Enter to stop the application..."
        read
        
        echo "Stopping the application..."
        kill $app_pid
    fi
fi

echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "1. Set up the iOS Shortcut as described in ios_shortcut_instructions.md"
echo "2. Test the complete workflow by taking a screenshot on your iPhone"
echo ""
echo "The service should be accessible at:"
echo "https://lieshout.loseyourip.com/screenshot-to-todoist/"
echo ""
echo "For troubleshooting, check the log file at:"
echo "$(pwd)/screenshot_to_todoist.log" 