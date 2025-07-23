# Puppeteer MCP Setup for MAMS Testing

## Overview
The Puppeteer MCP (Model Context Protocol) server has been set up to enable automated testing of the MAMS deployment through Claude Desktop.

## Installation Location
- **Directory**: `/Users/jens.lindner/Documents/development/MyVideoMAM/.mcp/puppeteer/`
- **Main file**: `index.js`

## Features
The Puppeteer MCP server provides the following tools for testing MAMS:

### 1. `test_mams_service`
Tests if a specific MAMS service is accessible and functioning.
- Parameters:
  - `service`: 'minio', 'rabbitmq', 'frontend', or 'api'
  - `timeout`: Timeout in milliseconds (default: 30000)
- Returns: Service status and screenshot

### 2. `login_mams_service`
Logs into MinIO or RabbitMQ and verifies authentication.
- Parameters:
  - `service`: 'minio' or 'rabbitmq'
  - `username`: Login username
  - `password`: Login password
- Returns: Login success status and screenshot

### 3. `check_all_services`
Checks all MAMS services and returns a comprehensive status report.
- Parameters:
  - `screenshot`: Boolean to include screenshots (default: false)
- Returns: Status report for all services

### 4. `test_minio_operations`
Tests MinIO operations like bucket creation.
- Parameters:
  - `username`: MinIO username
  - `password`: MinIO password
  - `bucketName`: Name of bucket to create (default: 'test-bucket')
- Returns: Operation results

## Claude Code Configuration

To use this MCP server with Claude Code, the configuration has been automatically set up:

1. **Configuration File**: `.mcp.json` in the project root
   - This file has been created at `/Users/jens.lindner/Documents/development/MyVideoMAM/.mcp.json`

2. **Configuration Content**:
```json
{
  "mcpServers": {
    "puppeteer-mams": {
      "command": "node",
      "args": ["/Users/jens.lindner/Documents/development/MyVideoMAM/.mcp/puppeteer/index.js"],
      "env": {
        "NODE_ENV": "production"
      }
    }
  }
}
```

3. **Activation**: The MCP server will be available automatically when you're in the MAMS project directory

4. **Security Note**: Claude Code will prompt for approval before using the MCP server from the `.mcp.json` file

## Usage Examples

Once configured, you can use the Puppeteer tools in Claude Code:

### Test MinIO Service
```
Use the puppeteer-mams tool to test if MinIO is accessible
```

### Login to RabbitMQ
```
Use the puppeteer-mams tool to login to RabbitMQ with username 'mams' and password 'mams_rabbit_prod_2024'
```

### Check All Services
```
Use the puppeteer-mams tool to check all MAMS services with screenshots
```

## Troubleshooting

### Connection Issues
If services are unreachable from your local machine:
1. Ensure you're on the same network as the server (192.168.178.186)
2. Check firewall settings on both the server and your local machine
3. Verify services are running: `ssh jens@192.168.178.186 'sudo docker ps'`

### Puppeteer Issues
If Puppeteer fails to launch:
1. Install Chrome/Chromium if not present
2. Check for missing dependencies: `npm ls puppeteer`
3. Try running with visible browser: Change `headless: 'new'` to `headless: false`

### MCP Server Issues
If the MCP server doesn't appear in Claude Code:
1. Ensure you're in the project directory containing `.mcp.json`
2. Check that Node.js is in your PATH
3. Test the server manually: `node /path/to/index.js`
4. Approve the MCP server when Claude Code prompts
5. Check Claude Code logs for errors

## Manual Testing

You can test the Puppeteer setup manually:

```bash
cd /Users/jens.lindner/Documents/development/MyVideoMAM/.mcp/puppeteer
node simple-test.js
```

This will check if the MAMS services are accessible from your machine.

## Network Configuration

For the Puppeteer tests to work from your local machine, ensure:
1. Your machine can reach 192.168.178.186
2. Ports 9001 (MinIO) and 15672 (RabbitMQ) are open
3. No VPN is blocking local network access

## Next Steps

1. Configure Claude Desktop with the MCP server
2. Test the connection to MAMS services
3. Use the Puppeteer tools to automate deployment testing
4. Create additional test scenarios as needed