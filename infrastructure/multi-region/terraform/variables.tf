# Multi-Region Infrastructure Variables

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "mams"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "domain_name" {
  description = "Primary domain name for the application"
  type        = string
}

# Region Configuration
variable "primary_region" {
  description = "Primary AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "secondary_regions" {
  description = "List of secondary AWS regions for deployment"
  type        = list(string)
  default     = ["eu-west-1", "ap-southeast-1"]
}

variable "dr_region" {
  description = "Disaster recovery region"
  type        = string
  default     = "us-west-2"
}

# VPC Configuration
variable "primary_vpc_cidr" {
  description = "CIDR block for primary region VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "secondary_vpc_cidrs" {
  description = "CIDR blocks for secondary region VPCs"
  type        = map(string)
  default = {
    "eu-west-1"      = "10.1.0.0/16"
    "ap-southeast-1" = "10.2.0.0/16"
  }
}

variable "primary_availability_zones" {
  description = "Availability zones for primary region"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "secondary_availability_zones" {
  description = "Availability zones for secondary regions"
  type        = map(list(string))
  default = {
    "eu-west-1"      = ["eu-west-1a", "eu-west-1b", "eu-west-1c"]
    "ap-southeast-1" = ["ap-southeast-1a", "ap-southeast-1b", "ap-southeast-1c"]
  }
}

# EKS Configuration
variable "eks_version" {
  description = "Kubernetes version for EKS clusters"
  type        = string
  default     = "1.28"
}

variable "primary_node_groups" {
  description = "Node group configuration for primary region"
  type = map(object({
    instance_types = list(string)
    min_size       = number
    max_size       = number
    desired_size   = number
    disk_size      = number
    labels         = map(string)
    taints = list(object({
      key    = string
      value  = string
      effect = string
    }))
  }))
  default = {
    general = {
      instance_types = ["t3.large"]
      min_size       = 3
      max_size       = 10
      desired_size   = 5
      disk_size      = 100
      labels = {
        role = "general"
      }
      taints = []
    }
    compute = {
      instance_types = ["c5.2xlarge"]
      min_size       = 2
      max_size       = 20
      desired_size   = 5
      disk_size      = 200
      labels = {
        role = "compute"
      }
      taints = [{
        key    = "compute"
        value  = "true"
        effect = "NoSchedule"
      }]
    }
    gpu = {
      instance_types = ["g4dn.xlarge"]
      min_size       = 0
      max_size       = 10
      desired_size   = 2
      disk_size      = 200
      labels = {
        role = "gpu"
      }
      taints = [{
        key    = "nvidia.com/gpu"
        value  = "true"
        effect = "NoSchedule"
      }]
    }
  }
}

variable "secondary_node_groups" {
  description = "Node group configuration for secondary regions"
  type = map(object({
    instance_types = list(string)
    min_size       = number
    max_size       = number
    desired_size   = number
    disk_size      = number
    labels         = map(string)
    taints = list(object({
      key    = string
      value  = string
      effect = string
    }))
  }))
  default = {
    general = {
      instance_types = ["t3.large"]
      min_size       = 2
      max_size       = 8
      desired_size   = 3
      disk_size      = 100
      labels = {
        role = "general"
      }
      taints = []
    }
    compute = {
      instance_types = ["c5.xlarge"]
      min_size       = 1
      max_size       = 10
      desired_size   = 2
      disk_size      = 200
      labels = {
        role = "compute"
      }
      taints = [{
        key    = "compute"
        value  = "true"
        effect = "NoSchedule"
      }]
    }
  }
}

# RDS Configuration
variable "primary_rds_instance_class" {
  description = "RDS instance class for primary region"
  type        = string
  default     = "db.r6g.2xlarge"
}

variable "primary_rds_allocated_storage" {
  description = "Allocated storage for primary RDS in GB"
  type        = number
  default     = 1000
}

variable "primary_read_replica_count" {
  description = "Number of read replicas in primary region"
  type        = number
  default     = 2
}

variable "secondary_read_replica_count" {
  description = "Number of read replicas in secondary regions"
  type        = number
  default     = 1
}

# MongoDB Configuration
variable "primary_mongodb_cluster_size" {
  description = "MongoDB Atlas cluster size for primary region"
  type        = string
  default     = "M40"
}

variable "primary_mongodb_disk_size_gb" {
  description = "MongoDB disk size in GB for primary region"
  type        = number
  default     = 500
}

variable "secondary_mongodb_cluster_size" {
  description = "MongoDB Atlas cluster size for secondary regions"
  type        = string
  default     = "M30"
}

# OpenSearch Configuration
variable "primary_opensearch_instance_type" {
  description = "OpenSearch instance type for primary region"
  type        = string
  default     = "r6g.2xlarge.search"
}

variable "primary_opensearch_instance_count" {
  description = "Number of OpenSearch instances in primary region"
  type        = number
  default     = 3
}

variable "secondary_opensearch_instance_type" {
  description = "OpenSearch instance type for secondary regions"
  type        = string
  default     = "r6g.xlarge.search"
}

variable "secondary_opensearch_instance_count" {
  description = "Number of OpenSearch instances in secondary regions"
  type        = number
  default     = 2
}

# Redis Configuration
variable "primary_redis_node_type" {
  description = "Redis node type for primary region"
  type        = string
  default     = "cache.r6g.xlarge"
}

variable "primary_redis_num_cache_nodes" {
  description = "Number of Redis cache nodes in primary region"
  type        = number
  default     = 3
}

variable "secondary_redis_node_type" {
  description = "Redis node type for secondary regions"
  type        = string
  default     = "cache.r6g.large"
}

variable "secondary_redis_num_cache_nodes" {
  description = "Number of Redis cache nodes in secondary regions"
  type        = number
  default     = 2
}

# Traffic Routing
variable "traffic_routing_policy" {
  description = "Traffic routing policy (weighted, latency, geolocation)"
  type        = string
  default     = "latency"
}

variable "primary_traffic_weight" {
  description = "Traffic weight for primary region (if using weighted routing)"
  type        = number
  default     = 60
}

# CloudFront Configuration
variable "cloudfront_cache_behaviors" {
  description = "CloudFront cache behaviors configuration"
  type = list(object({
    path_pattern     = string
    target_origin_id = string
    allowed_methods  = list(string)
    cached_methods   = list(string)
    ttl_default      = number
    ttl_max          = number
    compress         = bool
  }))
  default = [
    {
      path_pattern     = "/api/*"
      target_origin_id = "primary"
      allowed_methods  = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
      cached_methods   = ["GET", "HEAD"]
      ttl_default      = 0
      ttl_max          = 0
      compress         = true
    },
    {
      path_pattern     = "/static/*"
      target_origin_id = "s3"
      allowed_methods  = ["GET", "HEAD", "OPTIONS"]
      cached_methods   = ["GET", "HEAD", "OPTIONS"]
      ttl_default      = 86400
      ttl_max          = 31536000
      compress         = true
    },
    {
      path_pattern     = "/media/*"
      target_origin_id = "s3"
      allowed_methods  = ["GET", "HEAD", "OPTIONS"]
      cached_methods   = ["GET", "HEAD"]
      ttl_default      = 3600
      ttl_max          = 86400
      compress         = false
    }
  ]
}

# WAF Configuration
variable "waf_rate_limit_threshold" {
  description = "Rate limit threshold for WAF"
  type        = number
  default     = 2000
}

variable "waf_ip_whitelist" {
  description = "IP addresses to whitelist in WAF"
  type        = list(string)
  default     = []
}

variable "waf_geo_whitelist" {
  description = "Countries to whitelist in WAF (2-letter country codes)"
  type        = list(string)
  default     = ["US", "CA", "GB", "DE", "FR", "JP", "AU", "SG"]
}

# Monitoring Configuration
variable "alert_email_endpoints" {
  description = "Email addresses for alerts"
  type        = list(string)
  default     = []
}

variable "alert_slack_webhook" {
  description = "Slack webhook URL for alerts"
  type        = string
  default     = ""
}

# Backup Configuration
variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 30
}

variable "backup_schedule" {
  description = "Backup schedule in cron format"
  type        = string
  default     = "0 3 * * *"
}

# Tags
variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "MAMS"
    ManagedBy   = "Terraform"
    Environment = "production"
  }
}