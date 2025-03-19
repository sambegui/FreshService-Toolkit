#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Workspace Manager Module

Handles workspace discovery and management.
"""

import logging
from typing import Dict, List, Optional, Any

from .api_client import FreshServiceAPI


class WorkspaceManager:
    """
    Manages FreshService workspaces.
    Provides functionality to discover and switch between workspaces.
    """
    
    def __init__(self, api_client: FreshServiceAPI, logger: logging.Logger):
        """
        Initialize the workspace manager.
        
        Args:
            api_client: FreshServiceAPI instance
            logger: Logger instance
        """
        self.api_client = api_client
        self.logger = logger
        self._workspaces_cache = None
        self.current_workspace_id = None
        self._initialize_current_workspace()
    
    def _initialize_current_workspace(self) -> None:
        """Initialize the current workspace."""
        workspaces = self.get_workspaces()
        if workspaces:
            self.current_workspace_id = workspaces[0].get("id")
            self.logger.info(f"Initialized current workspace ID: {self.current_workspace_id}")
        else:
            self.logger.warning("No workspaces available")
    
    def get_current_workspace(self) -> Optional[Dict[str, Any]]:
        """
        Get the current workspace.
        
        Returns:
            Current workspace dictionary if available, None otherwise
        """
        if self.current_workspace_id:
            return self.get_workspace_by_id(self.current_workspace_id)
        return None
    
    def get_workspaces(self) -> List[Dict[str, Any]]:
        """
        Fetch all available workspaces from FreshService.
        Uses a cache to avoid redundant API calls.
        
        Returns:
            List of workspace dictionaries
        """
        if self._workspaces_cache is None:
            self.logger.info("Fetching available workspaces...")
            try:
                response = self.api_client.get("workspaces")
                self.logger.debug(f"Workspace API Response: {response}")
                
                workspaces = response.get("workspaces", [])
                
                if workspaces:
                    self.logger.info(f"Found {len(workspaces)} workspaces")
                    self._workspaces_cache = workspaces
                else:
                    self.logger.warning("No workspaces found in the API response")
                    self.logger.debug(f"Full API response: {response}")
                    # If no workspaces found, try using a default workspace
                    default_workspace = {
                        "id": 1,  # Default workspace ID is typically 1
                        "name": "Default Workspace",
                        "description": "Default FreshService workspace"
                    }
                    self._workspaces_cache = [default_workspace]
                    self.logger.info("Using default workspace as fallback")
            except Exception as e:
                self.logger.error(f"Error fetching workspaces: {str(e)}")
                self.logger.debug("Attempting to use default workspace...")
                # If API call fails, try using a default workspace
                default_workspace = {
                    "id": 1,  # Default workspace ID is typically 1
                    "name": "Default Workspace",
                    "description": "Default FreshService workspace"
                }
                self._workspaces_cache = [default_workspace]
                self.logger.info("Using default workspace as fallback")
        
        return self._workspaces_cache
    
    def get_workspace_by_id(self, workspace_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a workspace by its ID.
        
        Args:
            workspace_id: Workspace ID to find
            
        Returns:
            Workspace dictionary if found, None otherwise
        """
        workspaces = self.get_workspaces()
        for workspace in workspaces:
            if workspace.get("id") == workspace_id:
                return workspace
        
        self.logger.warning(f"Workspace with ID {workspace_id} not found")
        return None
    
    def get_workspace_by_name(self, workspace_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a workspace by its name.
        
        Args:
            workspace_name: Workspace name to find
            
        Returns:
            Workspace dictionary if found, None otherwise
        """
        workspaces = self.get_workspaces()
        for workspace in workspaces:
            if workspace.get("name") == workspace_name:
                return workspace
        
        self.logger.warning(f"Workspace with name '{workspace_name}' not found")
        return None
    
    def refresh_workspaces(self) -> List[Dict[str, Any]]:
        """
        Force refresh of workspaces from the API.
        Clears the cache and fetches fresh data.
        
        Returns:
            Updated list of workspace dictionaries
        """
        self.logger.info("Refreshing workspaces...")
        self._workspaces_cache = None
        return self.get_workspaces()
    
    def list_workspace_details(self) -> None:
        """
        Print detailed information about each workspace.
        Useful for debugging and information purposes.
        """
        workspaces = self.get_workspaces()
        
        if not workspaces:
            self.logger.info("No workspaces available")
            return
        
        self.logger.info(f"Available Workspaces ({len(workspaces)}):")
        for workspace in workspaces:
            workspace_id = workspace.get("id")
            name = workspace.get("name")
            description = workspace.get("description", "No description")
            
            self.logger.info(f"ID: {workspace_id} | Name: {name}")
            self.logger.info(f"  Description: {description}")
            self.logger.info("  -" * 30) 