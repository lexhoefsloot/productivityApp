# iOS Shortcut Setup Instructions

This document provides step-by-step instructions for creating an iOS Shortcut that will:
1. Capture or access a screenshot
2. Send it to our backend service
3. Create a Todoist task with the analyzed content

## Prerequisites

- iOS 14 or later
- Shortcuts app installed
- Todoist app installed (optional, but recommended)

## Creating the Shortcut

### Method 1: Quick Screenshot Processing

This method processes the most recent screenshot:

1. Open the Shortcuts app on your iPhone
2. Tap the "+" button to create a new shortcut
3. Tap "Add Action"
4. Search for and select "Get Latest Screenshot"
5. Add another action by tapping "+"
6. Search for and select "Get Contents of URL"
7. Configure the "Get Contents of URL" action:
   - URL: `https://lieshout.loseyourip.com/screenshot-to-todoist/process-screenshot`
   - Method: POST
   - Request Body: Form
   - Headers: Add a header with name "Accept" and value "application/json"
   - Form Fields: Add a field with name "image" and value "Shortcut Input" (select from the variables)
8. Add another action by tapping "+"
9. Search for and select "Show Notification"
10. Configure the notification to show the response from the server
11. Name your shortcut (e.g., "Screenshot to Todoist")
12. Tap "Done" to save

### Method 2: Share Sheet Integration

This method allows you to process any image from the share sheet:

1. Open the Shortcuts app on your iPhone
2. Tap the "+" button to create a new shortcut
3. Tap the settings icon (⚙️) at the top right
4. Enable "Show in Share Sheet"
5. Under "Share Sheet Types", select only "Images"
6. Tap "Done"
7. Add an action by tapping "+"
8. Search for and select "Get Contents of URL"
9. Configure the "Get Contents of URL" action:
   - URL: `https://lieshout.loseyourip.com/screenshot-to-todoist/process-screenshot`
   - Method: POST
   - Request Body: Form
   - Headers: Add a header with name "Accept" and value "application/json"
   - Form Fields: Add a field with name "image" and value "Shortcut Input" (select from the variables)
10. Add another action by tapping "+"
11. Search for and select "Show Notification"
12. Configure the notification to show the response from the server
13. Name your shortcut (e.g., "Image to Todoist")
14. Tap "Done" to save

## Using the Shortcut

### Method 1: Quick Screenshot Processing

1. Take a screenshot on your iPhone
2. Open the Shortcuts app
3. Tap on your "Screenshot to Todoist" shortcut
4. The shortcut will process the most recent screenshot and show a notification with the result

For faster access:
- Add the shortcut to your home screen: In the Shortcuts app, long press on the shortcut and select "Add to Home Screen"
- Add it to your widgets: Add a Shortcuts widget to your home screen and select this shortcut

### Method 2: Share Sheet Integration

1. Take a screenshot or open any image in Photos
2. Tap the share button
3. Scroll down and tap on your "Image to Todoist" shortcut
4. The shortcut will process the image and show a notification with the result

## Advanced: Siri Integration

You can also configure your shortcut to work with Siri:

1. Open the Shortcuts app
2. Tap on your shortcut
3. Tap the settings icon (⚙️) at the top right
4. Tap "Add to Siri"
5. Record a phrase like "Process my screenshot" or "Add screenshot to Todoist"
6. Tap "Done"

Now you can say "Hey Siri, process my screenshot" to run the shortcut.

## Troubleshooting

If your shortcut isn't working:

1. Check your internet connection
2. Verify that the server is running and accessible
3. Check that the image is being properly attached to the request
4. Look at the notification for any error messages

For more detailed error information, you can modify the shortcut to show the full response from the server. 