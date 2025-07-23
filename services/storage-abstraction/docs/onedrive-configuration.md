# OneDrive Storage Driver Configuration

The OneDrive storage driver allows MAMS to use Microsoft OneDrive and SharePoint as storage backends for media assets using the Microsoft Graph API.

## Prerequisites

1. A Microsoft 365 account or Azure Active Directory
2. An Azure App Registration for Microsoft Graph API access
3. Appropriate permissions for OneDrive/SharePoint access

## Creating an Azure App Registration

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to Azure Active Directory > App registrations
3. Click "New registration"
4. Configure the app:
   - Name: "MAMS Storage Integration"
   - Supported account types: Choose based on your needs
   - Redirect URI: (Optional for OAuth flow) `http://localhost:8080/callback`
5. After creation, note the:
   - Application (client) ID
   - Directory (tenant) ID

## Setting up Authentication

### Option 1: Client Credentials (Service Account)
1. In your app registration, go to "Certificates & secrets"
2. Create a new client secret
3. Note the secret value (shown only once)
4. Go to "API permissions" and add:
   - Microsoft Graph > Application permissions:
     - Files.Read.All
     - Files.ReadWrite.All
     - Sites.Read.All (if using SharePoint)
     - Sites.ReadWrite.All (if using SharePoint)
5. Grant admin consent for the permissions

### Option 2: OAuth2 with User Context
1. Go to "API permissions" and add:
   - Microsoft Graph > Delegated permissions:
     - Files.Read
     - Files.ReadWrite
     - Files.Read.All
     - Files.ReadWrite.All
     - offline_access (for refresh tokens)
2. Implement OAuth2 flow to get access and refresh tokens

## Configuration

Add the following to your storage configuration:

```yaml
storage_drivers:
  onedrive:
    type: onedrive
    # Required: Choose one authentication method
    access_token: "YOUR_ACCESS_TOKEN"  # For testing/development
    # OR use OAuth2/Client Credentials
    tenant_id: "YOUR_TENANT_ID"  # or "common" for multi-tenant
    client_id: "YOUR_CLIENT_ID"
    client_secret: "YOUR_CLIENT_SECRET"
    refresh_token: "YOUR_REFRESH_TOKEN"  # If using OAuth2
    
    # Drive configuration
    drive_type: "me"  # Options: "me" (personal), "sites" (SharePoint), "groups"
    # For SharePoint sites
    site_id: "contoso.sharepoint.com,da60e844-ba1d-49bc-b4d4-d5e36bae9019,712a596e-90a1-49e3-9b48-bfa80bee8740"
    # For Group drives
    group_id: "02bd9fd6-8f93-4758-87c3-1fb73740a315"
    
    # Optional: Path prefix for all files
    path_prefix: "/MAMS"
    # Optional: Chunk size for large uploads (default: 10MB)
    chunk_size: 10485760
    # Optional: Maximum file size (default: 250GB)
    max_file_size: 268435456000
```

## Environment Variables

You can also configure using environment variables:

```bash
# Required
ONEDRIVE_CLIENT_ID=your_client_id
ONEDRIVE_CLIENT_SECRET=your_client_secret
ONEDRIVE_TENANT_ID=your_tenant_id

# Optional
ONEDRIVE_ACCESS_TOKEN=your_access_token
ONEDRIVE_REFRESH_TOKEN=your_refresh_token
ONEDRIVE_DRIVE_TYPE=me
ONEDRIVE_SITE_ID=your_site_id
ONEDRIVE_PATH_PREFIX=/MAMS
ONEDRIVE_CHUNK_SIZE=10485760
```

## Drive Types

### Personal OneDrive (drive_type: "me")
Access the current user's OneDrive:
```yaml
drive_type: "me"
```

### SharePoint Site (drive_type: "sites")
Access a specific SharePoint site's document library:
```yaml
drive_type: "sites"
site_id: "contoso.sharepoint.com,da60e844-ba1d-49bc-b4d4-d5e36bae9019,712a596e-90a1-49e3-9b48-bfa80bee8740"
```

To find your site ID:
1. Use Graph Explorer: `https://graph.microsoft.com/v1.0/sites/contoso.sharepoint.com:/sites/teamsite`
2. Or use the SharePoint admin center

### Group Drive (drive_type: "groups")
Access a Microsoft 365 Group's shared drive:
```yaml
drive_type: "groups"
group_id: "02bd9fd6-8f93-4758-87c3-1fb73740a315"
```

## Features Supported

