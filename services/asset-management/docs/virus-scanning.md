# Virus Scanning Integration

The Asset Management Service includes comprehensive virus scanning capabilities to protect against malicious files being uploaded to the system.

## Features

- **Multiple Scanner Support**: Supports both local (ClamAV) and cloud-based (VirusTotal) scanners
- **Automatic Scanning**: Files are automatically scanned during the upload validation process
- **Configurable**: Can be enabled/disabled via environment variables
- **Fallback Support**: If one scanner fails, others are tried
- **Performance Optimized**: Scans run asynchronously without blocking uploads
- **Detailed Reporting**: Scan results are included in file validation reports

## Supported Scanners

### 1. ClamAV (Local)
- Open-source antivirus engine
- Runs locally for fast scanning
- No file size limits
- Requires ClamAV daemon (clamd) to be running

### 2. VirusTotal (Cloud)
- Cloud-based scanning using 70+ antivirus engines
- Requires API key
- 32MB file size limit for free tier
- Provides comprehensive threat detection

### 3. Hybrid Analysis (Planned)
- Advanced malware analysis
- Behavioral analysis capabilities
- Requires API key

## Configuration

### Environment Variables

```env
# Enable/disable virus scanning
ENABLE_VIRUS_SCAN=true

# VirusTotal configuration
VIRUS_SCAN_API_URL=https://www.virustotal.com/api/v3
VIRUS_SCAN_API_KEY=your-virustotal-api-key
```

### ClamAV Setup

1. Install ClamAV:
```bash
# Ubuntu/Debian
sudo apt-get install clamav clamav-daemon

# macOS
brew install clamav

# Docker
docker run -d -p 3310:3310 clamav/clamav:latest
```

2. Update virus definitions:
```bash
sudo freshclam
```

3. Start ClamAV daemon:
```bash
sudo systemctl start clamav-daemon  # Linux
# or
sudo clamd  # Direct start
```

### Docker Compose Integration

Add ClamAV to your docker-compose.yml:

```yaml
services:
  clamav:
    image: clamav/clamav:latest
    container_name: mams-clamav
    ports:
      - "3310:3310"
    volumes:
      - clamav_data:/var/lib/clamav
    environment:
      - CLAMAV_NO_FRESHCLAMD=false
    healthcheck:
      test: ["CMD", "clamdscan", "--ping"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  clamav_data:
```

## API Endpoints

### Check Scanner Status

```bash
GET /api/v1/assets/virus-scanner/status

Response:
{
  "enabled": true,
  "scanners": [
    {
      "name": "ClamAV",
      "available": true
    },
    {
      "name": "VirusTotal",
      "available": true
    }
  ]
}
```

## Integration with File Upload

Virus scanning is automatically integrated into the file upload validation process:

1. File is uploaded to temporary storage
2. File validation runs (size, type, etc.)
3. Virus scan is performed if enabled
4. If virus is detected, upload is rejected
5. Scan results are included in validation report

## Error Handling

- If all scanners fail but `fail_on_error=false`, upload continues with warning
- If virus is detected, upload is always rejected
- Scanner failures are logged but don't block the service

## Performance Considerations

- ClamAV scanning is fast for most files (<1 second)
- VirusTotal may take 30-60 seconds for analysis
- Large files may timeout with cloud scanners
- Consider scanning in background for very large files

## Security Best Practices

1. **Always Enable in Production**: Keep virus scanning enabled in production environments
2. **Regular Updates**: Ensure ClamAV virus definitions are updated daily
3. **Monitor Failures**: Set up alerts for scanner failures
4. **Quarantine**: Consider implementing quarantine for suspicious files
5. **Logging**: All scan results are logged for audit purposes

## Troubleshooting

### ClamAV Not Connecting

1. Check if clamd is running:
```bash
ps aux | grep clamd
```

2. Test connection:
```bash
echo "PING" | nc localhost 3310
```

3. Check logs:
```bash
sudo journalctl -u clamav-daemon
```

### VirusTotal Rate Limits

- Free tier: 4 requests/minute, 500 requests/day
- Consider implementing rate limiting or caching

### Scanner Timeouts

- Increase timeout in virus_scanner.py if needed
- Consider background scanning for large files

## Future Enhancements

1. **Quarantine System**: Move infected files to quarantine
2. **Scheduled Rescans**: Periodically rescan stored files
3. **Custom Rules**: Support for custom malware signatures
4. **Webhooks**: Notify admins of detected threats
5. **Statistics**: Track scan metrics and threat trends