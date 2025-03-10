#!/bin/bash

# Script to install the Screenshot to Todoist Apache configuration

echo "=== Installing Screenshot to Todoist Apache Configuration ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run this script as root or with sudo"
    exit 1
fi

# Check if the configuration file exists
if [ ! -f "screenshot_to_todoist.conf" ]; then
    echo "Error: screenshot_to_todoist.conf not found"
    exit 1
fi

# Get the current directory
CURRENT_DIR=$(pwd)

# Create a backup of the existing Apache configuration
echo "Creating a backup of the existing Apache configuration..."
TIMESTAMP=$(date +"%Y%m%d%H%M%S")
cp /etc/apache2/sites-available/zwemmen.conf /etc/apache2/sites-available/zwemmen.conf.backup.$TIMESTAMP

# Add our configuration to the existing VirtualHost
echo "Adding Screenshot to Todoist configuration to the existing VirtualHost..."

# Extract the content between the <VirtualHost *:443> tags
CONFIG=$(sed -n '/<VirtualHost \*:443>/,/<\/VirtualHost>/p' screenshot_to_todoist.conf | grep -v "<VirtualHost \*:443>" | grep -v "</VirtualHost>")

# Insert the configuration before the closing </VirtualHost> tag
sed -i "/<\/VirtualHost>/i\\
    # Screenshot to Todoist configuration\\
$CONFIG" /etc/apache2/sites-available/zwemmen.conf

# Make sure required modules are enabled
echo "Enabling required Apache modules..."
a2enmod proxy
a2enmod proxy_http
a2enmod headers

# Test the Apache configuration
echo "Testing Apache configuration..."
if apache2ctl configtest; then
    echo "Apache configuration test successful"
    
    # Restart Apache
    echo "Restarting Apache..."
    systemctl restart apache2
    
    echo "Installation complete!"
    echo "The Screenshot to Todoist service is now accessible at:"
    echo "https://lieshout.loseyourip.com/screenshot-to-todoist/"
else
    echo "Apache configuration test failed"
    echo "Restoring backup..."
    cp /etc/apache2/sites-available/zwemmen.conf.backup.$TIMESTAMP /etc/apache2/sites-available/zwemmen.conf
    echo "Backup restored. Please check the configuration manually."
fi 