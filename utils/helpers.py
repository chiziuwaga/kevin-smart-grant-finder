"""
Utility functions for the application.
"""

from datetime import datetime, timedelta

def format_currency(amount):
    """
    Format a number as currency.
    
    Args:
        amount (float): Amount to format
        
    Returns:
        str: Formatted currency string
    """
    return f'${amount:,.2f}'

def calculate_days_remaining(deadline):
    """
    Calculate days remaining until deadline.
    
    Args:
        deadline (datetime): Grant deadline
        
    Returns:
        int: Number of days remaining (negative if expired)
    """
    if not deadline:
        return None
    
    now = datetime.now()
    delta = deadline - now
    return delta.days

def calculate_deadline_status(deadline):
    """
    Calculate status based on deadline.
    
    Args:
        deadline (datetime): Grant deadline
        
    Returns:
        str: Status (upcoming, due_soon, expired)
    """
    now = datetime.now()
    if deadline < now:
        return 'expired'
    elif deadline - now <= timedelta(days=7):
        return 'due_soon'
    return 'upcoming'

def validate_grant_data(data):
    """
    Validate grant data structure.
    
    Args:
        data (dict): Grant data to validate
        
    Returns:
        tuple: (bool, str) - (is_valid, error_message)
    """
    required_fields = ['title', 'amount', 'deadline']
    
    for field in required_fields:
        if field not in data:
            return False, f'Missing required field: {field}'
    
    return True, ''