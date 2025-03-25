"""
Tests for the utils package.
"""

import pytest
from datetime import datetime, timedelta
from utils.helpers import format_currency, calculate_deadline_status, validate_grant_data

def test_format_currency():
    assert format_currency(1000) == '$1,000.00'
    assert format_currency(1000.50) == '$1,000.50'

def test_calculate_deadline_status():
    now = datetime.now()
    past = now - timedelta(days=1)
    future = now + timedelta(days=10)
    soon = now + timedelta(days=3)
    
    assert calculate_deadline_status(past) == 'expired'
    assert calculate_deadline_status(future) == 'upcoming'
    assert calculate_deadline_status(soon) == 'due_soon'

def test_validate_grant_data():
    valid_data = {
        'title': 'Test Grant',
        'amount': 1000,
        'deadline': datetime.now()
    }
    
    invalid_data = {
        'title': 'Test Grant',
        'amount': 1000
    }
    
    is_valid, _ = validate_grant_data(valid_data)
    assert is_valid
    
    is_valid, error = validate_grant_data(invalid_data)
    assert not is_valid
    assert 'deadline' in error