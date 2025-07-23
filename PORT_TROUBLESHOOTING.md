# MAMS Port 3000/8080 Troubleshooting Guide

## Current Situation
- Infrastructure services (MinIO, RabbitMQ, etc.) are accessible on their ports
- Ports 3000 and 8080 are not accessible from outside the server
- Services appear to start but cannot be reached externally

## Diagnostic Steps to Run on Server

### 1. Check Running Services
```bash
# SSH to server
ssh jens@192.168.178.186

# Check Docker containers
docker ps -a | grep -E "(test-nginx|mams-web|mams-api|3000|8080)"

# Check listening ports
sudo netstat -tlpn | grep -E "(3000|8080)"
# or
sudo ss -tlpn | grep -E "(3000|8080)"
```

### 2. Test Local Connectivity
```bash
# Test if services work locally
curl -I http://localhost:3000
curl http://localhost:8080/health
```

### 3. Check Firewall Settings
```bash
# Check UFW
sudo ufw status verbose

# If UFW is active, allow ports
sudo ufw allow 3000/tcp
sudo ufw allow 8080/tcp
sudo ufw reload

# Check iptables
sudo iptables -L -n -v | grep -E "(3000|8080)"
```

### 4. Check Docker Network Settings
```bash
# Inspect Docker's iptables rules
sudo iptables -t nat -L DOCKER -n -v

# Check Docker daemon settings
sudo systemctl status docker
docker info | grep -i driver
```

### 5. Network Interface Check
```bash
# Check if Docker is binding to all interfaces
docker inspect test-nginx | grep -A 10 "PortBindings"

# Check network interfaces
ip addr show
```

## Manual Service Start Commands

### Option 1: Direct Docker Run
```bash
# Frontend
docker run -d --name mams-frontend -p 3000:80 nginx:alpine

# API
docker run -d --name mams-api -p 8080:8080 -e PORT=8080 python:3.11-alpine sh -c "pip install fastapi uvicorn && python -c 'from fastapi import FastAPI; app = FastAPI(); app.get(\"/health\")(lambda: {\"status\": \"ok\"})' && uvicorn main:app --host 0.0.0.0 --port 8080"
```

### Option 2: Host Network Mode
```bash
# Try with host network mode
docker run -d --name mams-frontend --network host nginx:alpine
```

### Option 3: Python HTTP Server (Non-Docker)
```bash
# Kill Docker containers
docker stop mams-frontend mams-api
docker rm mams-frontend mams-api

# Start Python server directly
cd /opt/mams
sudo python3 -m http.server 3000 --bind 0.0.0.0 &
```

## Possible Issues and Solutions

### 1. Firewall Blocking
**Solution:**
```bash
# Disable firewall temporarily to test
sudo ufw disable
# Test access
# Re-enable: sudo ufw enable
```

### 2. Docker iptables Issues
**Solution:**
```bash
# Restart Docker
sudo systemctl restart docker

# Or disable Docker's iptables management
# Edit /etc/docker/daemon.json:
{
  "iptables": false
}
sudo systemctl restart docker
```

### 3. VMware Network Configuration
- Check if VMware has any port forwarding or firewall rules
- Ensure the VM's network adapter is in "Bridged" mode
- Check VMware's virtual network editor settings

### 4. Ubuntu's Default Firewall
```bash
# Check if ufw is installed and active
sudo ufw status

# Check systemd firewall
sudo systemctl status firewalld
```

## Verification Steps

After applying fixes:

1. **Local Test:**
   ```bash
   curl -I http://localhost:3000
   ```

2. **External Test:**
   ```bash
   # From your local machine
   curl -I http://192.168.178.186:3000
   nc -zv 192.168.178.186 3000
   ```

3. **Browser Test:**
   - Open http://192.168.178.186:3000
   - Check browser console for errors

## Alternative Access Methods

If ports 3000/8080 remain blocked:

1. **Use Existing Ports:**
   - Deploy frontend on port 9001 (alongside MinIO)
   - Use nginx on port 80

2. **SSH Tunnel:**
   ```bash
   # From your local machine
   ssh -L 3000:localhost:3000 jens@192.168.178.186
   # Then access http://localhost:3000
   ```

3. **Use Infrastructure Services:**
   - Access MinIO Console: http://192.168.178.186:9001
   - Access RabbitMQ: http://192.168.178.186:15672
   - These are working, so the network is functional

## Next Steps

1. Run the diagnostic commands above
2. Check VMware network settings
3. Try the alternative deployment methods
4. Consider using ports that are already working (80, 443, or share with existing services)

The infrastructure is deployed and working. The issue is specifically with exposing new ports 3000/8080 to external access.