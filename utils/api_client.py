#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FreshService API Client

This module handles all API interactions with FreshService.
"""

import base64
import json
import logging
import time
from typing import Dict, List, Optional, Any, Union
import requests
from requests.exceptions import RequestException


class FreshServiceAPI:
    """
    FreshService API client for interacting with the FreshService API.
    Handles authentication, rate limiting, and error handling.
    """
    
    BASE_URL = "https://fridababy.freshservice.com/api"
    API_VERSION = "v2"
    # Rate limiting: 50 requests per minute (as per FreshService API documentation)
    RATE_LIMIT = 50
    RATE_LIMIT_WINDOW = 60  # 60 seconds (1 minute)
    # Endpoints that don't need workspace prefix
    NON_WORKSPACE_ENDPOINTS = [
        "requesters", "agents", "departments", "groups", "roles",
        "locations", "products", "vendors", "assets", "problems",
        "releases", "changes", "solutions", "users"
    ]
    
    def __init__(self, api_key: str, logger: logging.Logger, dry_run: bool = False):
        """
        Initialize the FreshService API client.
        
        Args:
            api_key: The FreshService API key
            logger: Logger instance for logging
            dry_run: Whether to run in dry run mode (no changes made)
        """
        self.api_key = api_key
        self.logger = logger
        self.dry_run = dry_run
        self.auth_header = self._get_auth_header()
        self.domain = self._extract_domain_from_key()
        
        # Rate limiting tracking
        self.request_timestamps = []
    
    def _extract_domain_from_key(self) -> str:
        """Extract the domain from the API key format."""
        try:
            # API keys often contain the domain information
            # Format might be: domain:key or similar
            if ':' in self.api_key:
                return self.api_key.split(':')[0]
        except Exception as e:
            self.logger.warning(f"Could not extract domain from API key: {str(e)}")
        return None
    
    def _get_auth_header(self) -> Dict[str, str]:
        """
        Generate the authentication header for API requests.
        
        Returns:
            Auth header dictionary
        """
        # FreshService requires Basic auth with API key as the username part
        try:
            # Encode your_api_key:X where X can be any string or empty
            encoded_key = base64.b64encode(f"{self.api_key}:X".encode()).decode()
            return {
                'Authorization': f'Basic {encoded_key}',
                'Content-Type': 'application/json'
            }
        except Exception as e:
            self.logger.error(f"Failed to create auth header: {e}")
            return {
                'Authorization': f'Basic {self.api_key}',
                'Content-Type': 'application/json'
            }
    
    def _check_rate_limit(self) -> None:
        """
        Enforce rate limiting to avoid API throttling.
        Sleeps if necessary to stay within rate limits.
        """
        now = time.time()
        
        # Remove timestamps older than the window
        window_start = now - self.RATE_LIMIT_WINDOW
        self.request_timestamps = [ts for ts in self.request_timestamps if ts > window_start]
        
        # Check if we're at the limit
        if len(self.request_timestamps) >= self.RATE_LIMIT:
            # Calculate how long to wait
            oldest_request = min(self.request_timestamps)
            wait_time = self.RATE_LIMIT_WINDOW - (now - oldest_request)
            
            if wait_time > 0:
                # Log at debug level to avoid cluttering console
                self.logger.debug(f"Rate limit reached. Waiting {wait_time:.2f} seconds.")
                time.sleep(wait_time)

    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None, 
        params: Optional[Dict] = None,
        workspace_id: Optional[int] = None,
        expect_no_content: bool = False
    ) -> Dict:
        """
        Make an HTTP request to the FreshService API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path (without /api/v2/)
            data: Request data (for POST, PUT)
            params: URL parameters
            workspace_id: Optional workspace ID
            expect_no_content: If True, handle 204 No Content responses as success
            
        Returns:
            Response data as dictionary
            
        Raises:
            Exception on API error or rate limiting
        """
        # Rate limiting check
        self._check_rate_limit()
        
        # Add workspace ID to the endpoint if provided and needed
        workspace_endpoint = endpoint
        if workspace_id is not None:
            # Check if this is an endpoint that should NOT have workspace prefix
            # User endpoints like requesters/agents don't use workspace paths
            should_add_workspace = True
            
            try:
                # Check if the endpoint starts with any of the non-workspace endpoints
                for non_ws_endpoint in self.NON_WORKSPACE_ENDPOINTS:
                    if endpoint.startswith(non_ws_endpoint):
                        should_add_workspace = False
                        break
            except (AttributeError, TypeError):
                # If NON_WORKSPACE_ENDPOINTS doesn't exist, continue without changes
                self.logger.debug(f"NON_WORKSPACE_ENDPOINTS not defined, continuing with original endpoint")
            
            if should_add_workspace and 'workspace' not in endpoint:
                workspace_endpoint = f"workspaces/{workspace_id}/{endpoint}"
        
        # Build full URL
        url = f"{self.BASE_URL}/{self.API_VERSION}/{workspace_endpoint}"
        
        # Record the start time for rate limiting
        request_start = time.time()
        
        # Execute the request - log at info level for PUT/POST to aid debugging
        log_level = logging.INFO if method in ['PUT', 'POST'] else logging.DEBUG
        self.logger.log(log_level, f"Making {method} request to {url}")
        
        if params:
            self.logger.debug(f"Query params: {params}")
        
        if data and method in ['PUT', 'POST']:
            # For PUT/POST, log data at INFO level for debugging
            self.logger.info(f"Request data: {json.dumps(data)}")
            
        # Skip actual API call in dry run mode for modifying requests
        if self.dry_run and method != 'GET':
            self.logger.info(f"DRY RUN: Would make {method} request to {url}")
            if data:
                self.logger.debug(f"DRY RUN: With data: {json.dumps(data)}")
            return {"dry_run": True, "success": True, "message": "This is a dry run"}
        
        try:
            # Track this request
            self.request_timestamps.append(time.time())
            
            # Handle JSON data
            json_data = None
            if data:
                json_data = data
            
            # Make the request with verbose logging for debugging
            self.logger.info(f"HTTP {method} {url}")
            if json_data:
                self.logger.info(f"Request headers: {self.auth_header}")
                self.logger.info(f"Request payload: {json.dumps(json_data)}")
            
            response = requests.request(
                method=method,
                url=url,
                headers=self.auth_header,
                params=params,
                json=json_data
            )
            
            # Log response info for debugging
            self.logger.info(f"Response status: {response.status_code}")
            
            # Handle 204 No Content responses (used for delete operations)
            if expect_no_content and response.status_code == 204:
                self.logger.debug(f"Request to {url} succeeded with status 204 No Content")
                return True
            
            # Log response for debugging PUT/POST requests
            if method in ['PUT', 'POST']:
                try:
                    self.logger.info(f"Response headers: {response.headers}")
                    self.logger.info(f"Response text: {response.text}")
                except:
                    pass
            
            # Check for errors
            if response.status_code >= 400:
                # Try to get detailed error information
                error_details = None
                try:
                    error_details = response.json()
                    # Log details at info level for better debugging
                    self.logger.info(f"Error details: {error_details}")
                except:
                    self.logger.info(f"Raw error response: {response.text}")
                
                error_msg = f"{response.status_code} {response.reason} for url: {url}"
                # Log summary at error level for console
                self.logger.error(f"API request failed: {error_msg}")
                raise Exception(f"API request failed: {error_msg}")
            
            # Log success at debug level to reduce console output
            self.logger.debug(f"Request to {url} succeeded with status {response.status_code}")
            
            # Return the JSON response
            try:
                return response.json()
            except Exception as json_error:
                self.logger.error(f"Failed to parse JSON response: {str(json_error)}")
                self.logger.info(f"Raw response: {response.text}")
                raise Exception(f"Failed to parse API response as JSON: {str(json_error)}")
            
        except Exception as e:
            # Log the error at debug level with details, error level for summary
            self.logger.debug(f"Request to {url} failed: {str(e)}")
            # Don't re-raise for common 404/403 errors to allow fallback mechanisms to work
            if "404" in str(e) or "403" in str(e):
                self.logger.debug(f"Non-critical error: {str(e)}")
                raise e
            else:
                self.logger.error(f"API request error: {str(e).split('for url')[0]}")
                raise e
        finally:
            # Track request duration for rate limiting
            request_duration = time.time() - request_start
            self.logger.debug(f"Request took {request_duration:.3f} seconds")
    
    def get(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        workspace_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send a GET request to the FreshService API.
        
        Args:
            endpoint: API endpoint to call
            params: Query parameters
            workspace_id: Workspace ID for scoped requests
            
        Returns:
            Response data as dictionary
        """
        return self._make_request('GET', endpoint, params=params, workspace_id=workspace_id)
    
    def post(
        self, 
        endpoint: str, 
        data: Dict[str, Any],
        workspace_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send a POST request to the FreshService API.
        
        Args:
            endpoint: API endpoint to call
            data: Request data
            workspace_id: Workspace ID for scoped requests
            
        Returns:
            Response data as dictionary
        """
        return self._make_request('POST', endpoint, data=data, workspace_id=workspace_id)
    
    def put(
        self, 
        endpoint: str, 
        data: Dict[str, Any],
        workspace_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send a PUT request to the FreshService API.
        
        Args:
            endpoint: API endpoint to call
            data: Request data
            workspace_id: Workspace ID for scoped requests
            
        Returns:
            Response data as dictionary
        """
        return self._make_request('PUT', endpoint, data=data, workspace_id=workspace_id)
    
    def delete(
        self, 
        endpoint: str,
        workspace_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send a DELETE request to the FreshService API.
        
        Args:
            endpoint: API endpoint to call
            workspace_id: Workspace ID for scoped requests
            
        Returns:
            Response data as dictionary
        """
        return self._make_request('DELETE', endpoint, workspace_id=workspace_id, expect_no_content=True) 