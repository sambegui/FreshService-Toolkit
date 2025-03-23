#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
User Manager Module

Handles user-related operations in FreshService.
"""

import logging
import re
import json
from typing import Dict, List, Optional, Any, Tuple

from .api_client import FreshServiceAPI


class UserManager:
    """
    Manages FreshService users.
    Provides functionality for looking up, creating, updating, and deactivating users.
    """
    
    def __init__(
        self, 
        api_client: FreshServiceAPI, 
        workspace_id: int,
        logger: logging.Logger,
        dry_run: bool = False
    ):
        """
        Initialize the user manager.
        
        Args:
            api_client: FreshServiceAPI instance
            workspace_id: Current workspace ID
            logger: Logger instance
            dry_run: Whether to run in dry run mode
        """
        self.api_client = api_client
        self.workspace_id = workspace_id
        self.logger = logger
        self.dry_run = dry_run
        self.recent_users = []  # Cache for recently accessed users
        self.max_recent_users = 10  # Maximum number of recent users to track
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a user by their ID.
        
        Args:
            user_id: User ID to look up
            
        Returns:
            User dictionary if found, None otherwise
        """
        try:
            # Try requester endpoint first
            try:
                self.logger.debug(f"Trying to find user with ID {user_id} in requesters...")
                response = self.api_client.get(
                    f"requesters/{user_id}",
                    workspace_id=self.workspace_id
                )
                user = response.get("requester")
                
                if user:
                    self.logger.debug(f"Found user with ID {user_id} in requesters")
                    self._add_to_recent_users(user)
                    return user
            except Exception as e:
                self.logger.debug(f"User ID {user_id} not found in requesters: {e}")
            
            # Then try agent endpoint
            try:
                self.logger.debug(f"Trying to find user with ID {user_id} in agents...")
                response = self.api_client.get(
                    f"agents/{user_id}",
                    workspace_id=self.workspace_id
                )
                user = response.get("agent")
                
                if user:
                    self.logger.debug(f"Found user with ID {user_id} in agents")
                    self._add_to_recent_users(user)
                    return user
            except Exception as e:
                self.logger.debug(f"User ID {user_id} not found in agents: {e}")
            
            # If we reach this point, user wasn't found
            self.logger.warning(f"User with ID {user_id} not found in either requesters or agents")
            return None
                
        except Exception as e:
            self.logger.error(f"Error fetching user with ID {user_id}: {str(e)}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get a user by their email address.
        
        Args:
            email: User email to look up
            
        Returns:
            User dictionary if found, None otherwise
        """
        try:
            # Email validation
            if not self._is_valid_email(email):
                self.logger.warning(f"Invalid email format: {email}")
                return None
            
            # Try to find user in requesters first
            try:
                response = self.api_client.get(
                    "requesters",
                    params={"email": email},
                    workspace_id=self.workspace_id
                )
                
                users = response.get("requesters", [])
                
                if users and len(users) > 0:
                    user = users[0]  # Take the first match
                    self._add_to_recent_users(user)
                    return user
            except Exception as e:
                self.logger.warning(f"Error searching requester: {e}")
            
            # If not found, try agents endpoint with include_agents=true
            try:
                response = self.api_client.get(
                    "requesters",
                    params={"email": email, "include_agents": "true"},
                    workspace_id=self.workspace_id
                )
                
                users = response.get("requesters", [])
                
                if users and len(users) > 0:
                    user = users[0]  # Take the first match
                    self._add_to_recent_users(user)
                    return user
            except Exception as e:
                self.logger.warning(f"Error searching agent: {e}")
            
            self.logger.warning(f"No user found with email: {email}")
            return None
                
        except Exception as e:
            self.logger.error(f"Error fetching user with email {email}: {str(e)}")
            return None
    
    def search_users_by_name(
        self, 
        first_name: Optional[str] = None, 
        last_name: Optional[str] = None,
        fuzzy_match: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search for users by name with optional fuzzy matching.
        
        Args:
            first_name: First name to search for
            last_name: Last name to search for
            fuzzy_match: Whether to use fuzzy matching for approximate name matches
            
        Returns:
            List of matching user dictionaries
        """
        try:
            all_users = []
            
            # Skip API calls if no search terms provided
            if not first_name and not last_name:
                self.logger.debug("No search terms provided, returning empty results")
                return []
            
            # Build query string according to FreshService API format
            if first_name and last_name:
                # When both first and last name are provided, use the 'name' field
                # which is the combined first_name + last_name field in FreshService
                full_name = f"{first_name} {last_name}"
                query_string = f"~[name]:'{full_name}'"
                self.logger.debug(f"Using combined name query: {query_string}")
            else:
                # If only one is provided, use the appropriate field
                query_parts = []
                if first_name:
                    query_parts.append(f"~[first_name]:'{first_name}'")
                if last_name:
                    query_parts.append(f"~[last_name]:'{last_name}'")
                query_string = query_parts[0]
                self.logger.debug(f"Using single name component query: {query_string}")
            
            # Try to search requesters first
            try:
                self.logger.debug(f"Searching requesters with query: {query_string}")
                response = self.api_client.get(
                    "requesters",
                    params={"query": f'"{query_string}"'},
                    workspace_id=self.workspace_id
                )
                
                requesters = response.get("requesters", [])
                all_users.extend(requesters)
                
                # Update recent users for any exact matches
                for user in requesters:
                    self._add_to_recent_users(user)
                    
                self.logger.debug(f"Found {len(requesters)} requesters matching search criteria")
            except Exception as e:
                self.logger.warning(f"Error searching requesters by name: {e}")
                
                # If we get a 400, try a simplified search instead
                if "400" in str(e):
                    self.logger.debug("Got 400 error, trying simplified search")
                    # Try to search without the query parameter
                    try:
                        self.logger.debug("Fetching all requesters as fallback")
                        # Just get all requesters and filter manually
                        response = self.api_client.get(
                            "requesters",
                            workspace_id=self.workspace_id
                        )
                        
                        # Filter locally instead of via API
                        all_requesters = response.get("requesters", [])
                        
                        # Filter based on name case-insensitively
                        filtered_requesters = []
                        for user in all_requesters:
                            user_first = (user.get("first_name", "") or "").lower()
                            user_last = (user.get("last_name", "") or "").lower()
                            
                            first_match = not first_name or first_name.lower() in user_first
                            last_match = not last_name or last_name.lower() in user_last
                            
                            if first_match and last_match:
                                filtered_requesters.append(user)
                                
                        all_users.extend(filtered_requesters)
                        
                        # Update recent users
                        for user in filtered_requesters:
                            self._add_to_recent_users(user)
                            
                        self.logger.debug(f"Found {len(filtered_requesters)} requesters via manual filtering")
                    except Exception as e2:
                        self.logger.warning(f"Error in fallback requester search: {e2}")
            
            # Then try to search agents 
            try:
                self.logger.debug(f"Searching agents with query: {query_string}")
                response = self.api_client.get(
                    "requesters",
                    params={"query": f'"{query_string}"', "include_agents": "true"},
                    workspace_id=self.workspace_id
                )
                
                # Filter out any requesters already added (to avoid duplicates)
                requester_ids = {user.get("id") for user in all_users}
                agents = [
                    user for user in response.get("requesters", []) 
                    if user.get("id") not in requester_ids and user.get("is_agent", False)
                ]
                
                all_users.extend(agents)
                
                # Update recent users for any exact matches
                for user in agents:
                    self._add_to_recent_users(user)
                    
                self.logger.debug(f"Found {len(agents)} agents matching search criteria")
            except Exception as e:
                self.logger.warning(f"Error searching agents by name: {e}")
                
                # If we get a 400, try a simplified search instead
                if "400" in str(e):
                    self.logger.debug("Got 400 error, trying simplified search for agents")
                    # Try to search without the query parameter
                    try:
                        self.logger.debug("Fetching all agents as fallback")
                        # Get all agents and filter manually
                        response = self.api_client.get(
                            "agents",
                            workspace_id=self.workspace_id
                        )
                        
                        # Filter locally instead of via API
                        all_agents = response.get("agents", [])
                        
                        # Filter based on name case-insensitively
                        filtered_agents = []
                        for user in all_agents:
                            user_first = (user.get("first_name", "") or "").lower()
                            user_last = (user.get("last_name", "") or "").lower()
                            
                            first_match = not first_name or first_name.lower() in user_first
                            last_match = not last_name or last_name.lower() in user_last
                            
                            if first_match and last_match and user.get("id") not in requester_ids:
                                filtered_agents.append(user)
                                
                        all_users.extend(filtered_agents)
                        
                        # Update recent users
                        for user in filtered_agents:
                            self._add_to_recent_users(user)
                            
                        self.logger.debug(f"Found {len(filtered_agents)} agents via manual filtering")
                    except Exception as e2:
                        self.logger.warning(f"Error in fallback agent search: {e2}")
            
            # If no users found and fuzzy matching is enabled, try fuzzy search
            if not all_users and fuzzy_match:
                self.logger.debug(f"No exact matches found, trying fuzzy search")
                return self._fuzzy_name_search(first_name, last_name)
            
            return all_users
            
        except Exception as e:
            self.logger.error(f"Error searching users by name: {str(e)}")
            # If the main search fails, try fuzzy search as a fallback
            if fuzzy_match:
                try:
                    self.logger.debug("Attempting fuzzy search as fallback")
                    return self._fuzzy_name_search(first_name, last_name)
                except Exception as fuzzy_err:
                    self.logger.error(f"Fuzzy search fallback also failed: {str(fuzzy_err)}")
            return []
    
    def _fuzzy_name_search(
        self, 
        first_name: Optional[str] = None, 
        last_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform a simple fuzzy search on user names using string similarity.
        
        Args:
            first_name: First name to search for
            last_name: Last name to search for
            
        Returns:
            List of matching user dictionaries
        """
        try:
            all_users = []
            
            # If both first_name and last_name are None, return empty list
            if first_name is None and last_name is None:
                return []
                
            # Normalize search terms to lowercase if they exist
            search_first_name = first_name.lower() if first_name else ""
            search_last_name = last_name.lower() if last_name else ""
            
            # First try to get all requesters - this is just to get a pool of users to search
            try:
                response = self.api_client.get(
                    "requesters",
                    workspace_id=self.workspace_id
                )
                
                requesters = response.get("requesters", [])
                all_users.extend(requesters or [])
            except Exception as e:
                self.logger.debug(f"Error fetching requesters for fuzzy search: {e}")
            
            # Then try to get all agents
            try:
                response = self.api_client.get(
                    "agents",
                    workspace_id=self.workspace_id
                )
                
                agents = response.get("agents", [])
                # Avoid duplicates
                agent_ids = {agent.get("id") for agent in agents or []}
                requester_ids = {user.get("id") for user in all_users}
                
                for agent in agents or []:
                    if agent.get("id") not in requester_ids:
                        all_users.append(agent)
            except Exception as e:
                self.logger.debug(f"Error fetching agents for fuzzy search: {e}")
            
            # Now perform fuzzy search on the combined list
            matches = []
            
            for user in all_users:
                user_first = (user.get("first_name") or "").lower()
                user_last = (user.get("last_name") or "").lower()
                
                # Determine match score
                match_score = 0
                
                # Check first name
                if search_first_name and search_first_name in user_first:
                    # Exact match or contained within
                    if user_first == search_first_name:
                        match_score += 2
                    else:
                        match_score += 1
                
                # Check last name
                if search_last_name and search_last_name in user_last:
                    # Exact match or contained within
                    if user_last == search_last_name:
                        match_score += 2
                    else:
                        match_score += 1
                
                # Add user if we have a match
                if match_score > 0:
                    matches.append(user)
            
            # Update recent users for any matches
            for user in matches:
                self._add_to_recent_users(user)
            
            return matches
            
        except Exception as e:
            self.logger.error(f"Error in fuzzy name search: {str(e)}")
            return []
    
    def _is_agent(self, user_id: int) -> bool:
        """
        Check if a user is an agent or a requester by trying the agents endpoint first.
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if user is an agent, False if requester or unknown
        """
        try:
            # Try agent endpoint first
            response = self.api_client.get(
                f"agents/{user_id}",
                workspace_id=None  # Don't use workspace_id for user endpoints
            )
            # If we get a successful response, it's an agent
            return 'agent' in response
        except Exception:
            # If we get an error, assume it's not an agent
            return False
            
    def update_user(self, user_id: int, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update a user's details.
        
        Args:
            user_id: ID of the user to update
            update_data: Dictionary with fields to update
            
        Returns:
            Updated user dictionary if successful, None otherwise
        """
        try:
            # Log the update operation
            self.logger.info(f"Updating user with ID {user_id}")
            self.logger.debug(f"Original update data: {update_data}")
            
            # Check if the user is an agent directly (don't use get_user_by_id to avoid potential issues)
            is_agent = self._is_agent(user_id)
            endpoint = "agents" if is_agent else "requesters"
            
            self.logger.info(f"Identified user {user_id} as an {'agent' if is_agent else 'requester'}")
            
            # Handle dry run mode
            if self.dry_run:
                self.logger.info(f"DRY RUN: Would update {endpoint[:-1]} {user_id} with {update_data}")
                # Get current user to simulate updated user
                current_user = self.get_user_by_id(user_id)
                if current_user:
                    # Simulate update for display purposes
                    simulated_user = current_user.copy()
                    simulated_user.update(update_data)
                    return simulated_user
                return None
            
            # Process fields with special handling
            processed_data = {}
            
            # Use direct payload format that works with the API (without agent/requester wrapper)
            for key, value in update_data.items():
                # Special handling for department_ids
                if key == 'department_ids':
                    # Always ensure department_ids is a list of integers
                    if isinstance(value, list):
                        # Convert all values to integers
                        processed_data[key] = [int(dept_id) for dept_id in value]
                    else:
                        # Convert single value to a list with a single integer
                        processed_data[key] = [int(value)]
                else:
                    processed_data[key] = value
            
            # Log the final payload for debugging
            self.logger.info(f"Final request payload: {json.dumps(processed_data)}")
            
            # Make the API request with the direct payload format
            self.logger.info(f"Making PUT request to {endpoint}/{user_id}")
            try:
                response = self.api_client.put(
                    f"{endpoint}/{user_id}",
                    data=processed_data,
                    workspace_id=None  # Don't add workspace to user endpoints
                )
                
                # Process the response - extract user data from the response
                updated_user = response.get(endpoint[:-1])  # agent or requester key
                
                if updated_user:
                    self.logger.info(f"Successfully updated user {user_id}")
                    self._add_to_recent_users(updated_user)
                    return updated_user
                else:
                    self.logger.warning(f"User update response did not contain expected data: {response}")
                    return None
            except Exception as inner_e:
                self.logger.error(f"API request error: {str(inner_e)}")
                if hasattr(inner_e, 'response') and hasattr(inner_e.response, 'text'):
                    self.logger.error(f"Response text: {inner_e.response.text}")
                raise inner_e
                
        except Exception as e:
            self.logger.error(f"Error updating user {user_id}: {str(e)}")
            if hasattr(e, 'response') and e.response:
                try:
                    error_details = e.response.json()
                    self.logger.error(f"Error details: {error_details}")
                except:
                    self.logger.error(f"Error response: {e.response.text}")
            return None
    
    def deactivate_user(self, user_id: int) -> bool:
        """
        Deactivate a user.
        
        Args:
            user_id: ID of the user to deactivate
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Deactivating user with ID {user_id}")
            
            if self.dry_run:
                self.logger.info(f"DRY RUN: Would deactivate user {user_id}")
                return True
            
            # Check if the user is an agent or requester first
            user = self.get_user_by_id(user_id)
            if not user:
                self.logger.warning(f"User with ID {user_id} not found, cannot deactivate")
                return False
                
            is_agent = user.get("is_agent", False)
            endpoint = "agents" if is_agent else "requesters"
            
            # Make the API request to deactivate the user
            # According to the docs, this should return 204 No Content if successful
            success = self.api_client.delete(
                f"{endpoint}/{user_id}",
                workspace_id=self.workspace_id,
                expect_no_content=True  # Expect 204 No Content response
            )
            
            # Check if the operation was successful
            if success:
                self.logger.info(f"Successfully deactivated user {user_id}")
                
                # Update the cached user if in recent users
                for i, user in enumerate(self.recent_users):
                    if user.get("id") == user_id:
                        self.recent_users[i]["active"] = False
                        break
                
                return True
            else:
                self.logger.warning(f"Failed to deactivate user {user_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error deactivating user {user_id}: {str(e)}")
            return False
    
    def forget_user(self, user_id: int) -> bool:
        """
        Permanently delete a requester and the tickets that they requested.
        
        Args:
            user_id: ID of the requester to permanently delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Permanently deleting requester with ID {user_id}")
            
            if self.dry_run:
                self.logger.info(f"DRY RUN: Would permanently delete requester {user_id}")
                return True
            
            # Check if the user is a requester
            user = self.get_user_by_id(user_id)
            if not user:
                self.logger.warning(f"User with ID {user_id} not found, cannot forget")
                return False
                
            if user.get("is_agent", False):
                self.logger.warning(f"User with ID {user_id} is an agent, cannot forget (only requesters can be forgotten)")
                return False
            
            # Make the API request to permanently delete the requester
            # According to the docs, this should return 204 No Content if successful
            success = self.api_client.delete(
                f"requesters/{user_id}/forget",
                workspace_id=self.workspace_id,
                expect_no_content=True  # Expect 204 No Content response
            )
            
            # Check if the operation was successful
            if success:
                self.logger.info(f"Successfully forgot (permanently deleted) requester {user_id}")
                
                # Remove the user from recent users if present
                self.recent_users = [u for u in self.recent_users if u.get("id") != user_id]
                
                return True
            else:
                self.logger.warning(f"Failed to forget (permanently delete) requester {user_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error forgetting (permanently deleting) requester {user_id}: {str(e)}")
            return False
    
    def activate_user(self, user_id: int) -> bool:
        """
        Activate a previously deactivated user.
        
        Args:
            user_id: ID of the user to activate
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Activating user with ID {user_id}")
            
            if self.dry_run:
                self.logger.info(f"DRY RUN: Would activate user {user_id}")
                return True
            
            # Check if the user is an agent or requester first
            user = self.get_user_by_id(user_id)
            if not user:
                self.logger.warning(f"User with ID {user_id} not found, cannot activate")
                return False
                
            is_agent = user.get("is_agent", False)
            endpoint = "agents" if is_agent else "requesters"
            
            # Make the API request to activate the user
            response = self.api_client.put(
                f"{endpoint}/{user_id}/reactivate",
                data={},  # Empty data for reactivation
                workspace_id=self.workspace_id
            )
            
            # Check if the operation was successful
            if response and not response.get("error"):
                self.logger.info(f"Successfully activated user {user_id}")
                
                # Update the cached user if in recent users
                for i, user in enumerate(self.recent_users):
                    if user.get("id") == user_id:
                        self.recent_users[i]["active"] = True
                        break
                
                return True
            else:
                self.logger.warning(f"Failed to activate user {user_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error activating user {user_id}: {str(e)}")
            return False
    
    def get_user_groups(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all groups that a user belongs to.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of group dictionaries
        """
        try:
            self.logger.info(f"Fetching groups for user {user_id}")
            
            # Make the API request to get user groups
            response = self.api_client.get(
                f"users/{user_id}/groups",
                workspace_id=self.workspace_id
            )
            
            groups = response.get("groups", [])
            self.logger.info(f"Found {len(groups)} groups for user {user_id}")
            
            return groups
                
        except Exception as e:
            self.logger.error(f"Error fetching groups for user {user_id}: {str(e)}")
            return []
    
    def add_user_to_group(self, user_id: int, group_id: int) -> bool:
        """
        Add a user to a group.
        
        Args:
            user_id: ID of the user
            group_id: ID of the group
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Adding user {user_id} to group {group_id}")
            
            if self.dry_run:
                self.logger.info(f"DRY RUN: Would add user {user_id} to group {group_id}")
                return True
            
            # Make the API request to add user to group
            response = self.api_client.post(
                f"users/{user_id}/groups",
                data={"group_ids": [group_id]},
                workspace_id=self.workspace_id
            )
            
            # Check if the operation was successful
            if response and response.get("success", False):
                self.logger.info(f"Successfully added user {user_id} to group {group_id}")
                return True
            else:
                self.logger.warning(f"Failed to add user {user_id} to group {group_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error adding user {user_id} to group {group_id}: {str(e)}")
            return False
    
    def remove_user_from_group(self, user_id: int, group_id: int) -> bool:
        """
        Remove a user from a group.
        
        Args:
            user_id: ID of the user
            group_id: ID of the group
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Removing user {user_id} from group {group_id}")
            
            if self.dry_run:
                self.logger.info(f"DRY RUN: Would remove user {user_id} from group {group_id}")
                return True
            
            # Make the API request to remove user from group
            response = self.api_client.delete(
                f"users/{user_id}/groups/{group_id}",
                workspace_id=self.workspace_id
            )
            
            # Check if the operation was successful
            if response and response.get("success", False):
                self.logger.info(f"Successfully removed user {user_id} from group {group_id}")
                return True
            else:
                self.logger.warning(f"Failed to remove user {user_id} from group {group_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error removing user {user_id} from group {group_id}: {str(e)}")
            return False
    
    def force_password_reset(self, user_id: int) -> bool:
        """
        Force a password reset for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Forcing password reset for user {user_id}")
            
            if self.dry_run:
                self.logger.info(f"DRY RUN: Would force password reset for user {user_id}")
                return True
            
            # Make the API request to force password reset
            response = self.api_client.post(
                f"users/{user_id}/force_password_reset",
                data={},
                workspace_id=self.workspace_id
            )
            
            # Check if the operation was successful
            if response and response.get("success", False):
                self.logger.info(f"Successfully forced password reset for user {user_id}")
                return True
            else:
                self.logger.warning(f"Failed to force password reset for user {user_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error forcing password reset for user {user_id}: {str(e)}")
            return False
    
    def get_recent_users(self) -> List[Dict[str, Any]]:
        """
        Get recently accessed users.
        
        Returns:
            List of recent user dictionaries
        """
        return self.recent_users.copy()
    
    def get_inactive_users(self, days_threshold: int = 90) -> List[Dict[str, Any]]:
        """
        Get users who have been inactive for a specified number of days.
        
        Args:
            days_threshold: Number of days to consider as inactive threshold
            
        Returns:
            List of inactive user dictionaries
        """
        # This method would require additional API calls or data analysis
        # that would depend on the FreshService API capabilities
        # Placeholder for future implementation
        self.logger.warning("get_inactive_users method not fully implemented")
        return []
    
    def _add_to_recent_users(self, user: Dict[str, Any]) -> None:
        """
        Add a user to the recent users cache.
        
        Args:
            user: User dictionary to add
        """
        # Remove the user if already in the list
        self.recent_users = [u for u in self.recent_users if u.get("id") != user.get("id")]
        
        # Add the user to the beginning of the list
        self.recent_users.insert(0, user)
        
        # Trim the list if it exceeds the maximum size
        if len(self.recent_users) > self.max_recent_users:
            self.recent_users = self.recent_users[:self.max_recent_users]
    
    def _is_valid_email(self, email: str) -> bool:
        """
        Validate email format.
        
        Args:
            email: Email string to validate
            
        Returns:
            True if valid, False otherwise
        """
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email))
    
    def get_all_agents(self) -> List[Dict[str, Any]]:
        """
        Get all agents from FreshService API.
        
        Returns:
            List of all agents in the system
        """
        self.logger.info("Getting all agents")
        
        try:
            agents = []
            page = 1
            per_page = 100  # Maximum allowed by API
            
            while True:
                self.logger.debug(f"Fetching agents page {page}")
                
                try:
                    # Get page of agents
                    response = self.api_client.get(
                        "agents",
                        params={"per_page": per_page, "page": page},
                        workspace_id=self.workspace_id
                    )
                    
                    if not isinstance(response, dict) or 'agents' not in response:
                        self.logger.warning(f"Unexpected response format from agents endpoint: {response}")
                        break
                        
                    batch = response.get('agents', [])
                    
                    if not batch:
                        # No more agents to retrieve
                        break
                        
                    agents.extend(batch)
                    
                    # Check if there are more pages
                    if len(batch) < per_page:
                        # If we got fewer items than requested, this must be the last page
                        break
                        
                    page += 1
                except Exception as e:
                    self.logger.error(f"Error retrieving agents page {page}: {str(e)}")
                    break
            
            self.logger.info(f"Retrieved {len(agents)} agents")
            return agents
            
        except Exception as e:
            self.logger.error(f"Error retrieving all agents: {str(e)}")
            return [] 