# Add Serverless Mode Indicator to Projects Page

## Summary

This PR adds a visual indicator to inform users when they are communicating with an Elasticsearch serverless deployment. The indicator appears as a "Mode: Serverless" badge in the main Projects window header.

## Problem

When users connect to an Elasticsearch serverless deployment, there's no visual indication in the UI that they're in serverless mode. This can lead to confusion about available features and capabilities, as serverless mode has some limitations compared to standard Elasticsearch deployments.

## Solution

- **Backend**: Added `/api/mode` endpoint that detects serverless mode by checking the Elasticsearch cluster info
- **Frontend**: Added mode detection API call and visual indicator in the Projects page
- **UI**: Displays a warning-colored badge with cloud icon when in serverless mode

## Changes Made

### Backend Changes
- **`src/server/flask.py`**: Added `/api/mode` endpoint that:
  - Calls `es("studio").info()` to get cluster information
  - Checks `version.build_flavor` for "serverless" value
  - Returns mode status and cluster info

### Frontend Changes
- **`src/ui/js/api.js`**: Added `api.mode_get()` function to call the new endpoint
- **`src/ui/js/Pages/Projects/Projects.js`**: 
  - Added mode state management
  - Added `useEffect` to load mode on component mount
  - Added `renderModeIndicator()` function that displays badge when in serverless mode
  - Updated Page component to include mode indicator in header buttons

## Technical Details

### Serverless Detection
The detection works by checking the `build_flavor` field in the Elasticsearch cluster info response:
```json
{
  "version": {
    "build_flavor": "serverless",
    ...
  }
}
```

### UI Implementation
- Badge only appears when `mode === 'serverless'`
- Uses EUI Badge component with warning color and cloud icon
- Positioned in the page header alongside the "Create a new project" button
- Gracefully handles errors by setting mode to 'unknown' if detection fails

## Testing

To test this feature:
1. Connect to an Elasticsearch serverless deployment
2. Navigate to the Projects page
3. Verify the "Mode: Serverless" badge appears in the header
4. Connect to a standard Elasticsearch deployment
5. Verify no badge appears

## Screenshots

*[Screenshots would be added here showing the badge in serverless mode]*

## Related Issues

Closes #[issue-number] (if applicable)

## Checklist

- [x] Code follows the project's style guidelines
- [x] Self-review of code completed
- [x] Code is documented where necessary
- [x] Tests pass (if applicable)
- [x] Feature works in both serverless and standard modes
- [x] Error handling implemented for mode detection failures 