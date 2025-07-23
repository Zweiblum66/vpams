# Dropbox Storage Driver Configuration

The Dropbox storage driver allows MAMS to use Dropbox as a storage backend for media assets.

## Prerequisites

1. A Dropbox account (Business account recommended for production)
2. A Dropbox App created in the [Dropbox App Console](https://www.dropbox.com/developers/apps)
3. Access token or OAuth2 credentials

## Creating a Dropbox App

1. Go to [Dropbox App Console](https://www.dropbox.com/developers/apps)
2. Click "Create app"
3. Choose "Scoped access"
4. Choose "Full Dropbox" or "App folder" based on your needs
5. Name your app (e.g., "MAMS Storage")
6. After creation, go to the Permissions tab and enable:
   - `files.content.write`
   - `files.content.read`
   - `files.metadata.write`
   - `files.metadata.read`
   - `sharing.write`
   - `sharing.read`
   - `account_info.read`

## Obtaining Access Token

### Option 1: Generate Access Token (Development)
1. In your app settings, go to the OAuth 2 section
2. Click "Generate" under "Generated access token"
3. Copy the token (note: it has no expiration but can be revoked)

### Option 2: OAuth2 Flow (Production)
1. Note your App Key and App Secret
2. Implement OAuth2 flow to get refresh token
3. Use refresh token to get access tokens as needed

## Configuration

Add the following to your storage configuration:

```yaml
storage_drivers:
  dropbox:
    type: dropbox
    access_token: "YOUR_ACCESS_TOKEN"
    # Optional: For OAuth2 flow
    app_key: "YOUR_APP_KEY"
    app_secret: "YOUR_APP_SECRET"
    refresh_token: "YOUR_REFRESH_TOKEN"
    # Optional: Path prefix for all files
    path_prefix: "/mams"
    # Optional: Chunk size for large uploads (default: 8MB)
    chunk_size: 8388608
    # Optional: Maximum file size (default: 150GB)
    max_file_size: 161061273600
```

## Environment Variables

You can also configure using environment variables:

```bash
# Required
DROPBOX_ACCESS_TOKEN=your_access_token

# Optional OAuth2
DROPBOX_APP_KEY=your_app_key
DROPBOX_APP_SECRET=your_app_secret
DROPBOX_REFRESH_TOKEN=your_refresh_token

# Optional settings
DROPBOX_PATH_PREFIX=/mams
DROPBOX_CHUNK_SIZE=8388608
```

## Features Supported

- ✅ File upload/download
- ✅ Streaming downloads
- ✅ Large file uploads (>150MB) using upload sessions
- ✅ File listing and metadata
- ✅ Copy/move operations
- ✅ Delete operations
- ✅ Presigned URLs (shared links)
- ✅ Multipart uploads
- ✅ Storage usage metrics
- ❌ Storage tiers (not supported by Dropbox)
- ❌ Object versioning (limited support)
- ❌ Server-side encryption configuration

## Limitations

1. **File Size**: Maximum file size is 150GB (configurable)
2. **Path Restrictions**: Some characters are not allowed in paths
3. **Rate Limits**: Dropbox API has rate limits - consider implementing retry logic
4. **Shared Links**: Generated presigned URLs are public shared links
5. **Range Requests**: Limited support for partial content requests

## Performance Considerations

1. **Chunk Size**: Adjust chunk_size based on your network conditions
   - Larger chunks (up to 150MB) for stable, fast connections
   - Smaller chunks (4-8MB) for unstable connections

2. **Concurrent Uploads**: Dropbox supports concurrent chunk uploads for better performance

3. **API Calls**: Minimize API calls by:
   - Batching operations where possible
   - Caching metadata
   - Using continuations for large listings

## Security Best Practices

1. **Access Token Storage**: 
   - Never commit access tokens to version control
   - Use environment variables or secure secret management
   - Rotate tokens regularly

2. **Permissions**: 
   - Use the minimum required permissions
   - Consider using App folder instead of Full Dropbox access

3. **Shared Links**:
   - Set expiration dates on shared links
   - Monitor shared link usage
   - Revoke unused links

## Monitoring

Monitor these metrics:
- API rate limit usage
- Storage quota usage
- Upload/download speeds
- Failed operations

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify access token is valid
   - Check app permissions
   - Ensure token hasn't been revoked

2. **Path Errors**
   - Ensure paths start with `/`
   - Check for invalid characters
   - Verify path_prefix configuration

3. **Quota Exceeded**
   - Check available storage space
   - Monitor storage usage regularly
   - Implement cleanup policies

4. **Rate Limiting**
   - Implement exponential backoff
   - Use batch operations
   - Monitor rate limit headers

## Example Usage

```python
# Initialize storage service
storage_service = StorageService()
await storage_service.initialize()

# Upload a file to Dropbox
with open('video.mp4', 'rb') as f:
    data = f.read()
    await storage_service.put_object(
        'videos/2024/video.mp4',
        data,
        driver='dropbox'
    )

# Download a file
data = await storage_service.get_object(
    'videos/2024/video.mp4',
    driver='dropbox'
)

# Stream a large file
async for chunk in storage_service.get_object_stream(
    'videos/2024/large_video.mp4',
    chunk_size=1024*1024,  # 1MB chunks
    driver='dropbox'
):
    # Process chunk
    pass

# Generate a presigned URL
presigned_url = await storage_service.get_presigned_url(
    'videos/2024/video.mp4',
    operation='get',
    expires_in=3600,  # 1 hour
    driver='dropbox'
)
```