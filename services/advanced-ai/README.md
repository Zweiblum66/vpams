# Advanced AI Service

The Advanced AI Service provides predictive analytics, intelligent recommendations, and machine learning capabilities for the MAMS platform.

## Features

### 1. Usage Prediction
- **Multi-model ensemble predictions** using Prophet, ARIMA, LSTM, and XGBoost
- **Time series forecasting** for asset access patterns
- **Seasonality detection** (daily, weekly, monthly patterns)
- **Trend analysis** with growth rate calculation
- **Confidence scoring** based on model agreement

### 2. Storage Optimization
- **Intelligent tier recommendations** based on access patterns
- **Cost optimization** calculations
- **Access time impact** analysis
- **Batch optimization planning** with prioritization
- **Automated tier transition** recommendations

### 3. Content Recommendations
- **Hybrid recommendation engine** combining:
  - Collaborative filtering
  - Content-based filtering
  - Trending analysis
  - Personalized recommendations
- **Multiple recommendation types**:
  - Similar content
  - Trending content
  - Personalized suggestions
  - Popular content
- **Real-time recommendation updates**
- **Feedback integration** for model improvement

### 4. Predictive Maintenance
- **Component health monitoring**
- **Failure prediction** using ML models
- **Anomaly detection** with Isolation Forest
- **Risk assessment** and alerting
- **Maintenance scheduling** recommendations
- **Root cause analysis** for issues

## Architecture

```
advanced-ai/
├── src/
│   ├── api/
│   │   └── routes.py           # API endpoints
│   ├── core/
│   │   ├── config.py          # Service configuration
│   │   └── deps.py            # Dependencies
│   ├── db/
│   │   └── models.py          # Database models
│   ├── models/
│   │   └── schemas.py         # Pydantic schemas
│   ├── services/
│   │   ├── usage_predictor.py     # Usage prediction
│   │   ├── storage_optimizer.py   # Storage optimization
│   │   ├── recommendation_engine.py # Recommendations
│   │   └── maintenance_predictor.py # Maintenance
│   ├── utils/
│   │   ├── feature_engineering.py # ML features
│   │   └── metrics.py            # Prometheus metrics
│   └── main.py                   # FastAPI app
├── tests/                        # Test files
├── notebooks/                    # Jupyter notebooks
├── models/                       # Trained models
└── docker-compose.yml           # Docker config
```

## API Endpoints

### Usage Prediction
- `POST /api/v1/ai/predictions/usage` - Predict future usage
- `GET /api/v1/ai/predictions/usage/trends/{asset_id}` - Get usage trends
- `GET /api/v1/ai/predictions/usage/history` - Get prediction history

### Storage Optimization
- `POST /api/v1/ai/optimization/storage` - Generate optimization plan
- `GET /api/v1/ai/optimization/storage/recommendations` - Get recommendations

### Content Recommendations
- `POST /api/v1/ai/recommendations/content` - Get recommendations
- `POST /api/v1/ai/recommendations/feedback` - Record feedback

### Predictive Maintenance
- `GET /api/v1/ai/maintenance/predictions` - Get maintenance predictions
- `GET /api/v1/ai/maintenance/alerts` - Get maintenance alerts

### Model Management
- `GET /api/v1/ai/models` - List ML models
- `POST /api/v1/ai/models/train` - Trigger model training
- `GET /api/v1/ai/models/jobs/{job_id}` - Get training job status

## Machine Learning Models

### 1. Prophet (Time Series)
- Handles seasonality and holidays
- Robust to missing data
- Provides uncertainty intervals

### 2. ARIMA (Statistical)
- Classic time series model
- Good for stationary data
- Captures autocorrelation

### 3. LSTM (Deep Learning)
- Captures long-term dependencies
- Handles complex patterns
- Requires more data

### 4. XGBoost (Gradient Boosting)
- Feature-based predictions
- Fast training and inference
- Good for tabular data

