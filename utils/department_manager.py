#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Department Manager Module

Handles department-related operations in FreshService.
"""

import logging
from typing import Dict, List, Optional, Any

from .api_client import FreshServiceAPI


class DepartmentManager:
    """
    Manages FreshService departments.
    Provides functionality for fetching departments and managing department hierarchies.
    """
    
    def __init__(self, api_client: FreshServiceAPI, workspace_id: int, logger: logging.Logger):
        """
        Initialize the department manager.
        
        Args:
            api_client: FreshServiceAPI instance
            workspace_id: Current workspace ID
            logger: Logger instance
        """
        self.api_client = api_client
        self.workspace_id = workspace_id
        self.logger = logger
        self._departments_cache = None
    
    def get_departments(self) -> List[Dict[str, Any]]:
        """
        Fetch all departments from FreshService.
        Uses a cache to avoid redundant API calls.
        
        Returns:
            List of department dictionaries
        """
        if self._departments_cache is None:
            self.logger.info("Fetching all departments...")
            try:
                response = self.api_client.get(
                    "departments",
                    workspace_id=self.workspace_id
                )
                departments = response.get("departments", [])
                
                if departments:
                    self.logger.info(f"Found {len(departments)} departments")
                    self._departments_cache = departments
                else:
                    self.logger.warning("No departments found")
                    self._departments_cache = []
            except Exception as e:
                self.logger.error(f"Error fetching departments: {str(e)}")
                self._departments_cache = []
        
        return self._departments_cache
    
    def get_department_by_id(self, department_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a department by its ID.
        
        Args:
            department_id: Department ID to find
            
        Returns:
            Department dictionary if found, None otherwise
        """
        departments = self.get_departments()
        for department in departments:
            if department.get("id") == department_id:
                return department
        
        self.logger.warning(f"Department with ID {department_id} not found")
        return None
    
    def get_department_by_name(self, department_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a department by its name.
        
        Args:
            department_name: Department name to find
            
        Returns:
            Department dictionary if found, None otherwise
        """
        departments = self.get_departments()
        for department in departments:
            if department.get("name") == department_name:
                return department
        
        self.logger.warning(f"Department with name '{department_name}' not found")
        return None
    
    def search_departments(self, search_term: str) -> List[Dict[str, Any]]:
        """
        Search for departments matching a search term.
        
        Args:
            search_term: Term to search for in department names
            
        Returns:
            List of matching department dictionaries
        """
        departments = self.get_departments()
        matches = []
        
        # Convert search term to lowercase for case-insensitive matching
        search_term_lower = search_term.lower()
        
        for department in departments:
            name = department.get("name", "").lower()
            description = department.get("description", "").lower()
            
            if search_term_lower in name or search_term_lower in description:
                matches.append(department)
        
        self.logger.info(f"Found {len(matches)} departments matching '{search_term}'")
        return matches
    
    def get_department_hierarchy(self) -> Dict[str, Any]:
        """
        Build a hierarchical representation of departments.
        
        Returns:
            Dictionary representing the department hierarchy
        """
        departments = self.get_departments()
        hierarchy = {}
        
        # First, create a map of department ID to department
        dept_map = {dept.get("id"): dept for dept in departments}
        
        # Create a map of parent ID to children departments
        parent_map = {}
        for dept_id, dept in dept_map.items():
            parent_id = dept.get("parent_department_id")
            if parent_id not in parent_map:
                parent_map[parent_id] = []
            parent_map[parent_id].append(dept_id)
        
        # Recursive function to build the hierarchy
        def build_hierarchy(parent_id):
            if parent_id not in parent_map:
                return {}
            
            result = {}
            for dept_id in parent_map[parent_id]:
                dept = dept_map[dept_id]
                dept_name = dept.get("name")
                result[dept_name] = build_hierarchy(dept_id)
            
            return result
        
        # Start with departments that have no parent (None as parent_id)
        hierarchy = build_hierarchy(None)
        
        return hierarchy
    
    def get_department_options(self) -> List[Dict[str, str]]:
        """
        Get a list of departments formatted for menu options.
        
        Returns:
            List of department dictionaries with id and name
        """
        departments = self.get_departments()
        options = []
        
        for department in departments:
            dept_id = department.get("id")
            name = department.get("name")
            
            if dept_id and name:
                options.append({
                    "id": dept_id,
                    "name": name
                })
        
        # Sort options by name
        options.sort(key=lambda x: x["name"])
        
        return options
    
    def refresh_departments(self) -> List[Dict[str, Any]]:
        """
        Force refresh of departments from the API.
        Clears the cache and fetches fresh data.
        
        Returns:
            Updated list of department dictionaries
        """
        self.logger.info("Refreshing departments...")
        self._departments_cache = None
        return self.get_departments()
    
    def display_department_tree(self) -> None:
        """
        Display a tree-like representation of the department hierarchy.
        Useful for visualizing the organizational structure.
        """
        hierarchy = self.get_department_hierarchy()
        
        def _print_tree(tree, indent=0):
            for name, children in tree.items():
                self.logger.info(" " * indent + "- " + name)
                _print_tree(children, indent + 2)
        
        self.logger.info("Department Hierarchy:")
        _print_tree(hierarchy)
    
    def get_department_users(self, department_id: int) -> List[Dict[str, Any]]:
        """
        Get all users in a specific department.
        
        Args:
            department_id: Department ID to find users for
            
        Returns:
            List of user dictionaries
        """
        try:
            self.logger.info(f"Fetching users for department {department_id}")
            
            # Query the API for users in this department
            response = self.api_client.get(
                "users",
                params={"department_id": department_id},
                workspace_id=self.workspace_id
            )
            
            users = response.get("users", [])
            self.logger.info(f"Found {len(users)} users in department {department_id}")
            
            return users
        except Exception as e:
            self.logger.error(f"Error fetching users for department {department_id}: {str(e)}")
            return [] 