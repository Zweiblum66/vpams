# CDN Deployment Guide for MAMS

## Overview

This guide provides step-by-step instructions for deploying and configuring the Content Delivery Network (CDN) for MAMS static assets. The CDN implementation supports multiple providers (CloudFront, Cloudflare, Azure CDN) and includes automatic failover, optimization, and monitoring.

## Prerequisites

- AWS Account (for CloudFront)
- Cloudflare Account (optional)
- Azure Account (optional)
- Terraform 1.5+ installed
- AWS CLI configured
- Domain name with DNS control

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   Users                                 │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│                CDN Edge Locations                       │
├─────────────────────────────────────────────────────────┤
│  CloudFront │ Cloudflare │ Azure CDN │ Fastly          │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│               Origin Servers                            │
├─────────────────────────────────────────────────────────┤
│  S3 Buckets │ Load Balancer │ Application Servers      │
└─────────────────────────────────────────────────────────┘
```

## Deployment Steps

### 1. Prepare Static Assets

#### Build Frontend Assets
```bash
cd frontend
npm run build:cdn

# This creates optimized assets in dist/ with:
# - Minified JS/CSS
# - Compressed images (WebP with fallbacks)
# - Brotli/Gzip pre-compressed files
# - Hashed filenames for cache busting
```

#### Upload to S3 Origin
```bash
# Create S3 bucket for static assets
aws s3 mb s3://mams-static-assets-prod

# Configure bucket for static website hosting
aws s3 website s3://mams-static-assets-prod \
  --index-document index.html \
  --error-document error.html

# Sync assets with proper headers
aws s3 sync ./dist s3://mams-static-assets-prod \
  --cache-control "public, max-age=31536000" \
  --metadata-directive REPLACE \
  --exclude "*.html" \
  --exclude "sw.js"

# HTML files with shorter cache
aws s3 sync ./dist s3://mams-static-assets-prod \
  --cache-control "public, max-age=3600" \
  --metadata-directive REPLACE \
  --exclude "*" \
  --include "*.html" \
  --include "sw.js"
```

### 2. Deploy CloudFront Distribution

#### Using Terraform
```bash
cd infrastructure/terraform/cdn

# Initialize Terraform
terraform init

# Plan deployment
terraform plan -var-file=prod.tfvars

# Apply configuration
terraform apply -var-file=prod.tfvars
```

#### Manual AWS Console Setup
1. Navigate to CloudFront Console
2. Click "Create Distribution"
3. Configure Origin:
   - Origin Domain: `mams-static-assets-prod.s3.amazonaws.com`
   - Origin Path: `/`
   - Origin Access: Use OAC (Origin Access Control)
4. Configure Behaviors:
   - Path Pattern: `*`
   - Viewer Protocol Policy: Redirect HTTP to HTTPS
   - Allowed Methods: GET, HEAD, OPTIONS
   - Cache Policy: Use custom policy from `cdn-config.yaml`
5. Configure Distribution Settings:
   - Price Class: Use all edge locations
   - Alternate Domain Names: `cdn.mams.example.com`
   - SSL Certificate: Use ACM certificate
   - Enable IPv6
   - Enable HTTP/2 and HTTP/3

### 3. Configure DNS

#### Route 53 Configuration
```bash
# Create CNAME record
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "cdn.mams.example.com",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{
          "Value": "d1234567890.cloudfront.net"
        }]
      }
    }]
  }'
```

### 4. Configure CDN Service

#### Update Environment Variables
```bash
# .env.production
CDN_PROVIDER=cloudfront
CDN_CLOUDFRONT_DISTRIBUTION_ID=E1234567890ABC
CDN_CLOUDFRONT_DOMAIN=d1234567890.cloudfront.net
CDN_CUSTOM_DOMAIN=cdn.mams.example.com
CDN_SIGNING_KEY_ID=K1234567890ABC
CDN_SIGNING_PRIVATE_KEY_PATH=/secrets/cloudfront-private-key.pem
```

#### Deploy CDN Service
```bash
# Build and deploy CDN service
cd services/cdn-service
docker build -t mams-cdn-service:latest .
docker tag mams-cdn-service:latest your-registry/mams-cdn-service:latest
docker push your-registry/mams-cdn-service:latest

