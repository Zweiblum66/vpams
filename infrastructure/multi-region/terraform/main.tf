# Multi-Region MAMS Infrastructure
# Main Terraform configuration for deploying MAMS across multiple regions

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
  }
  
  backend "s3" {
    bucket         = "mams-terraform-state"
    key            = "multi-region/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "mams-terraform-locks"
    encrypt        = true
  }
}

# Primary region configuration
module "primary_region" {
  source = "./modules/region"
  
  region                = var.primary_region
  environment           = var.environment
  vpc_cidr              = var.primary_vpc_cidr
  availability_zones    = var.primary_availability_zones
  is_primary            = true
  
  # EKS configuration
  eks_cluster_name      = "${var.project_name}-${var.environment}-${var.primary_region}"
  eks_version           = var.eks_version
  node_groups           = var.primary_node_groups
  
  # Database configuration
  enable_rds            = true
  rds_instance_class    = var.primary_rds_instance_class
  rds_allocated_storage = var.primary_rds_allocated_storage
  enable_read_replicas  = true
  read_replica_count    = var.primary_read_replica_count
  
  # MongoDB Atlas configuration
  mongodb_cluster_size  = var.primary_mongodb_cluster_size
  mongodb_disk_size_gb  = var.primary_mongodb_disk_size_gb
  
  # OpenSearch configuration
  opensearch_instance_type  = var.primary_opensearch_instance_type
  opensearch_instance_count = var.primary_opensearch_instance_count
  
  # Redis configuration
  redis_node_type       = var.primary_redis_node_type
  redis_num_cache_nodes = var.primary_redis_num_cache_nodes
  
  # S3 configuration
  s3_replication_regions = var.secondary_regions
  
  tags = merge(var.common_tags, {
    Region = var.primary_region
    IsPrimary = "true"
  })
}

# Secondary regions
module "secondary_regions" {
  for_each = toset(var.secondary_regions)
  source   = "./modules/region"
  
  region                = each.value
  environment           = var.environment
  vpc_cidr              = var.secondary_vpc_cidrs[each.value]
  availability_zones    = var.secondary_availability_zones[each.value]
  is_primary            = false
  primary_region        = var.primary_region
  
  # EKS configuration
  eks_cluster_name      = "${var.project_name}-${var.environment}-${each.value}"
  eks_version           = var.eks_version
  node_groups           = var.secondary_node_groups
  
  # Database configuration (read replicas only)
  enable_rds            = true
  rds_source_db_identifier = module.primary_region.rds_cluster_identifier
  enable_read_replicas  = true
  read_replica_count    = var.secondary_read_replica_count
  
  # MongoDB Atlas configuration (replica set)
  mongodb_primary_cluster_id = module.primary_region.mongodb_cluster_id
  mongodb_cluster_size  = var.secondary_mongodb_cluster_size
  
  # OpenSearch configuration (cross-cluster replication)
  opensearch_primary_domain = module.primary_region.opensearch_domain_endpoint
  opensearch_instance_type  = var.secondary_opensearch_instance_type
  opensearch_instance_count = var.secondary_opensearch_instance_count
  
  # Redis configuration (replica)
  redis_primary_endpoint = module.primary_region.redis_primary_endpoint
  redis_node_type       = var.secondary_redis_node_type
  redis_num_cache_nodes = var.secondary_redis_num_cache_nodes
  
  # S3 configuration (replication destination)
  s3_replication_source_bucket = module.primary_region.s3_media_bucket_id
  
  tags = merge(var.common_tags, {
    Region = each.value
    IsPrimary = "false"
  })
}

# Global Load Balancer
module "global_load_balancer" {
  source = "./modules/global-load-balancer"
  
  environment          = var.environment
  primary_alb_dns_name = module.primary_region.alb_dns_name
  secondary_alb_dns_names = {
    for region, module in module.secondary_regions : region => module.alb_dns_name
  }
  
  # Route53 configuration
  domain_name          = var.domain_name
  health_check_path    = "/health"
  health_check_interval = 30
  
  # Traffic routing policy
  routing_policy       = var.traffic_routing_policy
  primary_weight       = var.primary_traffic_weight
  
  tags = var.common_tags
}

# Cross-region VPC peering
module "vpc_peering" {
  source = "./modules/vpc-peering"
  
