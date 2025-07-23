# Multi-Region Deployment Guide for MAMS

## Overview

This guide provides comprehensive instructions for deploying the MAMS (Media Asset Management System) platform across multiple AWS regions. The multi-region deployment ensures high availability, low latency for global users, and disaster recovery capabilities.

## Architecture Overview

### Global Infrastructure

```
┌─────────────────────────────────────────────────────────────┐
│                    CloudFront CDN (Global)                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Route 53 (Global DNS)                      │
│                  - Latency-based routing                    │
│                  - Health checks                            │
│                  - Failover policies                        │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        │                                           │
        ▼                                           ▼
┌───────────────────┐                     ┌───────────────────┐
│  Primary Region   │                     │ Secondary Region  │
│   (us-east-1)     │◄────────────────────│  (eu-west-1)     │
│                   │   VPC Peering       │                   │
│  - EKS Cluster    │                     │  - EKS Cluster    │
│  - RDS Primary    │                     │  - RDS Replica    │
│  - OpenSearch     │                     │  - OpenSearch     │
│  - MongoDB        │                     │  - MongoDB        │
│  - Redis Master   │                     │  - Redis Replica  │
│  - S3 Bucket      │◄────────────────────│  - S3 Bucket      │
└───────────────────┘   S3 Replication    └───────────────────┘
```

### Key Components

1. **Global Load Balancing**
   - CloudFront CDN for static content and API caching
   - Route 53 for DNS with latency-based routing
   - Application Load Balancers in each region

2. **Data Replication**
   - PostgreSQL with read replicas across regions
   - MongoDB Atlas Global Clusters
   - OpenSearch cross-cluster replication
   - S3 cross-region replication for media files
   - Redis replication for session data

3. **Container Orchestration**
   - EKS clusters in each region
   - Horizontal Pod Autoscaling
   - Pod Disruption Budgets for high availability
   - Priority classes for critical services

## Prerequisites

### Required Tools

1. **AWS CLI** (v2.x)
   ```bash
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   sudo ./aws/install
   ```

2. **Terraform** (v1.0+)
   ```bash
   wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
   unzip terraform_1.6.0_linux_amd64.zip
   sudo mv terraform /usr/local/bin/
   ```

3. **kubectl** (v1.28+)
   ```bash
   curl -LO "https://dl.k8s.io/release/v1.28.0/bin/linux/amd64/kubectl"
   sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
   ```

4. **Helm** (v3.x)
   ```bash
   curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
   ```

5. **eksctl** (optional but recommended)
   ```bash
   curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
   sudo mv /tmp/eksctl /usr/local/bin
   ```

### AWS Account Setup

1. **Create AWS Account** with appropriate limits:
   - VPC limit: 5+ per region
   - EIP limit: 5+ per region
   - EKS cluster limit: 2+ per region
   - RDS instance limit: 40+ per region

2. **Configure AWS Credentials**:
   ```bash
   aws configure
   # Enter your AWS Access Key ID
   # Enter your AWS Secret Access Key
   # Default region: us-east-1
   # Default output format: json
   ```

3. **Create S3 Bucket for Terraform State**:
   ```bash
   aws s3 mb s3://mams-terraform-state --region us-east-1
   aws s3api put-bucket-versioning \
     --bucket mams-terraform-state \
     --versioning-configuration Status=Enabled
   ```

4. **Create DynamoDB Table for State Locking**:
   ```bash
   aws dynamodb create-table \
     --table-name mams-terraform-locks \
     --attribute-definitions AttributeName=LockID,AttributeType=S \
     --key-schema AttributeName=LockID,KeyType=HASH \
     --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
     --region us-east-1
   ```

## Deployment Steps

### 1. Clone Repository and Navigate to Infrastructure

```bash
git clone https://github.com/your-org/mams.git
cd mams/infrastructure/multi-region
```

### 2. Configure Environment Variables

Create a `.env` file:

```bash
cat > .env << EOF
# Environment Configuration
ENVIRONMENT=prod
PRIMARY_REGION=us-east-1
SECONDARY_REGIONS=eu-west-1,ap-southeast-1
DOMAIN_NAME=mams.example.com

# Database Configuration
DB_MASTER_USERNAME=mams_admin
DB_MASTER_PASSWORD=$(openssl rand -base64 32)

# MongoDB Atlas Configuration
MONGODB_ATLAS_PROJECT_ID=your-project-id
MONGODB_ATLAS_CLUSTER_NAME=mams-cluster

# Monitoring
ALERT_EMAIL=ops@example.com
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
EOF
```

### 3. Initialize Terraform

```bash
cd terraform
terraform init
```

### 4. Plan Infrastructure Changes

```bash
terraform plan \
  -var-file=environments/prod.tfvars \
  -out=tfplan
```