# Update Kubernetes deployment
kubectl apply -f k8s/cdn-service-deployment.yaml
```

### 5. Enable Multi-CDN (Optional)

#### Add Cloudflare
1. Add domain to Cloudflare
2. Configure Page Rules:
   ```
   URL: cdn.mams.example.com/*
   Settings:
   - Cache Level: Cache Everything
   - Edge Cache TTL: 1 month
   - Browser Cache TTL: 1 year
   ```
3. Update CDN service config:
   ```yaml
   providers:
     cloudflare:
       enabled: true
       zone_id: ${CLOUDFLARE_ZONE_ID}
       api_key: ${CLOUDFLARE_API_KEY}
   ```

#### Add Azure CDN
```bash
# Create CDN profile
az cdn profile create \
  --name mams-cdn-profile \
  --resource-group mams-prod \
  --sku Standard_Microsoft

# Create endpoint
az cdn endpoint create \
  --name mams-static \
  --profile-name mams-cdn-profile \
  --resource-group mams-prod \
  --origin mams-static-assets-prod.s3.amazonaws.com
```

### 6. Configure Cache Rules

#### Cache-Control Headers
```yaml
# infrastructure/cdn/cache-rules.yaml
rules:
  - pattern: "*.js"
    headers:
      Cache-Control: "public, max-age=31536000, immutable"
      
  - pattern: "*.css"
    headers:
      Cache-Control: "public, max-age=31536000, immutable"
      
  - pattern: "*.jpg|*.jpeg|*.png|*.gif|*.webp"
    headers:
      Cache-Control: "public, max-age=2592000"
      
  - pattern: "*.woff|*.woff2|*.ttf|*.eot"
    headers:
      Cache-Control: "public, max-age=31536000"
      
  - pattern: "index.html"
    headers:
      Cache-Control: "public, max-age=3600, must-revalidate"
```

#### Invalidation Strategy
```bash
# Invalidate specific paths
aws cloudfront create-invalidation \
  --distribution-id E1234567890ABC \
  --paths "/index.html" "/app.*.js" "/app.*.css"

# Invalidate all content (use sparingly)
aws cloudfront create-invalidation \
  --distribution-id E1234567890ABC \
  --paths "/*"
```

### 7. Security Configuration

#### Enable WAF
```bash
# Create WAF ACL
aws wafv2 create-web-acl \
  --name mams-cdn-waf \
  --scope CLOUDFRONT \
  --default-action Allow={} \
  --rules file://waf-rules.json

# Associate with CloudFront
aws wafv2 associate-web-acl \
  --web-acl-arn arn:aws:wafv2:us-east-1:123456789012:global/webacl/mams-cdn-waf \
  --resource-arn arn:aws:cloudfront::123456789012:distribution/E1234567890ABC
```

#### Configure Geo-Restrictions
```yaml
# terraform/cdn/main.tf
restrictions {
  geo_restriction {
    restriction_type = "blacklist"
    locations        = ["CN", "KP"]  # Example: China, North Korea
  }
}
```

### 8. Monitoring Setup

#### CloudWatch Alarms
```bash
# High error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name cdn-high-error-rate \
  --alarm-description "CDN error rate above 5%" \
  --metric-name 4xxErrorRate \
  --namespace AWS/CloudFront \
  --statistic Average \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2

# Origin latency alarm
aws cloudwatch put-metric-alarm \
  --alarm-name cdn-origin-latency \
  --alarm-description "Origin latency above 1000ms" \
  --metric-name OriginLatency \
  --namespace AWS/CloudFront \
  --statistic Average \
  --period 300 \
  --threshold 1000 \
  --comparison-operator GreaterThanThreshold
```

#### Custom Metrics
```python
# Send custom metrics to CloudWatch
import boto3
from datetime import datetime

cloudwatch = boto3.client('cloudwatch')

def send_cdn_metrics(cache_hit_rate, bandwidth_gb):
    cloudwatch.put_metric_data(
        Namespace='MAMS/CDN',
        MetricData=[
            {
                'MetricName': 'CacheHitRate',
                'Value': cache_hit_rate,
                'Unit': 'Percent',
                'Timestamp': datetime.utcnow()
            },
            {
                'MetricName': 'BandwidthUsage',
                'Value': bandwidth_gb,
                'Unit': 'Gigabytes',
                'Timestamp': datetime.utcnow()
            }
        ]
    )
```

### 9. Performance Testing

#### Load Testing with Artillery
```yaml
# artillery/cdn-load-test.yml
config:
  target: "https://cdn.mams.example.com"
  phases:
    - duration: 60
      arrivalRate: 100
      rampTo: 1000
  
scenarios:
  - name: "Static Asset Loading"
    flow:
      - get:
          url: "/app.bundle.js"
      - get:
          url: "/styles.bundle.css"
      - get:
          url: "/logo.webp"
      - think: 5
      - get:
          url: "/fonts/roboto.woff2"
```

Run test:
```bash
artillery run artillery/cdn-load-test.yml
```

#### Verify CDN Performance
```bash
# Check cache headers
curl -I https://cdn.mams.example.com/app.bundle.js

# Verify compression
curl -H "Accept-Encoding: br,gzip" -I https://cdn.mams.example.com/app.bundle.js

# Test from different locations
for location in us-east-1 eu-west-1 ap-southeast-1; do
  echo "Testing from $location"
  time curl -s https://cdn.mams.example.com/app.bundle.js > /dev/null
done
```

### 10. CI/CD Integration

#### GitHub Actions Workflow
```yaml
# .github/workflows/deploy-cdn.yml
name: Deploy CDN Assets

on:
  push:
    branches: [main]
    paths:
      - 'frontend/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '20'
          
      - name: Build assets
        run: |
          cd frontend
          npm ci
          npm run build:cdn
          
      - name: Deploy to S3
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        run: |
          aws s3 sync ./frontend/dist s3://mams-static-assets-prod \
            --delete \
            --cache-control "public, max-age=31536000"
            
      - name: Invalidate CDN
        run: |
          aws cloudfront create-invalidation \
            --distribution-id ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID }} \
            --paths "/*"
```

## Troubleshooting

### Common Issues

#### 1. CORS Errors
```nginx
# Add CORS headers in CloudFront
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, HEAD, OPTIONS
Access-Control-Max-Age: 3600
```

#### 2. SSL Certificate Issues
- Ensure certificate covers all domains
- Certificate must be in us-east-1 for CloudFront
- Use AWS Certificate Manager (ACM)

#### 3. Cache Not Updating
```bash
# Force cache refresh
curl -H "Cache-Control: no-cache" https://cdn.mams.example.com/app.js

# Check cache headers
curl -I https://cdn.mams.example.com/app.js | grep -i cache
```

#### 4. Slow Origin Response
- Enable CloudFront caching for error responses
- Configure origin timeouts appropriately
- Use origin shield for better cache hit rates

## Best Practices

1. **Version Assets**: Use hash in filenames for cache busting
2. **Compress Everything**: Enable Brotli and Gzip
3. **Set Proper Headers**: Configure cache-control based on file type
4. **Monitor Usage**: Set up billing alerts for CDN costs
5. **Use Origin Shield**: Reduce origin load for popular content
6. **Enable HTTP/3**: Better performance for modern browsers
7. **Implement Failover**: Use multiple CDN providers
8. **Security Headers**: Add CSP, HSTS, X-Frame-Options

## Cost Optimization

### CloudFront Cost Reduction
1. Use appropriate price class (not all edge locations)
2. Enable compression at origin
3. Set long cache times for static assets
4. Use Origin Shield for popular content
5. Monitor and optimize data transfer

### Estimated Monthly Costs
- **Small (< 1TB/month)**: ~$100
- **Medium (1-10TB/month)**: ~$850
- **Large (10-100TB/month)**: ~$8,000
- **Enterprise (> 100TB/month)**: Custom pricing

## Maintenance

### Regular Tasks
1. **Weekly**: Review cache hit ratios
2. **Monthly**: Analyze bandwidth usage and costs
3. **Quarterly**: Update CDN rules and optimizations
4. **Annually**: Review CDN provider contracts

### Monitoring Checklist
- [ ] Cache hit ratio > 90%
- [ ] Origin latency < 200ms
- [ ] 4xx error rate < 1%
- [ ] 5xx error rate < 0.1%
- [ ] Bandwidth costs within budget
- [ ] Security rules up to date

## Rollback Procedure

If issues occur after deployment:

1. **Immediate Rollback**:
   ```bash
   # Revert CloudFront to previous config
   aws cloudfront get-distribution-config --id E1234567890ABC > backup.json
   aws cloudfront update-distribution --id E1234567890ABC --cli-input-json file://previous-config.json
   ```

2. **DNS Failover**:
   ```bash
   # Switch DNS to origin directly
   aws route53 change-resource-record-sets \
     --hosted-zone-id Z1234567890ABC \
     --change-batch file://failover-dns.json
   ```

3. **Disable CDN in Application**:
   ```bash
   # Update environment variable
   kubectl set env deployment/frontend-app CDN_ENABLED=false
   ```

## Support

For CDN-related issues:
1. Check CloudWatch metrics and logs
2. Review WAF blocked requests
3. Verify origin server health
4. Contact AWS Support for CloudFront issues
5. Escalate to DevOps team if needed