  primary_vpc_id = module.primary_region.vpc_id
  primary_region = var.primary_region
  
  secondary_vpcs = {
    for region, module in module.secondary_regions : region => {
      vpc_id = module.vpc_id
      cidr   = var.secondary_vpc_cidrs[region]
    }
  }
  
  tags = var.common_tags
}

# Global CloudFront CDN
module "cloudfront_cdn" {
  source = "./modules/cloudfront"
  
  environment = var.environment
  domain_name = var.domain_name
  
  # Origin configuration
  primary_origin = {
    domain_name = module.primary_region.alb_dns_name
    origin_id   = "primary-${var.primary_region}"
  }
  
  secondary_origins = [
    for region, module in module.secondary_regions : {
      domain_name = module.alb_dns_name
      origin_id   = "secondary-${region}"
    }
  ]
  
  # S3 origins for static content
  s3_origins = concat(
    [{
      domain_name = module.primary_region.s3_media_bucket_regional_domain_name
      origin_id   = "s3-${var.primary_region}"
    }],
    [for region, module in module.secondary_regions : {
      domain_name = module.s3_media_bucket_regional_domain_name
      origin_id   = "s3-${region}"
    }]
  )
  
  # Cache behaviors
  cache_behaviors = var.cloudfront_cache_behaviors
  
  # WAF configuration
  web_acl_id = module.waf.web_acl_id
  
  tags = var.common_tags
}

# WAF for CloudFront
module "waf" {
  source = "./modules/waf"
  
  environment = var.environment
  scope       = "CLOUDFRONT"
  
  # Rules configuration
  rate_limit_threshold = var.waf_rate_limit_threshold
  ip_whitelist        = var.waf_ip_whitelist
  geo_whitelist       = var.waf_geo_whitelist
  
  tags = var.common_tags
}

# Monitoring and Alerting
module "monitoring" {
  source = "./modules/monitoring"
  
  environment = var.environment
  
  # Regions to monitor
  monitored_regions = concat([var.primary_region], var.secondary_regions)
  
  # EKS clusters to monitor
  eks_clusters = merge(
    {
      (var.primary_region) = module.primary_region.eks_cluster_name
    },
    {
      for region, module in module.secondary_regions : region => module.eks_cluster_name
    }
  )
  
  # RDS clusters to monitor
  rds_clusters = merge(
    {
      (var.primary_region) = module.primary_region.rds_cluster_identifier
    },
    {
      for region, module in module.secondary_regions : region => module.rds_cluster_identifier
    }
  )
  
  # Alert configuration
  alert_email_endpoints = var.alert_email_endpoints
  alert_slack_webhook   = var.alert_slack_webhook
  
  tags = var.common_tags
}

# Disaster Recovery
module "disaster_recovery" {
  source = "./modules/disaster-recovery"
  
  environment     = var.environment
  primary_region  = var.primary_region
  dr_region       = var.dr_region
  
  # Backup configuration
  backup_retention_days = var.backup_retention_days
  backup_schedule       = var.backup_schedule
  
  # RDS snapshots
  rds_cluster_identifier = module.primary_region.rds_cluster_identifier
  
  # S3 backup
  s3_buckets_to_backup = [
    module.primary_region.s3_media_bucket_id
  ]
  
  tags = var.common_tags
}

# Outputs
output "primary_region_endpoints" {
  value = {
    eks_endpoint     = module.primary_region.eks_cluster_endpoint
    alb_endpoint     = module.primary_region.alb_dns_name
    rds_endpoint     = module.primary_region.rds_cluster_endpoint
    redis_endpoint   = module.primary_region.redis_primary_endpoint
    opensearch_endpoint = module.primary_region.opensearch_domain_endpoint
  }
}

output "secondary_region_endpoints" {
  value = {
    for region, module in module.secondary_regions : region => {
      eks_endpoint   = module.eks_cluster_endpoint
      alb_endpoint   = module.alb_dns_name
      rds_endpoint   = module.rds_cluster_endpoint
      redis_endpoint = module.redis_primary_endpoint
    }
  }
}

output "global_endpoints" {
  value = {
    cloudfront_domain = module.cloudfront_cdn.distribution_domain_name
    route53_domain    = module.global_load_balancer.route53_record_name
  }
}

output "vpc_peering_connections" {
  value = module.vpc_peering.peering_connection_ids
}