### 5. Random Forest (Classification)
- Failure prediction
- Feature importance analysis
- Robust to outliers

### 6. Isolation Forest (Anomaly Detection)
- Unsupervised anomaly detection
- Efficient for high-dimensional data
- Real-time detection

## Configuration

### Environment Variables

```bash
# Service Configuration
SERVICE_NAME=advanced-ai
SERVICE_PORT=8014
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/mams_ai
MONGODB_URL=mongodb://host:27017/mams_ai
REDIS_URL=redis://host:6379/13

# AI Configuration
USAGE_PREDICTION_WINDOW_DAYS=90
USAGE_PREDICTION_HORIZON_DAYS=30
USAGE_PREDICTION_MODELS=["prophet","arima","lstm","xgboost"]
USAGE_PREDICTION_MIN_HISTORY_DAYS=30

# Storage Optimization
STORAGE_OPTIMIZATION_ENABLED=true
STORAGE_TIER_THRESHOLDS={...}
COST_PER_GB_STORAGE={...}

# Recommendations
RECOMMENDATION_CACHE_TTL=3600
RECOMMENDATION_ENGINE_VERSION=1.0.0
RECOMMENDATION_MIN_CONFIDENCE=0.5

# Maintenance
MAINTENANCE_PREDICTION_ENABLED=true
MAINTENANCE_CHECK_INTERVAL_HOURS=6
MAINTENANCE_ALERT_RETENTION_DAYS=30
```

## Development

### Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest

# Start service
docker-compose up
```

### Training Models
```bash
# Run training container
docker-compose --profile training up ai-trainer

# Or train specific model
python -m src.train --model prophet --asset-id asset123
```

### Jupyter Notebooks
```bash
# Start Jupyter for experimentation
docker-compose --profile dev up jupyter
```

## Usage Examples

### Predict Asset Usage
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8014/api/v1/ai/predictions/usage",
        json={
            "asset_ids": ["asset123", "asset456"],
            "horizon_days": 30,
            "models_to_use": ["prophet", "xgboost"]
        },
        headers={"Authorization": "Bearer <token>"}
    )
    predictions = response.json()
```

### Get Storage Recommendations
```python
response = await client.post(
    "http://localhost:8014/api/v1/ai/optimization/storage",
    params={"min_savings_percent": 20},
    headers={"Authorization": "Bearer <token>"}
)
optimization_plan = response.json()
```

### Get Content Recommendations
```python
response = await client.post(
    "http://localhost:8014/api/v1/ai/recommendations/content",
    json={
        "recommendation_type": "similar",
        "reference_asset_id": "asset123",
        "count": 10
    },
    headers={"Authorization": "Bearer <token>"}
)
recommendations = response.json()
```

## Monitoring

### Metrics
- `ai_predictions_total` - Total predictions made
- `ai_prediction_latency_seconds` - Prediction latency
- `ai_model_accuracy` - Model accuracy metrics
- `ai_recommendations_generated` - Recommendations count
- `ai_storage_optimizations` - Storage optimizations
- `ai_maintenance_predictions` - Maintenance predictions

### Health Check
```bash
curl http://localhost:8014/health
```

## Testing

```bash
# Run all tests
pytest

# Run specific test
pytest tests/test_usage_predictor.py

# Run with coverage
pytest --cov=src

# Run integration tests
pytest tests/integration/
```

## Performance

- Usage predictions: < 500ms for 100 assets
- Storage optimization: < 2s for 10,000 assets
- Recommendations: < 200ms (cached)
- Model training: Varies by model and data size

## Security

- API key authentication required
- User-based access control
- Input validation on all endpoints
- Secure model storage
- Audit logging for predictions

## Troubleshooting

### Model Training Issues
- Check training data availability
- Verify model storage permissions
- Review training logs in container

### Prediction Errors
- Ensure sufficient historical data
- Check for data quality issues
- Verify model loading

### Performance Issues
- Monitor Redis cache hit rate
- Check database query performance
- Review model inference times