import pytest
from datetime import datetime, timedelta
from app.engine.risk_engine import forecast_time_to_threshold

class MockReading:
    def __init__(self, timestamp: datetime, reading_ppm: float):
        self.timestamp = timestamp
        self.reading_ppm = reading_ppm

def test_forecasting_rising_trend():
    # Clearly rising synthetic trend: starts at 5 ppm, rises 0.5 ppm every minute
    # Threshold = 10.0 ppm
    start_time = datetime(2026, 1, 1, 12, 0, 0)
    readings = []
    for i in range(10): # 10 readings over 10 minutes
        timestamp = start_time + timedelta(minutes=i)
        value = 5.0 + 0.5 * i # 5.0, 5.5, 6.0, ..., 9.5
        readings.append(MockReading(timestamp, value))
        
    # Last reading is at 9.0 minutes (value = 9.5 ppm)
    # Threshold (10.0 ppm) should be reached in 1.0 more minute (at 10.0 minutes)
    pred_minutes, conf_int = forecast_time_to_threshold(readings, 10.0)
    
    assert pred_minutes is not None
    assert abs(pred_minutes - 1.0) < 0.1
    assert pred_minutes >= 0
    assert conf_int is not None
    assert conf_int >= 0

def test_forecasting_flat_trend():
    # Flat stable trend: value stays at 5.0 ppm
    start_time = datetime(2026, 1, 1, 12, 0, 0)
    readings = []
    for i in range(10):
        timestamp = start_time + timedelta(minutes=i)
        readings.append(MockReading(timestamp, 5.0))
        
    pred_minutes, conf_int = forecast_time_to_threshold(readings, 10.0)
    
    # Should not predict a breach since trend is flat (slope <= 0)
    assert pred_minutes is None
    assert conf_int is None

def test_forecasting_falling_trend():
    # Falling trend: starts at 5.0 ppm and falls
    start_time = datetime(2026, 1, 1, 12, 0, 0)
    readings = []
    for i in range(10):
        timestamp = start_time + timedelta(minutes=i)
        value = 5.0 - 0.2 * i
        readings.append(MockReading(timestamp, value))
        
    pred_minutes, conf_int = forecast_time_to_threshold(readings, 10.0)
    
    # Should not predict a breach since trend is falling
    assert pred_minutes is None
    assert conf_int is None