Review the plan carefully to ensure:
- Correct number of resources
- Appropriate instance sizes
- Correct regions configured

### 5. Apply Infrastructure

```bash
terraform apply tfplan
```

This will create:
- VPCs in all regions with proper CIDR ranges
- EKS clusters with node groups
- RDS clusters with read replicas
- OpenSearch domains
- Redis clusters
- S3 buckets with replication
- Load balancers and CDN

### 6. Deploy Kubernetes Resources

Use the deployment script:

```bash
cd ../scripts
./deploy-multi-region.sh \
  --environment prod \
  --primary us-east-1 \
  --secondary eu-west-1,ap-southeast-1 \
  --version v1.0.0
```

### 7. Verify Deployment

```bash
# Check primary region
kubectl config use-context mams-prod-us-east-1
kubectl get pods -n mams
kubectl get svc -n mams

# Check secondary regions
kubectl config use-context mams-prod-eu-west-1
kubectl get pods -n mams
```

### 8. Configure DNS

Update your domain's DNS records to point to the CloudFront distribution:

```bash
# Get CloudFront domain
CLOUDFRONT_DOMAIN=$(terraform output -raw cloudfront_domain_name)

# Create CNAME record
aws route53 change-resource-record-sets \
  --hosted-zone-id YOUR_ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "mams.example.com",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "'$CLOUDFRONT_DOMAIN'"}]
      }
    }]
  }'
```

## Configuration Management

### Region-Specific Configuration

Each region has specific configuration managed through Kubernetes ConfigMaps:

```yaml
# Primary Region Configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: region-config
  namespace: mams
data:
  REGION: "us-east-1"
  IS_PRIMARY: "true"
  DATABASE_MODE: "read-write"
  CACHE_MODE: "primary"
```

```yaml
# Secondary Region Configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: region-config
  namespace: mams
data:
  REGION: "eu-west-1"
  IS_PRIMARY: "false"
  DATABASE_MODE: "read-only"
  CACHE_MODE: "replica"
```

### Service Configuration

Services are configured to be region-aware:

```python
# Example: Asset Service Configuration
import os

REGION = os.getenv('REGION', 'us-east-1')
IS_PRIMARY = os.getenv('IS_PRIMARY', 'false').lower() == 'true'

if IS_PRIMARY:
    DATABASE_URL = os.getenv('PRIMARY_DATABASE_URL')
    CACHE_MODE = 'write-through'
else:
    DATABASE_URL = os.getenv('REPLICA_DATABASE_URL')
    CACHE_MODE = 'read-through'
```

## Data Replication Strategies

### 1. PostgreSQL Replication

- **Primary Region**: Read-write master
- **Secondary Regions**: Read-only replicas
- **Replication**: Asynchronous streaming replication
- **Lag Monitoring**: CloudWatch metrics for replication lag

### 2. MongoDB Replication

Using MongoDB Atlas Global Clusters:
- **Primary Region**: Primary replica set
- **Secondary Regions**: Secondary replica sets
- **Read Preference**: Secondary preferred for read operations
- **Write Concern**: Majority for critical operations

### 3. OpenSearch Cross-Cluster Replication

```bash
# Configure follower index
curl -X PUT "https://secondary-opensearch.region.es.amazonaws.com/_plugins/_replication/follower-index/_follow" \
  -H 'Content-Type: application/json' \
  -d '{
    "leader_alias": "primary-cluster",
    "leader_index": "mams-assets",
    "follower_index": "mams-assets-replica"
  }'
```

### 4. S3 Cross-Region Replication

Configured automatically via Terraform:
- **Replication Rule**: All objects replicated
- **Storage Class**: INTELLIGENT_TIERING in secondary regions
- **Metrics**: Replication metrics enabled

## Monitoring and Observability

### 1. CloudWatch Dashboards

Created automatically for each region:
- **Infrastructure Dashboard**: EKS, RDS, OpenSearch metrics
- **Application Dashboard**: API latency, error rates, throughput
- **Replication Dashboard**: Cross-region replication lag

### 2. Prometheus and Grafana

Deployed in each region:
```bash
# Access Grafana
kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80
# Default credentials: admin/prom-operator
```

### 3. Alerts Configuration

```yaml
# Example Alert Rule
groups:
  - name: multi-region-alerts
    rules:
      - alert: CrossRegionReplicationLag
        expr: mysql_slave_lag_seconds > 60
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High replication lag detected"
          description: "Replication lag is {{ $value }} seconds"
```

## Disaster Recovery Procedures

### 1. Regional Failover

In case of primary region failure:

```bash
# 1. Update Route53 health checks
aws route53 update-health-check \
  --health-check-id PRIMARY_HEALTH_CHECK_ID \
  --disabled

# 2. Promote secondary RDS to primary
aws rds promote-read-replica \
  --db-instance-identifier mams-prod-eu-west-1-replica

# 3. Update application configuration
kubectl set env deployment/api-gateway \
  -n mams \
  IS_PRIMARY=true \
  DATABASE_MODE=read-write
```

