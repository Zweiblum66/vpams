# Zapier Integration Guide

## Overview

The MAMS Zapier integration allows you to connect MAMS with 5,000+ apps through Zapier's automation platform. You can trigger actions in other apps when events occur in MAMS, and vice versa.

## Key Features

- **Instant Triggers**: Real-time notifications when assets are created, updated, or workflow events occur
- **Actions**: Create assets, update metadata, and trigger workflows from other apps
- **Searches**: Find assets and projects in MAMS from your Zaps
- **Filters**: Control which events trigger your Zaps based on asset type, project, etc.

## Setup Instructions

### 1. Generate API Key in MAMS

1. Navigate to Settings → Integrations in MAMS
2. Click "Create New Integration"
3. Select "Zapier" as the integration type
4. Generate and copy your API key

### 2. Connect MAMS to Zapier

1. In Zapier, search for "MAMS" when creating a new Zap
2. Choose a trigger or action
3. Click "Connect a new account"
4. Enter:
   - Your MAMS instance URL (e.g., `https://mams.yourcompany.com`)
   - The API key from step 1

### 3. Configure Your Zap

Choose from available triggers and actions to build your automation.

## Available Triggers

### Asset Created
Triggers when a new asset is uploaded to MAMS.

**Available Fields:**
- Asset ID
- Asset Name
- Asset Type (video, image, audio, document)
- File Size
- File Path
- Duration (for video/audio)
- Resolution (for video/images)
- Project ID
- Uploaded By
- Upload Timestamp

**Filter Options:**
- By asset type
- By project
- By uploader

### Workflow Completed
Triggers when a workflow finishes processing.

**Available Fields:**
- Workflow ID
- Workflow Type
- Result (success/failed)
- Duration
- Input Asset(s)
- Output Asset(s)
- Triggered By

### Project Created
Triggers when a new project is created.

**Available Fields:**
- Project ID
- Project Name
- Description
- Created By
- Team Size
- Project Type

## Available Actions

### Create Asset
Upload a new asset to MAMS.

**Required Fields:**
- File URL or content
- Asset Name
- Asset Type

**Optional Fields:**
- Project ID
- Metadata fields
- Tags

### Update Asset Metadata
Update metadata for an existing asset.

**Required Fields:**
- Asset ID
- Metadata fields to update

### Trigger Workflow
Start a workflow on an asset.

**Required Fields:**
- Asset ID
- Workflow Type

**Optional Fields:**
- Workflow parameters
- Priority

## Available Searches

### Find Asset
Search for assets by various criteria.

**Search By:**
- Name
- Type
- Project
- Tags
- Date range

### Find Project
Search for projects.

**Search By:**
- Name
- Status
- Owner
- Date range

## Common Use Cases

### 1. Social Media Publishing
**Trigger**: Asset Created (type: image)
**Action**: Post to Instagram/Twitter/Facebook

Automatically share approved images to social media platforms.

### 2. Video Processing Notification
**Trigger**: Workflow Completed (type: transcoding)
**Action**: Send Slack message or email

Notify team members when video processing is complete.

### 3. Project Management Integration
**Trigger**: Project Created
**Action**: Create Asana/Trello/Monday.com project

Sync MAMS projects with your project management tool.

### 4. Cloud Backup
**Trigger**: Asset Created
**Action**: Upload to Google Drive/Dropbox

Automatically backup new assets to cloud storage.

### 5. Content Calendar
**Trigger**: Asset Updated (metadata: publish_date)
**Action**: Create Google Calendar event

Schedule content publication based on metadata.

## Advanced Features

### Webhooks
For developers, MAMS supports direct webhook integration:

```http
POST /api/v1/integrations/zapier/webhook/{integration_id}
```

### Custom Fields
Pass custom metadata fields that can be used in your Zaps:

```json
{
  "custom_field_1": "value1",
  "custom_field_2": "value2"
}
```

### Batch Operations
Some actions support batch operations for efficiency:
- Bulk metadata updates
- Multiple asset creation

## Best Practices

1. **Use Filters**: Reduce unnecessary Zap runs by filtering events
2. **Error Handling**: Set up error notifications in your Zaps
3. **Rate Limits**: MAMS allows 1000 API calls per hour
4. **Testing**: Always test your Zaps with sample data first

## Troubleshooting

### Authentication Issues
- Verify your API key is active
- Check your MAMS instance URL includes https://
- Ensure your user has appropriate permissions

### Missing Data
- Some fields may be empty depending on asset type
- Use Zapier's formatter to handle missing fields

### Webhook Delays
- Webhooks are typically instant (< 1 second)
- Check your Zapier plan for webhook limits

## API Reference

The Zapier integration uses the following MAMS API endpoints:

- `GET /api/v1/integrations/zapier/auth/test` - Test authentication
- `POST /api/v1/integrations/zapier/triggers` - Create triggers
- `GET /api/v1/integrations/zapier/sample-data/{event_type}` - Get sample data
- `POST /api/v1/integrations/zapier/searches/assets` - Search assets
- `POST /api/v1/integrations/zapier/actions/create-asset` - Create assets

## Support

For issues specific to the MAMS Zapier integration:
- Check the [MAMS documentation](https://docs.mams.io/integrations/zapier)
- Contact MAMS support: support@mams.io

For Zapier-specific issues:
- Visit [Zapier Help](https://help.zapier.com)
- Check your Zap history for error details