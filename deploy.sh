#!/bin/bash

# Screenshot to Todoist Deployment Script
# This script helps set up the Screenshot to Todoist service on an Apache server

echo "=== Screenshot to Todoist Deployment ==="
echo "This script will help you set up the backend service."

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

# Create Apache configuration file
echo "Creating Apache configuration file..."
cat > screenshot_to_todoist.conf << EOF
<VirtualHost *:80>
    ServerName your-domain.com
    
    ProxyPass /screenshot-to-todoist http://localhost:5000
    ProxyPassReverse /screenshot-to-todoist http://localhost:5000
    
    ErrorLog \${APACHE_LOG_DIR}/screenshot_error.log
    CustomLog \${APACHE_LOG_DIR}/screenshot_access.log combined
</VirtualHost>
EOF

echo "Apache configuration file created at screenshot_to_todoist.conf"
echo "Please update the ServerName in this file and move it to your Apache sites-available directory."

# Create systemd service file
echo "Creating systemd service file..."
cat > screenshot_to_todoist.service << EOF
[Unit]
Description=Screenshot to Todoist Service
After=network.target

[Service]
User=$(whoami)
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 screenshot_to_todoist:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo "systemd service file created at screenshot_to_todoist.service"
echo "To install the service, run:"
echo "sudo cp screenshot_to_todoist.service /etc/systemd/system/"
echo "sudo systemctl daemon-reload"
echo "sudo systemctl enable screenshot_to_todoist"
echo "sudo systemctl start screenshot_to_todoist"

# Test the application
echo "Would you like to test the application now? (y/n)"
read test_app

if [ "$test_app" = "y" ]; then
    echo "Starting the application in development mode..."
    python screenshot_to_todoist.py &
    app_pid=$!
    
    echo "Application started with PID $app_pid"
    echo "You can test it by sending a request to http://localhost:5000/health"
    echo "Press Enter to stop the application..."
    read
    
    echo "Stopping the application..."
    kill $app_pid
fi

echo "=== Deployment setup complete ==="
echo "Next steps:"
echo "1. Update the Apache configuration with your domain name"
echo "2. Install and enable the systemd service"
echo "3. Set up the iOS Shortcut as described in ios_shortcut_instructions.md"
echo "4. Test the complete workflow" 