# """
# Tests for scrape endpoint.
# """
# import pytest
# from flask import json

# def test_scrape_url_success(client, auth_headers):
#     """Test successful URL scraping."""
#     data = {'url': 'https://example.com'}
#     response = client.post('/api/scrape', json=data, headers=auth_headers)
#     assert response.status_code == 200

# def test_scrape_url_invalid_url(client, auth_headers):
#     """Test scraping with invalid URL."""
#     data = {'url': 'not-a-url'}
#     response = client.post('/api/scrape', json=data, headers=auth_headers)
#     assert response.status_code == 400
#     assert 'URL' in response.json['error']['message']

# def test_scrape_url_missing_url(client, auth_headers):
#     """Test scraping without URL parameter."""
#     response = client.post('/api/scrape', json={}, headers=auth_headers)
#     assert response.status_code == 400
#     assert 'URL is required' in response.json['error']['message']

# def test_scrape_url_empty_url(client, auth_headers):
#     """Test scraping with empty URL."""
#     data = {'url': ''}
#     response = client.post('/api/scrape', json=data, headers=auth_headers)
#     assert response.status_code == 400
#     assert 'URL' in response.json['error']['message']

# def test_scrape_url_invalid_json(client, auth_headers):
#     """Test scraping with invalid JSON payload."""
#     response = client.post('/api/scrape', 
#         data='invalid json',
#         headers=auth_headers,
#         content_type='application/json'
#     )
#     assert response.status_code == 400
#     assert 'Request must be JSON' in response.json['error']['message']

# def test_scrape_url_unsupported_protocol(client, auth_headers):
#     """Test scraping with unsupported protocol."""
#     data = {'url': 'ftp://example.com'}
#     response = client.post('/api/scrape', json=data, headers=auth_headers)
#     assert response.status_code == 400
#     assert 'protocol' in response.json['error']['message'].lower()

# def test_scrape_url_timeout(client, auth_headers):
#     """Test scraping with a URL that causes timeout."""
#     data = {'url': 'https://httpstat.us/200?sleep=5000'}  # 5 second delay
#     response = client.post('/api/scrape', json=data, headers=auth_headers)
#     assert response.status_code == 500
#     assert 'timeout' in response.json['error']['message'].lower()

# def test_scrape_url_not_found(client, auth_headers):
#     """Test scraping with a non-existent URL."""
#     data = {'url': 'https://example.com/nonexistent'}
#     response = client.post('/api/scrape', json=data, headers=auth_headers)
#     assert response.status_code == 500
#     assert 'not found' in response.json['error']['message'].lower()

# def test_scrape_url_server_error(client, auth_headers):
#     """Test scraping with a URL that returns server error."""
#     data = {'url': 'https://httpstat.us/500'}
#     response = client.post('/api/scrape', json=data, headers=auth_headers)
#     assert response.status_code == 500
#     assert 'server' in response.json['error']['message'].lower() 