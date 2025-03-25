# API Integration Guide

## Overview
This document outlines the API integrations used in Kevin's Smart Grant Finder system.

## Core APIs

### 1. MongoDB Integration
```python
from database.mongodb_client import MongoDBClient

# Initialize client
client = MongoDBClient()

# Store grant data
client.store_grant({
    'title': 'Grant Title',
    'amount': 50000,
    'deadline': '2024-12-31',
    'source': 'grants.gov',
    'category': 'federal'
})

# Query grants
grants = client.get_grants(
    min_score=0.85,
    days_to_deadline=30,
    category='federal'
)
```

### 2. Pinecone Vector Search
```python
from database.pinecone_client import PineconeClient

# Initialize client
client = PineconeClient()

# Index grant description
client.index_grant(
    id='grant_123',
    description='Rural broadband deployment grant...',
    metadata={
        'category': 'telecom',
        'amount': 100000
    }
)

# Search similar grants
results = client.search(
    query='rural connectivity infrastructure',
    filter={
        'category': 'telecom'
    }
)
```

### 3. Grant Source APIs

#### Grants.gov API
```python
from utils.api_clients import GrantsGovClient

client = GrantsGovClient()
grants = client.search(
    keywords=['telecommunications', 'broadband'],
    agency='USDA',
    eligibility='nonprofits'
)
```

#### USDA Grants API
```python
from utils.api_clients import USDAClient

client = USDAClient()
programs = client.get_programs(
    category='telecommunications',
    state='LA'
)
```

## Data Models

### Grant Schema
```python
grant_schema = {
    'title': str,
    'description': str,
    'amount': float,
    'deadline': datetime,
    'source': str,
    'category': str,
    'score': float,
    'url': str,
    'requirements': list,
    'status': str
}
```

### Search Parameters
```python
search_params = {
    'keywords': list,
    'filters': {
        'category': str,
        'min_amount': float,
        'max_amount': float,
        'deadline_after': datetime,
        'deadline_before': datetime,
        'source': str
    },
    'sort': {
        'field': str,
        'order': str
    }
}
```

## Error Handling

```python
class APIError(Exception):
    def __init__(self, message, status_code=None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

def handle_api_error(error):
    if isinstance(error, APIError):
        log_error(error.message, error.status_code)
        return {
            'error': error.message,
            'status': error.status_code
        }
    return {
        'error': 'Internal server error',
        'status': 500
    }
```

## Rate Limiting

```python
from utils.rate_limiter import RateLimiter

limiter = RateLimiter(
    max_requests=100,
    time_window=60  # seconds
)

@limiter.limit
def make_api_request():
    # API call implementation
    pass
```

## Authentication

```python
from utils.auth import APIKeyAuth

auth = APIKeyAuth(
    api_key=os.getenv('API_KEY'),
    api_secret=os.getenv('API_SECRET')
)

def get_auth_headers():
    return {
        'Authorization': f'Bearer {auth.get_token()}',
        'Content-Type': 'application/json'
    }
```

## Webhook Integration

```python
from flask import Flask, request
from utils.webhook_handler import WebhookHandler

app = Flask(__name__)
handler = WebhookHandler()

@app.route('/webhook/grants', methods=['POST'])
def handle_grant_webhook():
    data = request.json
    handler.process_grant_update(data)
    return {'status': 'success'}
```

## Best Practices

1. **Error Handling**
   - Implement proper error handling for all API calls
   - Log errors with sufficient context
   - Return meaningful error messages

2. **Rate Limiting**
   - Respect API rate limits
   - Implement backoff strategies
   - Cache responses when possible

3. **Authentication**
   - Store credentials securely
   - Rotate API keys regularly
   - Use environment variables for sensitive data

4. **Monitoring**
   - Track API response times
   - Monitor rate limit usage
   - Set up alerts for API failures

5. **Testing**
   - Write unit tests for API integrations
   - Use mock responses for testing
   - Validate response schemas 