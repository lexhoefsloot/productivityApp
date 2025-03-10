# Screenshot to Todoist

A Python Flask application that processes iPhone screenshots, analyzes them using Claude's Vision API, and creates tasks in Todoist with estimated time requirements.

## Overview

This application provides a backend service that:

1. Receives screenshot images from an iOS Shortcut
2. Sends the image to Claude's Vision API for analysis
3. Extracts a task title and time estimate from Claude's response
4. Creates a task in Todoist with the format "XY: *Task Title*" where:
   - X = number of hours
   - Y = number of 10-minute increments (e.g., 2 = 20 minutes)

## Setup Instructions

### 1. Server Setup

1. Clone this repository to your Apache server
2. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```
3. Copy the example environment file and add your API keys:
   ```
   cp .env.example .env
   ```
   Then edit `.env` to add your Anthropic and Todoist API keys.

### 2. Configure Apache

#### Option 1: Using the installation script (Recommended)

If you're using the existing Apache configuration on `lieshout.loseyourip.com`, you can use the provided installation script:

```bash
sudo chmod +x install_apache_config.sh
sudo ./install_apache_config.sh
```

This script will:
1. Create a backup of your existing Apache configuration
2. Add the Screenshot to Todoist configuration to your existing VirtualHost
3. Enable the required Apache modules
4. Test the configuration and restart Apache

#### Option 2: Manual configuration

If you prefer to configure Apache manually, add the following to your Apache configuration:

```apache
# Screenshot to Todoist configuration
ProxyPass /screenshot-to-todoist http://localhost:5000
ProxyPassReverse /screenshot-to-todoist http://localhost:5000

# Add headers for proper forwarding
<Location "/screenshot-to-todoist">
    ProxyPreserveHost On
    RequestHeader set X-Forwarded-Proto "https"
    RequestHeader set X-Forwarded-For "%{REMOTE_ADDR}s"
    
    # Add CORS headers if needed
    Header always set Access-Control-Allow-Origin "*"
    Header always set Access-Control-Allow-Methods "GET, POST, OPTIONS"
    Header always set Access-Control-Allow-Headers "Origin, Content-Type, Accept, Authorization"
</Location>

# Health check endpoint
<Location "/screenshot-to-todoist/health">
    ProxyPass http://localhost:5000/health
    ProxyPassReverse http://localhost:5000/health
    ProxyPreserveHost On
    RequestHeader set X-Forwarded-Proto "https"
    RequestHeader set X-Forwarded-For "%{REMOTE_ADDR}s"
</Location>
```

Make sure to enable the required Apache modules:
```
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod headers
sudo systemctl restart apache2
```

### 3. Run the Application

For development:
```
python screenshot_to_todoist.py
```

For production, use Gunicorn:
```
gunicorn -w 4 -b 0.0.0.0:5000 screenshot_to_todoist:app
```

Consider setting up a systemd service to keep the application running:

```
[Unit]
Description=Screenshot to Todoist Service
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/app
ExecStart=/usr/local/bin/gunicorn -w 4 -b 0.0.0.0:5000 screenshot_to_todoist:app
Restart=always

[Install]
WantedBy=multi-user.target
```

### 4. iOS Shortcut Setup

Follow the detailed instructions in `ios_shortcut_instructions.md` to set up the iOS Shortcut.

The shortcut will be configured to send screenshots to:
```
https://lieshout.loseyourip.com/screenshot-to-todoist/process-screenshot
```

## Testing

### Web Interface

A web interface is available for testing at:
```
https://lieshout.loseyourip.com/screenshot-to-todoist/
```

### Test Script

You can also use the provided test script to verify the API integrations:
```
./test.sh
```

Or test the APIs directly:
```
python test_apis.py test_image.jpg
```

## API Endpoints

- `GET /health`: Health check endpoint
- `POST /process-screenshot`: Main endpoint that processes screenshots and creates Todoist tasks

## Troubleshooting

Check the log file at `screenshot_to_todoist.log` for detailed error information.

Common issues:
- Missing or invalid API keys
- Network connectivity problems
- Image format issues
- Anthropic API compatibility issues (fixed in the code)

## License

MIT
