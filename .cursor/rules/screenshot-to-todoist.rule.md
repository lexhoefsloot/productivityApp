# iPhone Screenshot to Todoist Integration Action Plan

This rule outlines an action plan for a daily workflow to convert an iPhone screenshot of a task into a Todoist entry with minimal user interaction.

## Overview

When a user takes a screenshot on their iPhone, the following steps will be executed:

1. **Screenshot Capture**
   - The screenshot is taken on the iPhone, ideally using a custom iOS Shortcut or a standalone app for quick access.
   - The goal is to reduce manual steps and ensure the process is fast and convenient.

2. **Direct Image Analysis via Claude Vision API**
   - Instead of performing OCR on the device, the screenshot image is sent directly to Claude's Vision API.
   - Claude can analyze images directly and extract both textual content and understand the visual context.
   - Reference: [Claude Vision API Documentation](https://docs.anthropic.com/en/docs/build-with-claude/vision)

3. **Task Analysis with Specific Prompt**
   - The following prompt will be used with Claude to ensure it outputs the task in the exact required format:

   ```
   Below is an image of a task. Please analyze the image and determine the task's title in no more than 5-7 words. Also, estimate the required time to complete this task and express it in a two-digit format where the first digit is the number of hours and the second digit is the number of tens of minutes (e.g., '02' means 0 hours and 20 minutes). Return your answer strictly in the following format:

   XY: *Title of Task*

   For example, if the task takes 20 minutes and is 'Buy groceries', you should output:
   02: Buy groceries

   Now, please analyze the following image and provide the result.
   ```

4. **Task Formatting & Todoist Integration**
   - Claude will return the result already formatted as "02: *My Task Title*" (the example indicates 0 hours and 20 minutes).
   - This formatted response can be directly added to Todoist via its API without additional processing.

## Technical Implementation

- **iOS Shortcut / Standalone App**: 
  - Create an iOS Shortcut that captures a screenshot or accesses the most recent screenshot.
  - The shortcut should send the image to a serverless backend function.

- **Serverless Backend Component**: 
  - Implement a serverless function (AWS Lambda, Google Cloud Functions, etc.) that:
    1. Receives the image from the iOS Shortcut
    2. Calls the Claude Vision API with the specified prompt
    3. Parses the response (which should already be in the correct format)
    4. Calls the Todoist API to create the task

- **API Integration**:
  - Claude Vision API: Use the Messages API with image content blocks as described in the [documentation](https://docs.anthropic.com/en/docs/build-with-claude/vision).
  - Todoist API: Use the [Create Task endpoint](https://developer.todoist.com/rest/v2/#create-a-new-task) to add the task.

- **Error Handling**: 
  - Implement error handling for cases where:
    - Claude API does not return data in the expected format
    - Todoist API call fails
    - Network connectivity issues occur

## Minimizing User Interaction

- After taking a screenshot, the user should only need to activate the iOS Shortcut (via share sheet, home screen icon, or Siri).
- The entire process from screenshot to Todoist task creation should happen automatically without further user input.
- Consider adding a notification when the task is successfully added to Todoist.

## Future Enhancements

- Allow the user to review and edit the task before final submission in Todoist if needed.
- Expand the integration to allow additional metadata or categorization in Todoist.
- Add support for batch processing multiple screenshots at once.
- Implement a custom app with a more streamlined UX if the Shortcut approach proves limiting.

## References

- [Claude Vision API Documentation](https://docs.anthropic.com/en/docs/build-with-claude/vision)
- [Todoist API Documentation](https://developer.todoist.com/rest/v2/)
- [iOS Shortcuts Documentation](https://support.apple.com/guide/shortcuts/welcome/ios)
- [Cursor Rules for AI](https://docs.cursor.com/context/rules-for-ai) 