### 2. Data Recovery

```bash
# Restore from backup
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier mams-prod-restored \
  --db-snapshot-identifier manual-backup-2024-01-15

# Restore S3 objects
aws s3 sync \
  s3://mams-backup-bucket/ \
  s3://mams-media-bucket/ \
  --source-region us-west-2 \
  --region us-east-1
```

### 3. Service Recovery Priority

1. **Critical Services** (Priority: 1000)
   - API Gateway
   - Authentication Service
   - Asset Management Service

2. **High Priority** (Priority: 100)
   - Search Engine
   - Metadata Service
   - Storage Service

3. **Standard Priority** (Priority: 0)
   - Proxy Generation
   - AI/ML Service
   - Workflow Engine

## Cost Optimization

### 1. Instance Right-Sizing

Monitor and adjust instance sizes based on usage:

```bash
# Get recommendations
aws compute-optimizer get-ec2-instance-recommendations \
  --instance-arns arn:aws:ec2:region:account-id:instance/*
```

### 2. Spot Instances for Non-Critical Workloads

Configure node groups to use spot instances:

```hcl
# terraform/modules/region/eks/node_groups.tf
managed_node_groups = {
  spot = {
    instance_types = ["t3.large", "t3a.large"]
    capacity_type  = "SPOT"
    min_size       = 2
    max_size       = 10
    desired_size   = 4
  }
}
```

### 3. S3 Lifecycle Policies

Automatically configured for cost optimization:
- **0-30 days**: STANDARD
- **30-90 days**: STANDARD_IA
- **90+ days**: GLACIER
- **365+ days**: DEEP_ARCHIVE

## Security Best Practices

### 1. Network Security

- **VPC Peering**: Encrypted transit between regions
- **Security Groups**: Least privilege access
- **NACLs**: Additional layer of security
- **PrivateLink**: For AWS service access

### 2. Data Encryption

- **At Rest**: KMS encryption for all data stores
- **In Transit**: TLS 1.3 for all communications
- **Key Rotation**: Automatic key rotation enabled

### 3. Access Control

- **IRSA**: IAM Roles for Service Accounts
- **RBAC**: Kubernetes role-based access control
- **MFA**: Required for administrative access

### 4. Compliance

- **Audit Logs**: CloudTrail enabled in all regions
- **Config Rules**: AWS Config for compliance checking
- **GuardDuty**: Threat detection enabled

## Troubleshooting

### Common Issues

1. **EKS Node Group Scaling Issues**
   ```bash
   # Check autoscaler logs
   kubectl logs -n kube-system deployment/cluster-autoscaler
   
   # Check node status
   kubectl get nodes -o wide
   ```

2. **Cross-Region Replication Lag**
   ```bash
   # Check RDS replication status
   aws rds describe-db-instances \
     --db-instance-identifier mams-prod-replica \
     --query 'DBInstances[0].StatusInfos'
   ```

3. **Pod Scheduling Issues**
   ```bash
   # Check pod events
   kubectl describe pod POD_NAME -n mams
   
   # Check node resources
   kubectl top nodes
   ```

### Health Checks

Run periodic health checks:

```bash
# Run health check script
./scripts/health-check.sh --all-regions

# Check specific service
curl -s https://mams.example.com/health | jq .
```

## Maintenance Procedures

### 1. Rolling Updates

```bash
# Update deployment with zero downtime
kubectl set image deployment/api-gateway \
  api-gateway=mams/api-gateway:v1.1.0 \
  -n mams \
  --record
```

### 2. Database Maintenance

```bash
# Create manual backup before maintenance
aws rds create-db-snapshot \
  --db-instance-identifier mams-prod-primary \
  --db-snapshot-identifier manual-backup-$(date +%Y%m%d)

# Apply minor version upgrade
aws rds modify-db-instance \
  --db-instance-identifier mams-prod-primary \
  --auto-minor-version-upgrade \
  --apply-immediately
```

### 3. Certificate Renewal

Certificates are auto-renewed via cert-manager, but manual verification:

```bash
# Check certificate expiry
kubectl get certificate -n mams -o wide

# Force renewal if needed
kubectl delete certificate mams-tls -n mams
```

## Conclusion

This multi-region deployment provides:
- **High Availability**: 99.99% uptime SLA
- **Low Latency**: <100ms for users globally
- **Disaster Recovery**: RTO < 15 minutes, RPO < 5 minutes
- **Scalability**: Auto-scaling based on demand
- **Cost Efficiency**: Optimized resource utilization

For additional support, contact the DevOps team or refer to the internal wiki.