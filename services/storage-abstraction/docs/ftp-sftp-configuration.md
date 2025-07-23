# FTP/SFTP Storage Driver Configuration

The FTP and SFTP storage drivers allow MAMS to use FTP and SFTP servers as storage backends for media assets.

## FTP Driver

### Prerequisites

1. An FTP server with appropriate access
2. FTP credentials (username/password or anonymous access)
3. Sufficient storage space and permissions

### Configuration

Add the following to your storage configuration:

```yaml
storage_drivers:
  ftp_storage:
    type: ftp
    host: "ftp.example.com"
    port: 21  # Default FTP port
    username: "your_username"
    password: "your_password"
    # Optional settings
    path_prefix: "/mams"  # Base directory for all files
    passive: true  # Use passive mode (recommended)
    timeout: 30  # Connection timeout in seconds
    encoding: "utf-8"  # Filename encoding
```

### Environment Variables

```bash
FTP_HOST=ftp.example.com
FTP_PORT=21
FTP_USERNAME=your_username
FTP_PASSWORD=your_password
FTP_PATH_PREFIX=/mams
FTP_PASSIVE=true
FTP_TIMEOUT=30
```

### Features Supported

- ✅ File upload/download
- ✅ Streaming downloads
- ✅ File listing and metadata
- ✅ Move operations (server-side rename)
- ✅ Delete operations
- ✅ Basic file information
- ❌ Copy operations (uses download/upload)
- ❌ Presigned URLs
- ❌ Multipart uploads
- ❌ Storage tiers

### Limitations

1. **Performance**: FTP is generally slower than modern protocols
2. **Security**: FTP transmits credentials in plain text
3. **Metadata**: Limited metadata compared to cloud storage
4. **Features**: No server-side copy, presigned URLs, or advanced features
5. **Concurrency**: Limited concurrent connection support

## SFTP Driver

### Prerequisites

1. An SSH/SFTP server with appropriate access
2. SSH credentials (password or SSH key)
3. Sufficient storage space and permissions

### Configuration

#### Password Authentication

```yaml
storage_drivers:
  sftp_storage:
    type: sftp
    host: "sftp.example.com"
    port: 22  # Default SSH port
    username: "your_username"
    password: "your_password"
    # Optional settings
    path_prefix: "/mams"  # Base directory for all files
    timeout: 30  # Connection timeout in seconds
    auto_add_host_key: false  # Auto-accept new host keys (use with caution)
```

#### Key-Based Authentication

```yaml
storage_drivers:
  sftp_storage:
    type: sftp
    host: "sftp.example.com"
    port: 22
    username: "your_username"
    key_filename: "/path/to/private/key"
    key_password: "key_passphrase"  # If key is encrypted
    path_prefix: "/mams"
    timeout: 30
    auto_add_host_key: false
```

### Environment Variables

```bash
# Common settings
SFTP_HOST=sftp.example.com
SFTP_PORT=22
SFTP_USERNAME=your_username
SFTP_PATH_PREFIX=/mams
SFTP_TIMEOUT=30
SFTP_AUTO_ADD_HOST_KEY=false

# Password auth
SFTP_PASSWORD=your_password

# Key auth
SFTP_KEY_FILENAME=/path/to/private/key
SFTP_KEY_PASSWORD=key_passphrase
```

### Features Supported

- ✅ File upload/download
- ✅ Streaming downloads
- ✅ File listing with full metadata
- ✅ Move operations (server-side rename)
- ✅ Delete operations
- ✅ File permissions and ownership info
- ✅ Storage usage information (if supported by server)
- ❌ Copy operations (uses download/upload)
- ❌ Presigned URLs
- ❌ Multipart uploads
- ❌ Storage tiers

### Security Best Practices

1. **Use SFTP over FTP**: SFTP is encrypted, FTP is not
2. **Key-Based Auth**: Prefer SSH keys over passwords
3. **Host Key Verification**: Disable `auto_add_host_key` in production
4. **Minimal Permissions**: Use accounts with minimal required permissions
5. **IP Restrictions**: Restrict access by IP if possible

## Performance Considerations

### FTP
1. **Passive Mode**: Use passive mode for better firewall compatibility
2. **Binary Mode**: Driver automatically uses binary mode for all transfers
3. **Connection Pooling**: Reuse connections when possible

### SFTP
1. **Compression**: Enable SSH compression for text files
2. **Concurrent Operations**: SFTP supports multiple operations per connection
3. **Chunk Size**: Adjust based on network conditions

### Common Optimization Tips
1. **Path Prefix**: Use a dedicated directory to improve listing performance
2. **Connection Timeout**: Adjust based on network latency
3. **Parallel Transfers**: Implement application-level parallelism

