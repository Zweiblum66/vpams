"""
Metrics collection for advanced AI service
"""

from prometheus_client import Counter, Histogram, Gauge, Summary


# Prediction metrics
predictions_made = Counter(
    'ai_predictions_made_total',
    'Total number of predictions made',
    ['type', 'model']
)

prediction_accuracy = Gauge(
    'ai_prediction_accuracy',
    'Prediction accuracy score',
    ['type', 'model']
)

prediction_latency = Histogram(
    'ai_prediction_latency_seconds',
    'Prediction request latency',
    ['type', 'model'],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60]
)

# Model metrics
model_training_time = Histogram(
    'ai_model_training_seconds',
    'Model training time',
    ['model_type'],
    buckets=[60, 300, 600, 1800, 3600, 7200, 14400]
)

model_updates = Counter(
    'ai_model_updates_total',
    'Total number of model updates',
    ['model_type']
)

model_performance = Gauge(
    'ai_model_performance',
    'Model performance metrics',
    ['model_type', 'metric']
)

# Recommendation metrics
recommendations_generated = Counter(
    'ai_recommendations_generated_total',
    'Total recommendations generated',
    ['type']
)

recommendation_click_rate = Gauge(
    'ai_recommendation_ctr',
    'Recommendation click-through rate',
    ['type']
)

# Storage optimization metrics
storage_optimizations = Counter(
    'ai_storage_optimizations_total',
    'Total storage optimizations suggested'
)

storage_savings_gb = Gauge(
    'ai_storage_savings_gb',
    'Estimated storage savings in GB'
)

cost_savings_usd = Gauge(
    'ai_cost_savings_usd',
    'Estimated cost savings in USD',
    ['type']
)

# Content intelligence metrics
content_analyzed = Counter(
    'ai_content_analyzed_total',
    'Total content items analyzed',
    ['analysis_type']
)

tags_generated = Counter(
    'ai_tags_generated_total',
    'Total tags generated',
    ['source']
)

clusters_created = Gauge(
    'ai_content_clusters',
    'Number of content clusters'
)

# Maintenance prediction metrics
maintenance_predictions = Counter(
    'ai_maintenance_predictions_total',
    'Total maintenance predictions made',
    ['component_type', 'risk_level']
)

maintenance_alerts = Counter(
    'ai_maintenance_alerts_total',
    'Total maintenance alerts generated',
    ['severity']
)

# Search metrics
ai_searches = Counter(
    'ai_searches_total',
    'Total AI-powered searches',
    ['search_type']
)

search_relevance_score = Gauge(
    'ai_search_relevance',
    'Average search relevance score'
)

# Resource utilization
gpu_utilization = Gauge(
    'ai_gpu_utilization_percent',
    'GPU utilization percentage',
    ['device_id']
)

model_memory_usage = Gauge(
    'ai_model_memory_bytes',
    'Model memory usage in bytes',
    ['model_type']
)

# Summary metrics
request_duration = Summary(
    'ai_request_duration_seconds',
    'Request duration in seconds',
    ['endpoint', 'method']
)


# Helper class to organize metrics
class AIMetrics:
    """Container for all AI service metrics"""
    
    def __init__(self):
        # Prediction metrics
        self.predictions_made = predictions_made
        self.prediction_accuracy = prediction_accuracy
        self.prediction_latency = prediction_latency
        
        # Model metrics
        self.model_training_time = model_training_time
        self.model_updates = model_updates
        self.model_performance = model_performance
        
        # Recommendation metrics
        self.recommendations_generated = recommendations_generated
        self.recommendation_click_rate = recommendation_click_rate
        
        # Storage optimization metrics
        self.storage_optimizations = storage_optimizations
        self.storage_savings_gb = storage_savings_gb
        self.cost_savings_usd = cost_savings_usd
        
        # Content intelligence metrics
        self.content_analyzed = content_analyzed
        self.tags_generated = tags_generated
        self.clusters_created = clusters_created
        
        # Maintenance prediction metrics
        self.maintenance_predictions = maintenance_predictions
        self.maintenance_alerts = maintenance_alerts
        
        # Search metrics
        self.ai_searches = ai_searches
        self.search_relevance_score = search_relevance_score
        
        # Resource utilization
        self.gpu_utilization = gpu_utilization
        self.model_memory_usage = model_memory_usage
        
        # Summary metrics
        self.request_duration = request_duration


# Global metrics instance
ai_metrics = AIMetrics()