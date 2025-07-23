#!/bin/bash

# MAMS API Gateway Deployment Script
# This script handles deployment of the API Gateway to various environments

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEPLOYMENT_ENV="${1:-development}"
KUBE_CONTEXT="${2:-}"
NAMESPACE="${3:-mams}"
IMAGE_TAG="${4:-latest}"
REGISTRY="${5:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Usage function
usage() {
    cat << EOF
Usage: $0 [ENVIRONMENT] [KUBE_CONTEXT] [NAMESPACE] [IMAGE_TAG] [REGISTRY]

Deploy MAMS API Gateway to Kubernetes

Arguments:
  ENVIRONMENT    Target environment (development|staging|production) [default: development]
  KUBE_CONTEXT   Kubernetes context to use [default: current context]
  NAMESPACE      Kubernetes namespace [default: mams]
  IMAGE_TAG      Docker image tag [default: latest]
  REGISTRY       Docker registry [default: none]

Examples:
  $0 development
  $0 staging my-staging-context mams-staging v1.2.3
  $0 production prod-cluster mams-prod v1.2.3 myregistry.com

Environment Variables:
  KUBECONFIG     Path to kubeconfig file
  DOCKER_REGISTRY Docker registry for images
  API_GATEWAY_SECRET_KEY  Secret key for API Gateway
  DATABASE_URL   Database connection string
  REDIS_URL      Redis connection string

EOF
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi
    
    # Check docker
    if ! command -v docker &> /dev/null; then
        log_error "docker is not installed"
        exit 1
    fi
    
    # Check if running in correct directory
    if [[ ! -f "$PROJECT_ROOT/Dockerfile" ]]; then
        log_error "Dockerfile not found. Are you running from the correct directory?"
        exit 1
    fi
    
    # Check environment
    if [[ ! "$DEPLOYMENT_ENV" =~ ^(development|staging|production)$ ]]; then
        log_error "Invalid environment: $DEPLOYMENT_ENV. Must be one of: development, staging, production"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Set kubectl context
set_kubectl_context() {
    if [[ -n "$KUBE_CONTEXT" ]]; then
        log_info "Setting kubectl context to $KUBE_CONTEXT"
        kubectl config use-context "$KUBE_CONTEXT"
    else
        CURRENT_CONTEXT=$(kubectl config current-context)
        log_info "Using current kubectl context: $CURRENT_CONTEXT"
    fi
}

# Build Docker image
build_image() {
    log_info "Building Docker image..."
    
    local image_name="mams-api-gateway"
    local full_image_name="$image_name:$IMAGE_TAG"
    
    if [[ -n "$REGISTRY" ]]; then
        full_image_name="$REGISTRY/$image_name:$IMAGE_TAG"
    fi
    
    # Build the image
    docker build -t "$full_image_name" "$PROJECT_ROOT"
    
    # Push to registry if specified
    if [[ -n "$REGISTRY" ]]; then
        log_info "Pushing image to registry..."
        docker push "$full_image_name"
    fi
    
    log_success "Docker image built: $full_image_name"
}

# Create namespace if it doesn't exist
create_namespace() {
    log_info "Creating namespace if it doesn't exist..."
    
    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_info "Namespace $NAMESPACE already exists"
    else
        kubectl apply -f "$PROJECT_ROOT/kubernetes/namespace.yaml"
        log_success "Namespace $NAMESPACE created"
    fi
}

# Deploy secrets
deploy_secrets() {
    log_info "Deploying secrets..."
    
    # Check if secrets exist
    if kubectl get secret api-gateway-secrets -n "$NAMESPACE" &> /dev/null; then
        log_warning "Secrets already exist. Skipping secret creation."
        log_warning "To update secrets, delete them first: kubectl delete secret api-gateway-secrets -n $NAMESPACE"
        return 0
    fi
    
    # Create secrets from environment variables or prompt
    local secret_key="${API_GATEWAY_SECRET_KEY:-}"
    local database_url="${DATABASE_URL:-}"
    local redis_url="${REDIS_URL:-}"
    
    if [[ -z "$secret_key" ]]; then
        log_warning "API_GATEWAY_SECRET_KEY not set. Generating random key..."
        secret_key=$(openssl rand -hex 32)
    fi
    
    if [[ -z "$database_url" ]]; then
        case "$DEPLOYMENT_ENV" in
            development)
                database_url="postgresql://mams_app:mams_dev_password@postgres-service:5432/mams_gateway"
                ;;
            staging)
                database_url="postgresql://mams_app:mams_staging_password@postgres-service:5432/mams_gateway"
                ;;
            production)
                log_error "DATABASE_URL must be set for production deployment"
                exit 1
                ;;
        esac
    fi
    
    if [[ -z "$redis_url" ]]; then
        case "$DEPLOYMENT_ENV" in
            development)
                redis_url="redis://redis-service:6379/0"
                ;;
            staging)
                redis_url="redis://:redis_staging_password@redis-service:6379/0"
                ;;
            production)
                log_error "REDIS_URL must be set for production deployment"
                exit 1
                ;;
        esac
    fi
    
    # Create secret
    kubectl create secret generic api-gateway-secrets \
        --from-literal=SECRET_KEY="$secret_key" \
        --from-literal=DATABASE_URL="$database_url" \
        --from-literal=REDIS_URL="$redis_url" \
        --from-literal=JAEGER_ENDPOINT="http://jaeger-service:14268" \
        --from-literal=CORS_ORIGINS="https://mams.example.com" \
        --from-literal=ALLOWED_HOSTS="api.mams.example.com,localhost" \
        --from-literal=IP_WHITELIST_ALLOWED_IPS="192.168.1.0/24,10.0.0.0/8" \
        --from-literal=IP_WHITELIST_ADMIN_IPS="192.168.1.100,10.0.0.1" \
        --from-literal=SERVICE_DISCOVERY_URL="http://consul-service:8500" \
        -n "$NAMESPACE"
    
    log_success "Secrets deployed"
}

