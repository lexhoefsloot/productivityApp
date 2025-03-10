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

Add the following to your Apache configuration to proxy requests to the Flask application:

```apache
<VirtualHost *:80>
    ServerName your-domain.com
    
    ProxyPass /screenshot-to-todoist http://localhost:5000
    ProxyPassReverse /screenshot-to-todoist http://localhost:5000
    
    ErrorLog ${APACHE_LOG_DIR}/screenshot_error.log
    CustomLog ${APACHE_LOG_DIR}/screenshot_access.log combined
</VirtualHost>
```

Make sure to enable the required Apache modules:
```
sudo a2enmod proxy
sudo a2enmod proxy_http
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

1. Create a new iOS Shortcut
2. Add an action to get the latest screenshot or take a new screenshot
3. Add a "Get Contents of URL" action with the following settings:
   - URL: `https://your-domain.com/screenshot-to-todoist/process-screenshot`
   - Method: POST
   - Request Body: Form
   - Add a field named "image" with the screenshot as the value
4. Add a notification action to show the response

## API Endpoints

- `GET /health`: Health check endpoint
- `POST /process-screenshot`: Main endpoint that processes screenshots and creates Todoist tasks

## Troubleshooting

Check the log file at `screenshot_to_todoist.log` for detailed error information.

Common issues:
- Missing or invalid API keys
- Network connectivity problems
- Image format issues

## License

MIT
