# Region Module - Deploys MAMS infrastructure in a single region

# VPC Configuration
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(var.tags, {
    Name = "${var.eks_cluster_name}-vpc"
  })
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(var.tags, {
    Name = "${var.eks_cluster_name}-igw"
  })
}

# Public Subnets
resource "aws_subnet" "public" {
  count                   = length(var.availability_zones)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 4, count.index)
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = merge(var.tags, {
    Name                                            = "${var.eks_cluster_name}-public-${var.availability_zones[count.index]}"
    "kubernetes.io/cluster/${var.eks_cluster_name}" = "shared"
    "kubernetes.io/role/elb"                        = "1"
  })
}

# Private Subnets
resource "aws_subnet" "private" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, count.index + length(var.availability_zones))
  availability_zone = var.availability_zones[count.index]

  tags = merge(var.tags, {
    Name                                            = "${var.eks_cluster_name}-private-${var.availability_zones[count.index]}"
    "kubernetes.io/cluster/${var.eks_cluster_name}" = "shared"
    "kubernetes.io/role/internal-elb"               = "1"
  })
}

# Database Subnets
resource "aws_subnet" "database" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, count.index + 2 * length(var.availability_zones))
  availability_zone = var.availability_zones[count.index]

  tags = merge(var.tags, {
    Name = "${var.eks_cluster_name}-db-${var.availability_zones[count.index]}"
  })
}

# NAT Gateways
resource "aws_eip" "nat" {
  count  = var.is_primary ? length(var.availability_zones) : 1
  domain = "vpc"

  tags = merge(var.tags, {
    Name = "${var.eks_cluster_name}-nat-eip-${count.index}"
  })
}

resource "aws_nat_gateway" "main" {
  count         = var.is_primary ? length(var.availability_zones) : 1
  subnet_id     = aws_subnet.public[count.index].id
  allocation_id = aws_eip.nat[count.index].id

  tags = merge(var.tags, {
    Name = "${var.eks_cluster_name}-nat-${count.index}"
  })
}

# Route Tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = merge(var.tags, {
    Name = "${var.eks_cluster_name}-public-rt"
  })
}

resource "aws_route_table" "private" {
  count  = var.is_primary ? length(var.availability_zones) : 1
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[count.index].id
  }

  tags = merge(var.tags, {
    Name = "${var.eks_cluster_name}-private-rt-${count.index}"
  })
}

# Route Table Associations
resource "aws_route_table_association" "public" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[var.is_primary ? count.index : 0].id
}

# EKS Cluster
module "eks" {
  source = "./eks"

  cluster_name       = var.eks_cluster_name
  cluster_version    = var.eks_version
  vpc_id             = aws_vpc.main.id
  subnet_ids         = concat(aws_subnet.private[*].id, aws_subnet.public[*].id)
  node_groups        = var.node_groups
  
  tags = var.tags
}

# RDS Aurora PostgreSQL
module "rds" {
  source = "./rds"

  cluster_identifier = "${var.eks_cluster_name}-db"
  is_primary        = var.is_primary
  source_db_identifier = var.rds_source_db_identifier
  
  vpc_id             = aws_vpc.main.id
  subnet_ids         = aws_subnet.database[*].id
  instance_class     = var.rds_instance_class
  allocated_storage  = var.rds_allocated_storage
  
  enable_read_replicas = var.enable_read_replicas
  read_replica_count   = var.read_replica_count
  
  tags = var.tags
}

# MongoDB Atlas (via provider)
module "mongodb" {
  source = "./mongodb"
  
  cluster_name       = "${var.eks_cluster_name}-mongodb"
  is_primary        = var.is_primary
  primary_cluster_id = var.mongodb_primary_cluster_id
  
  cluster_size      = var.mongodb_cluster_size
  disk_size_gb      = var.mongodb_disk_size_gb
  vpc_id            = aws_vpc.main.id
  
  tags = var.tags
}

# OpenSearch Domain
module "opensearch" {
  source = "./opensearch"
  
  domain_name        = "${var.eks_cluster_name}-search"
  is_primary        = var.is_primary
  primary_domain     = var.opensearch_primary_domain
  
  vpc_id             = aws_vpc.main.id
  subnet_ids         = aws_subnet.private[*].id
  instance_type      = var.opensearch_instance_type
  instance_count     = var.opensearch_instance_count
  
  tags = var.tags
}

# ElastiCache Redis
module "redis" {
  source = "./redis"
  
  cluster_id         = "${var.eks_cluster_name}-cache"
  is_primary        = var.is_primary
  primary_endpoint   = var.redis_primary_endpoint
  
  vpc_id             = aws_vpc.main.id
  subnet_ids         = aws_subnet.private[*].id
  node_type          = var.redis_node_type
  num_cache_nodes    = var.redis_num_cache_nodes
  
  tags = var.tags
}

# S3 Buckets
module "s3" {
  source = "./s3"
  
  bucket_prefix      = "${var.eks_cluster_name}-media"
  is_primary        = var.is_primary
  
  replication_regions = var.s3_replication_regions
  replication_source_bucket = var.s3_replication_source_bucket
  
  tags = var.tags
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "${var.eks_cluster_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = var.environment == "prod"
  enable_http2              = true
  enable_cross_zone_load_balancing = true

  tags = var.tags
}

# ALB Security Group
resource "aws_security_group" "alb" {
  name_prefix = "${var.eks_cluster_name}-alb-"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = var.tags
}

# Outputs
output "vpc_id" {
  value = aws_vpc.main.id
}

output "eks_cluster_name" {
  value = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "rds_cluster_identifier" {
  value = module.rds.cluster_identifier
}

output "rds_cluster_endpoint" {
  value = module.rds.cluster_endpoint
}

output "redis_primary_endpoint" {
  value = module.redis.primary_endpoint
}

output "opensearch_domain_endpoint" {
  value = module.opensearch.domain_endpoint
}

output "mongodb_cluster_id" {
  value = module.mongodb.cluster_id
}

output "s3_media_bucket_id" {
  value = module.s3.media_bucket_id
}

output "s3_media_bucket_regional_domain_name" {
  value = module.s3.media_bucket_regional_domain_name
}