# Deploy ConfigMaps
deploy_configmaps() {
    log_info "Deploying ConfigMaps..."
    
    # Update environment-specific values
    local temp_configmap=$(mktemp)
    cp "$PROJECT_ROOT/kubernetes/configmap.yaml" "$temp_configmap"
    
    # Replace environment-specific values
    case "$DEPLOYMENT_ENV" in
        development)
            sed -i.bak 's/ENVIRONMENT: "production"/ENVIRONMENT: "development"/' "$temp_configmap"
            sed -i.bak 's/LOG_LEVEL: "INFO"/LOG_LEVEL: "DEBUG"/' "$temp_configmap"
            sed -i.bak 's/OPENAPI_ENABLED: "true"/OPENAPI_ENABLED: "true"/' "$temp_configmap"
            ;;
        staging)
            sed -i.bak 's/ENVIRONMENT: "production"/ENVIRONMENT: "staging"/' "$temp_configmap"
            sed -i.bak 's/LOG_LEVEL: "INFO"/LOG_LEVEL: "INFO"/' "$temp_configmap"
            sed -i.bak 's/OPENAPI_ENABLED: "true"/OPENAPI_ENABLED: "true"/' "$temp_configmap"
            ;;
        production)
            sed -i.bak 's/LOG_LEVEL: "INFO"/LOG_LEVEL: "WARNING"/' "$temp_configmap"
            sed -i.bak 's/OPENAPI_ENABLED: "true"/OPENAPI_ENABLED: "false"/' "$temp_configmap"
            ;;
    esac
    
    kubectl apply -f "$temp_configmap" -n "$NAMESPACE"
    rm "$temp_configmap" "$temp_configmap.bak"
    
    log_success "ConfigMaps deployed"
}

# Deploy application
deploy_application() {
    log_info "Deploying application..."
    
    # Update image in deployment
    local temp_deployment=$(mktemp)
    cp "$PROJECT_ROOT/kubernetes/deployment.yaml" "$temp_deployment"
    
    local image_name="mams-api-gateway:$IMAGE_TAG"
    if [[ -n "$REGISTRY" ]]; then
        image_name="$REGISTRY/mams-api-gateway:$IMAGE_TAG"
    fi
    
    sed -i.bak "s|image: mams-api-gateway:latest|image: $image_name|" "$temp_deployment"
    
    # Apply deployment
    kubectl apply -f "$temp_deployment" -n "$NAMESPACE"
    rm "$temp_deployment" "$temp_deployment.bak"
    
    # Apply service
    kubectl apply -f "$PROJECT_ROOT/kubernetes/service.yaml" -n "$NAMESPACE"
    
    log_success "Application deployed"
}