- ✅ File upload/download
- ✅ Streaming downloads
- ✅ Large file uploads (>4MB) using upload sessions
- ✅ File listing and metadata
- ✅ Copy/move operations
- ✅ Delete operations
- ✅ Presigned URLs (sharing links)
- ✅ Multipart uploads
- ✅ Storage usage metrics
- ✅ Automatic token refresh
- ❌ Storage tiers (not supported by OneDrive)
- ❌ Object versioning (limited support)
- ❌ Custom metadata

## Limitations

1. **File Size**: Maximum file size is 250GB
2. **Path Length**: Maximum path length is 400 characters
3. **Rate Limits**: Microsoft Graph has rate limits - implement retry logic
4. **Sharing Links**: Generated presigned URLs are public sharing links
5. **Special Characters**: Some characters are not allowed in file names

## Performance Considerations

1. **Chunk Size**: 
   - Recommended: 5-10MB chunks
   - Maximum: 60MB per chunk
   - Adjust based on network conditions

2. **Concurrent Operations**:
   - OneDrive supports concurrent uploads
   - Limit concurrent operations to avoid throttling

3. **Caching**:
   - Cache file metadata to reduce API calls
   - Use ETags for conditional requests

## Security Best Practices

1. **Authentication**:
   - Use app-only access for service accounts
   - Implement proper token storage and rotation
   - Never expose client secrets

2. **Permissions**:
   - Use least-privilege principle
   - Grant only required permissions
   - Regular permission audits

3. **Sharing Links**:
   - Set expiration on sharing links
   - Use "view" type for read-only access
   - Monitor shared link usage

4. **Data Residency**:
   - Be aware of data location requirements
   - Configure appropriate geo locations

## Monitoring

Monitor these metrics:
- API rate limit headers
- Token expiration
- Storage quota usage
- Upload/download performance
- Failed operations

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   ```
   401 Unauthorized
   ```
   - Verify token is valid
   - Check token expiration
   - Ensure proper permissions

2. **Permission Errors**
   ```
   403 Forbidden
   ```
   - Verify app permissions
   - Check admin consent
   - Confirm resource access

3. **Rate Limiting**
   ```
   429 Too Many Requests
   ```
   - Implement exponential backoff
   - Check Retry-After header
   - Reduce request frequency

4. **Invalid Paths**
   ```
   400 Bad Request - Invalid path
   ```
   - Remove special characters
   - Check path length
   - Verify parent folders exist

## Example Usage

```python
# Initialize storage service
storage_service = StorageService()
await storage_service.initialize()

# Upload a file to OneDrive
with open('video.mp4', 'rb') as f:
    data = f.read()
    await storage_service.put_object(
        'videos/2024/video.mp4',
        data,
        driver='onedrive'
    )

# Download a file
data = await storage_service.get_object(
    'videos/2024/video.mp4',
    driver='onedrive'
)

# Stream a large file
async for chunk in storage_service.get_object_stream(
    'videos/2024/large_video.mp4',
    chunk_size=5*1024*1024,  # 5MB chunks
    driver='onedrive'
):
    # Process chunk
    pass

# List files in a folder
objects, next_token = await storage_service.list_objects(
    prefix='videos/2024',
    driver='onedrive'
)

# Generate a sharing link
presigned_url = await storage_service.get_presigned_url(
    'videos/2024/video.mp4',
    operation='get',
    expires_in=86400,  # 24 hours
    driver='onedrive'
)

# Get storage usage
usage = await storage_service.get_storage_usage(driver='onedrive')
print(f"Used: {usage['used_bytes'] / 1024**3:.2f} GB")
print(f"Total: {usage['total_bytes'] / 1024**3:.2f} GB")
```

## SharePoint-Specific Features

When using SharePoint (drive_type: "sites"), additional features are available:

1. **Document Libraries**: Access specific document libraries
2. **Metadata**: SharePoint column data (read-only via this driver)
3. **Permissions**: Inherits SharePoint permissions
4. **Versioning**: SharePoint versioning is maintained

## Migration from Other Storage

To migrate from another storage driver to OneDrive:

1. Use the cross-driver copy functionality
2. Implement parallel uploads for performance
3. Verify checksums after migration
4. Update file references in your database

```python
# Example migration script
source_driver = 'local'
target_driver = 'onedrive'

objects, _ = await storage_service.list_objects(driver=source_driver)
for obj in objects:
    data = await storage_service.get_object(obj.key, driver=source_driver)
    await storage_service.put_object(obj.key, data, driver=target_driver)
```