## Monitoring

Monitor these metrics:
- Connection success/failure rates
- Transfer speeds
- Authentication failures
- Timeout occurrences
- Storage usage (SFTP only)

## Troubleshooting

### FTP Issues

1. **Connection Failed**
   ```
   Failed to connect to FTP server
   ```
   - Check host and port
   - Verify firewall rules
   - Test with FTP client

2. **Authentication Failed**
   ```
   530 Login incorrect
   ```
   - Verify credentials
   - Check user permissions
   - Ensure account is not locked

3. **Passive Mode Issues**
   ```
   425 Can't open data connection
   ```
   - Enable passive mode
   - Check firewall for data port range
   - Configure server passive port range

4. **Encoding Issues**
   ```
   UnicodeDecodeError
   ```
   - Check filename encoding setting
   - Ensure server uses same encoding

### SFTP Issues

1. **Connection Failed**
   ```
   Connection refused
   ```
   - Check SSH service is running
   - Verify port (usually 22)
   - Check firewall rules

2. **Authentication Failed**
   ```
   Authentication failed
   ```
   - Verify username/password
   - Check SSH key permissions (600)
   - Ensure user has SFTP access

3. **Host Key Verification Failed**
   ```
   Host key verification failed
   ```
   - Add host to known_hosts
   - Or enable auto_add_host_key (dev only)

4. **Permission Denied**
   ```
   Permission denied
   ```
   - Check file/directory permissions
   - Verify user has write access
   - Check quota limits

## Example Usage

```python
# Initialize storage service
storage_service = StorageService()
await storage_service.initialize()

# Upload a file via FTP
with open('video.mp4', 'rb') as f:
    data = f.read()
    await storage_service.put_object(
        'videos/2024/video.mp4',
        data,
        driver='ftp_storage'
    )

# Download a file via SFTP
data = await storage_service.get_object(
    'videos/2024/video.mp4',
    driver='sftp_storage'
)

# Stream a large file
async for chunk in storage_service.get_object_stream(
    'videos/2024/large_video.mp4',
    chunk_size=1024*1024,  # 1MB chunks
    driver='sftp_storage'
):
    # Process chunk
    pass

# List files
objects, next_token = await storage_service.list_objects(
    prefix='videos/2024',
    driver='ftp_storage'
)

# Check if file exists
exists = await storage_service.exists(
    'videos/2024/video.mp4',
    driver='sftp_storage'
)

# Get storage usage (SFTP only)
usage = await storage_service.get_storage_usage(driver='sftp_storage')
if usage['total_bytes'] > 0:
    print(f"Used: {usage['used_bytes'] / 1024**3:.2f} GB")
    print(f"Total: {usage['total_bytes'] / 1024**3:.2f} GB")
```

## Migration Guide

### From FTP to SFTP

1. Set up SFTP access on the same server
2. Update configuration to use SFTP driver
3. No file migration needed if using same filesystem
4. Update any FTP-specific code

### From FTP/SFTP to Cloud Storage

```python
# Migration script
source_driver = 'ftp_storage'
target_driver = 's3'

# List all files
objects, _ = await storage_service.list_objects(driver=source_driver)

for obj in objects:
    # Download from FTP/SFTP
    data = await storage_service.get_object(obj.key, driver=source_driver)
    
    # Upload to cloud
    await storage_service.put_object(obj.key, data, driver=target_driver)
    
    # Verify and delete source
    if await storage_service.exists(obj.key, driver=target_driver):
        await storage_service.delete_object(obj.key, driver=source_driver)
```

## Advanced Configuration

### FTP with TLS (FTPS)

Currently not supported. Use SFTP for secure transfers.

### SFTP with Jump Host

For SFTP servers behind a jump host:

1. Set up SSH config (~/.ssh/config):
   ```
   Host jump-host
       HostName jump.example.com
       User jumpuser
   
   Host target-server
       HostName sftp.internal.com
       User sftpuser
       ProxyJump jump-host
   ```

2. Use the configured host:
   ```yaml
   sftp_storage:
     type: sftp
     host: "target-server"  # Uses SSH config
     username: "sftpuser"
     key_filename: "/path/to/key"
   ```

### Custom SFTP Subsystem

Some servers use custom SFTP paths:

```yaml
sftp_storage:
  type: sftp
  host: "custom.example.com"
  sftp_subsystem: "/usr/local/bin/sftp-server"  # If non-standard
```

## Compliance Considerations

1. **Data Residency**: FTP/SFTP keeps data on your servers
2. **Access Logs**: Enable and monitor server access logs
3. **Encryption**: Use SFTP for data in transit encryption
4. **Retention**: Implement server-side retention policies
5. **Audit Trail**: Maintain logs of all operations