# Deploy ingress
deploy_ingress() {
    log_info "Deploying ingress..."
    
    local temp_ingress=$(mktemp)
    cp "$PROJECT_ROOT/kubernetes/ingress.yaml" "$temp_ingress"
    
    # Update hostnames based on environment
    case "$DEPLOYMENT_ENV" in
        development)
            sed -i.bak 's/api.mams.example.com/api-dev.mams.example.com/' "$temp_ingress"
            sed -i.bak 's/admin.mams.example.com/admin-dev.mams.example.com/' "$temp_ingress"
            ;;
        staging)
            sed -i.bak 's/api.mams.example.com/api-staging.mams.example.com/' "$temp_ingress"
            sed -i.bak 's/admin.mams.example.com/admin-staging.mams.example.com/' "$temp_ingress"
            ;;
        production)
            # Keep production hostnames as-is
            ;;
    esac
    
    kubectl apply -f "$temp_ingress" -n "$NAMESPACE"
    rm "$temp_ingress" "$temp_ingress.bak"
    
    log_success "Ingress deployed"
}

# Deploy HPA
deploy_hpa() {
    log_info "Deploying HPA..."
    
    local temp_hpa=$(mktemp)
    cp "$PROJECT_ROOT/kubernetes/hpa.yaml" "$temp_hpa"
    
    # Adjust scaling parameters based on environment
    case "$DEPLOYMENT_ENV" in
        development)
            sed -i.bak 's/minReplicas: 2/minReplicas: 1/' "$temp_hpa"
            sed -i.bak 's/maxReplicas: 10/maxReplicas: 3/' "$temp_hpa"
            ;;
        staging)
            sed -i.bak 's/minReplicas: 2/minReplicas: 2/' "$temp_hpa"
            sed -i.bak 's/maxReplicas: 10/maxReplicas: 5/' "$temp_hpa"
            ;;
        production)
            # Keep production scaling as-is
            ;;
    esac
    
    kubectl apply -f "$temp_hpa" -n "$NAMESPACE"
    rm "$temp_hpa" "$temp_hpa.bak"
    
    log_success "HPA deployed"
}

# Wait for deployment to be ready
wait_for_deployment() {
    log_info "Waiting for deployment to be ready..."
    
    kubectl rollout status deployment/api-gateway -n "$NAMESPACE" --timeout=600s
    
    # Wait for pods to be ready
    kubectl wait --for=condition=ready pod -l app=api-gateway -n "$NAMESPACE" --timeout=300s
    
    log_success "Deployment is ready"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    # Check pods
    local pod_count=$(kubectl get pods -l app=api-gateway -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}' | wc -w)
    log_info "Running pods: $pod_count"
    
    # Check services
    local service_ip=$(kubectl get service api-gateway-service -n "$NAMESPACE" -o jsonpath='{.spec.clusterIP}')
    log_info "Service IP: $service_ip"
    
    # Check ingress
    local ingress_ip=$(kubectl get ingress api-gateway-ingress -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    if [[ -n "$ingress_ip" ]]; then
        log_info "Ingress IP: $ingress_ip"
    else
        log_warning "Ingress IP not yet assigned"
    fi
    
    # Health check
    log_info "Performing health check..."
    kubectl exec -n "$NAMESPACE" deployment/api-gateway -- curl -f http://localhost:8000/health
    
    log_success "Deployment verification completed"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up temporary files..."
    # Add cleanup logic here if needed
}

# Main deployment function
main() {
    log_info "Starting MAMS API Gateway deployment..."
    log_info "Environment: $DEPLOYMENT_ENV"
    log_info "Namespace: $NAMESPACE"
    log_info "Image Tag: $IMAGE_TAG"
    
    # Set trap for cleanup
    trap cleanup EXIT
    
    # Run deployment steps
    check_prerequisites
    set_kubectl_context
    build_image
    create_namespace
    deploy_secrets
    deploy_configmaps
    deploy_application
    deploy_ingress
    deploy_hpa
    wait_for_deployment
    verify_deployment
    
    log_success "MAMS API Gateway deployment completed successfully!"
    
    # Print access information
    case "$DEPLOYMENT_ENV" in
        development)
            log_info "Access the API at: http://api-dev.mams.example.com"
            log_info "Admin interface: http://admin-dev.mams.example.com"
            ;;
        staging)
            log_info "Access the API at: https://api-staging.mams.example.com"
            log_info "Admin interface: https://admin-staging.mams.example.com"
            ;;
        production)
            log_info "Access the API at: https://api.mams.example.com"
            log_info "Admin interface: https://admin.mams.example.com"
            ;;
    esac
    
    log_info "API Documentation: /docs"
    log_info "Health Check: /health"
    log_info "Metrics: /metrics"
}

# Handle command line arguments
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    usage
    exit 0
fi

# Run main function
main "$@"