"""
Feature Engineering Utilities

Creates features for machine learning models.
"""

import pandas as pd
import numpy as np
from datetime import datetime, date
from typing import List, Dict, Any, Optional
import holidays


class FeatureEngineer:
    """Creates features for ML models"""
    
    def __init__(self, country_code: str = "US"):
        self.holidays = holidays.country_holidays(country_code)
        self.feature_names = []
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create features from usage data"""
        df = df.copy()
        
        # Time-based features
        df = self._add_time_features(df)
        
        # Lag features
        df = self._add_lag_features(df)
        
        # Rolling statistics
        df = self._add_rolling_features(df)
        
        # Holiday features
        df = self._add_holiday_features(df)
        
        # Trend features
        df = self._add_trend_features(df)
        
        # Store feature names
        self.feature_names = [col for col in df.columns if col not in ['date', 'access_count']]
        
        return df
    
    def create_future_features(self, target_date: date, baseline_value: float) -> np.ndarray:
        """Create features for a future date"""
        features = []
        
        # Time features
        features.extend(self._get_time_features(target_date))
        
        # Holiday feature
        features.append(1 if target_date in self.holidays else 0)
        
        # Use baseline for lag features (simplified)
        features.extend([baseline_value] * 7)  # 7 lag features
        
        # Use baseline for rolling features
        features.extend([baseline_value] * 6)  # 6 rolling features
        
        # Trend features (neutral)
        features.extend([0, baseline_value])
        
        return np.array(features)
    
    def _add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add time-based features"""
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['day'] = df['date'].dt.day
        df['day_of_week'] = df['date'].dt.dayofweek
        df['day_of_year'] = df['date'].dt.dayofyear
        df['week_of_year'] = df['date'].dt.isocalendar().week
        df['quarter'] = df['date'].dt.quarter
        
        # Cyclic features
        df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
        df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        
        # Weekend indicator
        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
        
        # Month start/end
        df['is_month_start'] = (df['day'] <= 5).astype(int)
        df['is_month_end'] = (df['day'] >= 25).astype(int)
        
        return df
    
    def _add_lag_features(self, df: pd.DataFrame, lags: List[int] = [1, 2, 3, 7, 14, 21, 28]) -> pd.DataFrame:
        """Add lag features"""
        for lag in lags:
            df[f'lag_{lag}'] = df['access_count'].shift(lag)
        
        # Fill NaN values with forward fill then backward fill
        lag_columns = [f'lag_{lag}' for lag in lags]
        df[lag_columns] = df[lag_columns].fillna(method='ffill').fillna(method='bfill')
        
        return df
    
    def _add_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add rolling window statistics"""
        windows = [7, 14, 30]
        
        for window in windows:
            df[f'rolling_mean_{window}'] = df['access_count'].rolling(window, min_periods=1).mean()
            df[f'rolling_std_{window}'] = df['access_count'].rolling(window, min_periods=1).std()
            
            # Fill NaN std values with 0
            df[f'rolling_std_{window}'] = df[f'rolling_std_{window}'].fillna(0)
        
        return df
    
    def _add_holiday_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add holiday-related features"""
        df['is_holiday'] = df['date'].apply(lambda x: 1 if x in self.holidays else 0)
        
        # Days to/from nearest holiday
        df['days_to_holiday'] = df['date'].apply(self._days_to_nearest_holiday)
        df['days_from_holiday'] = df['date'].apply(self._days_from_nearest_holiday)
        
        return df
    
    def _add_trend_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add trend features"""
        # Simple linear trend
        df['time_index'] = range(len(df))
        
        # Moving average trend
        df['trend_ma_7'] = df['access_count'].rolling(7, min_periods=1).mean()
        
        return df
    
    def _get_time_features(self, target_date: date) -> List[float]:
        """Get time features for a specific date"""
        dt = pd.Timestamp(target_date)
        
        features = [
            dt.year,
            dt.month,
            dt.day,
            dt.dayofweek,
            dt.dayofyear,
            dt.isocalendar()[1],  # week of year
            dt.quarter,
            np.sin(2 * np.pi * dt.month / 12),
            np.cos(2 * np.pi * dt.month / 12),
            np.sin(2 * np.pi * dt.dayofweek / 7),
            np.cos(2 * np.pi * dt.dayofweek / 7),
            1 if dt.dayofweek >= 5 else 0,  # is_weekend
            1 if dt.day <= 5 else 0,  # is_month_start
            1 if dt.day >= 25 else 0  # is_month_end
        ]
        
        return features
    
    def _days_to_nearest_holiday(self, current_date: date) -> int:
        """Calculate days to nearest future holiday"""
        future_holidays = [h for h in self.holidays if h > current_date]
        if future_holidays:
            return (min(future_holidays) - current_date).days
        return 365  # No holiday in next year
    
    def _days_from_nearest_holiday(self, current_date: date) -> int:
        """Calculate days from nearest past holiday"""
        past_holidays = [h for h in self.holidays if h <= current_date]
        if past_holidays:
            return (current_date - max(past_holidays)).days
        return 365  # No holiday in past year
    
    def get_feature_names(self) -> List[str]:
        """Get list of feature names"""
        return self.feature_names
    
    def get_feature_importance(self, model: Any, feature_names: Optional[List[str]] = None) -> Dict[str, float]:
        """Extract feature importance from trained model"""
        if feature_names is None:
            feature_names = self.feature_names
        
        importance_dict = {}
        
        # XGBoost
        if hasattr(model, 'feature_importances_'):
            importances = model.feature_importances_
            for name, importance in zip(feature_names, importances):
                importance_dict[name] = float(importance)
        
        # Linear models
        elif hasattr(model, 'coef_'):
            coefficients = np.abs(model.coef_)
            for name, coef in zip(feature_names, coefficients):
                importance_dict[name] = float(coef)
        
        return importance_dict