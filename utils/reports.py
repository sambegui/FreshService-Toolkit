#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FreshService Reports Module

Handles reporting functionalities including user activity tracking
through ticket interactions.
"""

import os
import csv
import logging
import datetime
import time
from typing import Dict, List, Optional, Any, Tuple

class ReportsManager:
    """
    Manages report generation for FreshService data.
    """
    
    def __init__(self, api_client, workspace_id, logger=None):
        """
        Initialize the ReportsManager.
        
        Args:
            api_client: FreshServiceAPI client instance
            workspace_id: Current workspace ID
            logger: Logger instance
        """
        self.api_client = api_client
        self.workspace_id = workspace_id
        self.logger = logger or logging.getLogger(__name__)
    
    def get_user_ticket_activity(self, user_id=None, email=None, start_date=None, end_date=None, limit=50) -> List[Dict]:
        """
        Get ticket activity for a specific user.
        
        Args:
            user_id: User ID to filter by
            email: User email to filter by (alternative to user_id)
            start_date: Start date for ticket activity (ISO format: YYYY-MM-DDT00:00:00Z)
            end_date: End date for ticket activity (ISO format: YYYY-MM-DDT00:00:00Z)
            limit: Maximum number of tickets to return
            
        Returns:
            List of ticket activity data
        """
        self.logger.info(f"Getting ticket activity for user_id={user_id}, email={email}")
        
        # Build query parameters
        params = {'per_page': min(limit, 100)}  # API max is 100 per page
        
        if user_id:
            params['requester_id'] = user_id
        elif email:
            params['email'] = email
        else:
            self.logger.error("Either user_id or email must be provided")
            return []
            
        if start_date:
            params['updated_since'] = start_date
        
        # Add workspace filter parameter if we have one
        if self.workspace_id:
            params['workspace_id'] = self.workspace_id
            
        # Get tickets - use base endpoint without workspace prefix
        try:
            result = self.api_client._make_request(
                'GET', 
                'tickets', 
                params=params,
                workspace_id=None  # Don't use workspace prefix for tickets endpoint
            )
            
            if isinstance(result, dict) and 'tickets' in result:
                tickets = result.get('tickets', [])
                self.logger.info(f"Found {len(tickets)} tickets for user")
                return tickets
            else:
                self.logger.error(f"Unexpected API response format: {result}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error getting tickets: {str(e)}")
            return []
    
    def get_ticket_conversations(self, ticket_id: int) -> List[Dict]:
        """
        Get conversations for a specific ticket.
        
        Args:
            ticket_id: Ticket ID
            
        Returns:
            List of conversation data
        """
        self.logger.info(f"Getting conversations for ticket {ticket_id}")
        
        try:
            result = self.api_client._make_request(
                'GET', 
                f'tickets/{ticket_id}', 
                params={'include': 'conversations'},
                workspace_id=None  # Don't use workspace prefix for tickets endpoint
            )
            
            if isinstance(result, dict) and 'ticket' in result:
                ticket = result.get('ticket', {})
                conversations = ticket.get('conversations', [])
                self.logger.info(f"Found {len(conversations)} conversations for ticket {ticket_id}")
                return conversations
            else:
                self.logger.error(f"Unexpected API response format: {result}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error getting ticket conversations: {str(e)}")
            return []
    
    def get_user_activity_report(self, user_id=None, email=None, days=30) -> Tuple[List[Dict], Dict]:
        """
        Generate a comprehensive user activity report.
        
        Args:
            user_id: User ID to report on
            email: User email to report on (alternative to user_id)
            days: Number of days to look back
            
        Returns:
            Tuple of (activity_items, summary)
        """
        # Calculate date range
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=days)
        start_date_str = start_date.strftime("%Y-%m-%dT00:00:00Z")
        
        # Get ticket data
        tickets = self.get_user_ticket_activity(
            user_id=user_id,
            email=email,
            start_date=start_date_str,
            limit=100
        )
        
        activity_items = []
        
        # Process each ticket
        for ticket in tickets:
            ticket_id = ticket.get('id')
            
            # Basic ticket information
            activity_item = {
                'ticket_id': ticket_id,
                'subject': ticket.get('subject', 'No subject'),
                'status': ticket.get('status', 'Unknown'),
                'priority': ticket.get('priority', 'Unknown'),
                'created_at': ticket.get('created_at'),
                'updated_at': ticket.get('updated_at'),
                'type': 'ticket'
            }
            activity_items.append(activity_item)
            
            # Get conversations if available
            try:
                conversations = self.get_ticket_conversations(ticket_id)
                
                # Add each conversation as an activity item
                for conv in conversations:
                    activity_items.append({
                        'ticket_id': ticket_id,
                        'conversation_id': conv.get('id'),
                        'body': conv.get('body', 'No content'),
                        'created_at': conv.get('created_at'),
                        'updated_at': conv.get('updated_at'),
                        'user_id': conv.get('user_id'),
                        'type': 'conversation'
                    })
            except Exception as e:
                self.logger.error(f"Error processing conversations for ticket {ticket_id}: {str(e)}")
        
        # Sort by date (newest first)
        activity_items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # Generate summary
        summary = {
            'total_tickets': len(tickets),
            'date_range': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            'total_conversations': len([i for i in activity_items if i.get('type') == 'conversation']),
        }
        
        return activity_items, summary
        
    def get_activity_visualization(self, activity_items, use_simple_chars=False):
        """
        Create a simple ASCII visualization of activity distribution.
        
        Args:
            activity_items: List of activity items
            use_simple_chars: Whether to use simple ASCII chars (for CSV export)
            
        Returns:
            List of strings with visualization data
        """
        if not activity_items:
            return ["No data available for visualization"]
            
        # Extract dates and group by day of week
        day_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}  # Monday to Sunday
        day_names = {
            0: "Monday   ",
            1: "Tuesday  ",
            2: "Wednesday",
            3: "Thursday ",
            4: "Friday   ",
            5: "Saturday ",
            6: "Sunday   "
        }
        
        for item in activity_items:
            date_str = item.get('created_at', '')
            if date_str:
                try:
                    date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
                    # Get day of week (0 = Monday, 6 = Sunday)
                    day_of_week = date_obj.weekday()
                    day_counts[day_of_week] += 1
                except Exception:
                    continue
        
        # Create visualization
        result = ["", "Activity Distribution by Day of Week:", ""]
        
        # Find max for scaling
        max_count = max(day_counts.values()) if day_counts.values() else 0
        scale_factor = 40 / max_count if max_count > 0 else 0
        
        # Generate bars - use simpler chars for CSV export
        for day in range(7):
            count = day_counts[day]
            bar_length = int(count * scale_factor) if count > 0 else 0
            
            # For CSV export, just show the count in parentheses
            if use_simple_chars:
                result.append(f"{day_names[day]}: ({count})")
            else:
                bar = "█" * bar_length
                result.append(f"{day_names[day]}: {bar} ({count})")
        
        return result
        
    def export_activity_report_to_csv(self, activity_items, summary, output_path):
        """
        Export activity report to CSV.
        
        Args:
            activity_items: List of activity items
            summary: Summary dictionary
            output_path: Output file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Status and priority mapping for human-readable values
            status_map = {
                1: "Open",
                2: "Pending",
                3: "Resolved",
                4: "Closed", 
                5: "New",
                6: "In Progress",
                7: "On Hold"
            }
            
            priority_map = {
                1: "Low",
                2: "Medium",
                3: "High",
                4: "Urgent"
            }
            
            # Prepare data for CSV
            csv_data = []
            
            # Add summary as header rows
            csv_data.append(['User Activity Report'])
            csv_data.append(['Date Range', summary.get('date_range')])
            csv_data.append(['Total Tickets', str(summary.get('total_tickets', 0))])
            csv_data.append(['Total Conversations', str(summary.get('total_conversations', 0))])
            csv_data.append([])  # Empty row
            
            # Add visualization with simple chars for CSV
            visualization = self.get_activity_visualization(activity_items, use_simple_chars=True)
            for line in visualization:
                csv_data.append([line])
            
            csv_data.append([])  # Empty row
            
            # Add column headers - improved headers
            headers = [
                'Date', 
                'Type', 
                'Ticket ID', 
                'Subject/Content', 
                'Status',
                'Priority',
                'Last Updated'
            ]
            csv_data.append(headers)
            
            # Add data rows
            for item in activity_items:
                # Format the date
                created_date = self._format_date(item.get('created_at', ''))
                updated_date = self._format_date(item.get('updated_at', ''))
                
                if item.get('type') == 'ticket':
                    # Convert numeric status and priority to readable text
                    status_val = item.get('status')
                    status_text = status_map.get(status_val, f"Status {status_val}")
                    
                    priority_val = item.get('priority')
                    priority_text = priority_map.get(priority_val, f"Priority {priority_val}")
                    
                    csv_data.append([
                        created_date,
                        'Ticket',
                        str(item.get('ticket_id', '')),
                        item.get('subject', ''),
                        status_text,
                        priority_text,
                        updated_date
                    ])
                elif item.get('type') == 'conversation':
                    # Clean the HTML content
                    body = self._clean_html(item.get('body', ''))
                    
                    # Truncate long content
                    if len(body) > 100:
                        body = body[:97] + '...'
                        
                    csv_data.append([
                        created_date,
                        'Response',
                        str(item.get('ticket_id', '')),
                        body,
                        '', # No status for conversations
                        '',  # No priority for conversations
                        updated_date
                    ])
            
            # Write to CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerows(csv_data)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting activity report to CSV: {str(e)}")
            return False
    
    def _clean_html(self, html_content):
        """
        Remove HTML tags from content and clean up formatting.
        
        Args:
            html_content: HTML content to clean
            
        Returns:
            Cleaned text
        """
        if not html_content:
            return ""
            
        try:
            import re
            
            # Replace common HTML entities
            replacements = {
                '&nbsp;': ' ',
                '&amp;': '&',
                '&lt;': '<',
                '&gt;': '>',
                '&quot;': '"',
                '&apos;': "'",
                '&#39;': "'",
                '&ndash;': '-',
                '&mdash;': '--',
                '<br>': ' ',
                '<br/>': ' ',
                '<br />': ' ',
                '</div>': ' ',
                '</p>': ' '
            }
            
            # Apply replacements
            for old, new in replacements.items():
                html_content = html_content.replace(old, new)
            
            # First handle line breaks to preserve some formatting
            html_content = re.sub(r'<(div|p)[^>]*>', ' ', html_content, flags=re.IGNORECASE)
            
            # Remove all remaining HTML tags
            clean_text = re.sub(r'<[^>]+>', ' ', html_content)
            
            # Fix excess whitespace
            clean_text = re.sub(r'\s+', ' ', clean_text)
            
            # Remove leading/trailing whitespace
            clean_text = clean_text.strip()
            
            return clean_text
        except Exception as e:
            self.logger.error(f"Error cleaning HTML: {str(e)}")
            # If there's an error cleaning, return a truncated version of the original
            return html_content[:100] + '...' if len(html_content) > 100 else html_content
    
    def _format_date(self, date_str):
        """
        Format ISO date string to a more readable format.
        
        Args:
            date_str: ISO format date string (YYYY-MM-DDTHH:MM:SSZ)
            
        Returns:
            Formatted date string (YYYY-MM-DD HH:MM)
        """
        if not date_str:
            return ""
            
        try:
            # Parse ISO format
            date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
            # Return formatted date
            return date_obj.strftime("%Y-%m-%d %H:%M")
        except Exception:
            # If parsing fails, return original
            return date_str 

    def is_agent(self, user_id):
        """
        Check if a user is also an agent in FreshService.
        
        Args:
            user_id: User ID to check
            
        Returns:
            Boolean indicating if user is an agent
        """
        self.logger.info(f"Checking if user {user_id} is an agent")
        
        try:
            # Try to retrieve the agent record
            result = self.api_client._make_request(
                'GET',
                f'agents/{user_id}',
                workspace_id=None  # Don't use workspace prefix for agents endpoint
            )
            
            # If we get a valid response, the user is an agent
            is_agent = isinstance(result, dict) and 'agent' in result
            self.logger.info(f"User {user_id} is {'' if is_agent else 'not '}an agent")
            return is_agent
            
        except Exception as e:
            self.logger.error(f"Error checking if user is agent: {str(e)}")
            return False
    
    def get_agent_ticket_interactions(self, agent_id, start_date=None, limit=100):
        """
        Get tickets where the agent has interacted (responded or updated).
        
        Args:
            agent_id: Agent ID to check
            start_date: Start date for ticket activity (ISO format)
            limit: Maximum number of tickets to return
            
        Returns:
            List of tickets the agent has interacted with
        """
        self.logger.info(f"Getting ticket interactions for agent_id={agent_id}")
        
        # We will combine results from different queries
        all_agent_tickets = []
        
        # Try multiple approaches to find agent tickets, with fallbacks
        approaches = [
            self._get_agent_tickets_by_responder_id,
            self._get_agent_tickets_by_filter,
            self._get_agent_tickets_by_scanning
        ]
        
        for approach_index, approach_method in enumerate(approaches):
            if all_agent_tickets:
                self.logger.info(f"Already found {len(all_agent_tickets)} tickets, skipping additional approaches")
                break
                
            try:
                self.logger.info(f"Trying approach #{approach_index+1} to find agent tickets")
                tickets = approach_method(agent_id, start_date, limit)
                if tickets:
                    all_agent_tickets.extend(tickets)
                    self.logger.info(f"Found {len(tickets)} tickets using approach #{approach_index+1}")
            except Exception as e:
                self.logger.error(f"Error with approach #{approach_index+1}: {str(e)}")
                # Continue to next approach
        
        return all_agent_tickets
    
    def _get_agent_tickets_by_responder_id(self, agent_id, start_date=None, limit=100):
        """Approach 1: Try to get tickets based on agent assignment using supported methods"""
        self.logger.info(f"Searching for tickets assigned to agent {agent_id} using supported parameters")
        
        # For this method, we won't use responder_id directly since it's not supported
        # Instead, we'll use other supported parameters and filter locally
        params = {
            'per_page': min(limit, 100),
            # Avoid using responder_id parameter directly - it's not supported
        }
        
        if start_date:
            params['updated_since'] = start_date
            
        if self.workspace_id:
            params['workspace_id'] = self.workspace_id
        
        result = self.api_client._make_request(
            'GET', 
            'tickets', 
            params=params,
            workspace_id=None
        )
        
        if not isinstance(result, dict) or 'tickets' not in result:
            return []
            
        # Filter tickets locally to find ones where the agent is responder
        agent_tickets = []
        tickets = result.get('tickets', [])
        self.logger.info(f"Filtering {len(tickets)} tickets for agent {agent_id} assignment")
        
        for ticket in tickets:
            responder_id = ticket.get('responder_id')
            if responder_id and str(responder_id) == str(agent_id):
                agent_tickets.append(ticket)
        
        self.logger.info(f"Found {len(agent_tickets)} tickets assigned to agent {agent_id}")
        return agent_tickets
    
    def _get_agent_tickets_by_filter(self, agent_id, start_date=None, limit=100):
        """Approach 2: Try using standard filter parameters"""
        self.logger.info(f"Searching for tickets with agent {agent_id} using standard filters")
        
        # Try using the watching filter which might show tickets the agent is involved with
        filter_params = {
            'per_page': min(limit, 100),
            'filter': 'watching',  # This is a supported filter value
        }
        
        if start_date:
            filter_params['updated_since'] = start_date
            
        if self.workspace_id:
            filter_params['workspace_id'] = self.workspace_id
        
        result = self.api_client._make_request(
            'GET', 
            'tickets', 
            params=filter_params,
            workspace_id=None
        )
        
        if not isinstance(result, dict) or 'tickets' not in result:
            return []
            
        tickets = result.get('tickets', [])
        
        # Still need to filter locally to verify this agent is involved
        agent_tickets = []
        for ticket in tickets:
            # Check if agent is the responder
            if ticket.get('responder_id') and str(ticket.get('responder_id')) == str(agent_id):
                agent_tickets.append(ticket)
                continue
            
            # Otherwise, we'll need to check ticket conversations in the next method
                
        self.logger.info(f"Found {len(agent_tickets)} tickets with agent {agent_id} through standard filters")
        return agent_tickets
    
    def _get_agent_tickets_by_scanning(self, agent_id, start_date=None, limit=100):
        """Approach 3: Get all recent tickets and filter locally"""
        self.logger.info(f"Scanning recent tickets for agent {agent_id}")
        
        # Get a sample of recent tickets without filtering
        recent_params = {
            'per_page': min(limit, 100),
            'order_by': 'updated_at',
            'order_type': 'desc'  # Most recently updated first
        }
        
        if start_date:
            recent_params['updated_since'] = start_date
        
        if self.workspace_id:
            recent_params['workspace_id'] = self.workspace_id
        
        # Try to get tickets
        try:
            result = self.api_client._make_request(
                'GET', 
                'tickets', 
                params=recent_params,
                workspace_id=None
            )
            
            if not isinstance(result, dict) or 'tickets' not in result:
                self.logger.warning("No tickets found or unexpected response format")
                return []
                
            recent_tickets = result.get('tickets', [])
            self.logger.info(f"Checking {len(recent_tickets)} recent tickets for agent assignment")
            
            # Local filtering to find tickets where agent is assigned
            agent_tickets = []
            
            # Track errors to avoid excessive logging
            conversation_errors = 0
            max_conversation_errors = 3  # Only log first few errors
            
            for ticket in recent_tickets:
                responder_id = ticket.get('responder_id')
                if responder_id and str(responder_id) == str(agent_id):
                    agent_tickets.append(ticket)
                    continue
                    
                # If we didn't find the agent as responder, check conversations
                try:
                    ticket_id = ticket.get('id')
                    conversations = self.get_ticket_conversations(ticket_id)
                    if any(conv.get('user_id') == agent_id for conv in conversations):
                        agent_tickets.append(ticket)
                except Exception as e:
                    conversation_errors += 1
                    if conversation_errors <= max_conversation_errors:
                        self.logger.error(f"Error checking conversations for ticket {ticket.get('id')}: {str(e)}")
                    elif conversation_errors == max_conversation_errors + 1:
                        self.logger.error(f"Additional conversation errors suppressed to avoid log spam")
            
            self.logger.info(f"Found {len(agent_tickets)} tickets with agent involvement through scanning")
            return agent_tickets
            
        except Exception as e:
            self.logger.error(f"Error scanning tickets: {str(e)}")
            # Return empty list on error instead of raising exception
            return []
    
    def get_agent_activity_report(self, agent_id, days=30):
        """
        Generate an agent activity report showing tickets they worked on.
        
        Args:
            agent_id: Agent ID to report on
            days: Number of days to look back
            
        Returns:
            Tuple of (activity_items, summary)
        """
        self.logger.info(f"Generating agent activity report for agent_id={agent_id}")
        
        # Calculate date range
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=days)
        start_date_str = start_date.strftime("%Y-%m-%dT00:00:00Z")
        
        # Get tickets the agent has interacted with
        agent_tickets = self.get_agent_ticket_interactions(
            agent_id=agent_id,
            start_date=start_date_str,
            limit=100
        )
        
        activity_items = []
        
        # Process each ticket
        for ticket in agent_tickets:
            ticket_id = ticket.get('id')
            
            # Add ticket as an activity item with agent role
            activity_item = {
                'ticket_id': ticket_id,
                'subject': ticket.get('subject', 'No subject'),
                'status': ticket.get('status', 'Unknown'),
                'priority': ticket.get('priority', 'Unknown'),
                'created_at': ticket.get('created_at'),
                'updated_at': ticket.get('updated_at'),
                'type': 'ticket',
                'role': 'agent',
                'agent_role': 'Assigned' if ticket.get('responder_id') == agent_id else 'Collaborator'
            }
            activity_items.append(activity_item)
            
            # Get conversations to find agent responses
            try:
                conversations = self.get_ticket_conversations(ticket_id)
                
                # Add each agent response as an activity item
                for conv in conversations:
                    if conv.get('user_id') == agent_id:
                        activity_items.append({
                            'ticket_id': ticket_id,
                            'conversation_id': conv.get('id'),
                            'body': conv.get('body', 'No content'),
                            'created_at': conv.get('created_at'),
                            'updated_at': conv.get('updated_at'),
                            'user_id': conv.get('user_id'),
                            'type': 'conversation',
                            'role': 'agent',
                            'conversation_type': conv.get('private', False) and 'Private Note' or 'Public Reply'
                        })
            except Exception as e:
                self.logger.error(f"Error processing agent conversations for ticket {ticket_id}: {str(e)}")
        
        # Sort by date (newest first)
        activity_items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # Generate summary
        summary = {
            'total_tickets': len(agent_tickets),
            'date_range': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            'total_responses': len([i for i in activity_items if i.get('type') == 'conversation']),
            'assigned_tickets': len([i for i in activity_items if i.get('type') == 'ticket' and i.get('agent_role') == 'Assigned']),
            'collaborated_tickets': len([i for i in activity_items if i.get('type') == 'ticket' and i.get('agent_role') == 'Collaborator'])
        }
        
        return activity_items, summary
    
    def get_comprehensive_user_activity(self, user_id=None, email=None, days=30):
        """
        Generate a comprehensive activity report that includes both requester and agent activity if applicable.
        
        Args:
            user_id: User ID to report on
            email: User email to report on (alternative to user_id)
            days: Number of days to look back
            
        Returns:
            Tuple of (activity_items, summary, is_agent)
        """
        # Get requester activity (tickets created by the user)
        requester_items, requester_summary = self.get_user_activity_report(
            user_id=user_id,
            email=email,
            days=days
        )
        
        # Check if user is an agent
        is_agent = False
        agent_items = []
        agent_summary = {}
        agent_error = None
        agent_activity_attempted = False
        
        if user_id:
            try:
                is_agent = self.is_agent(user_id)
                
                if is_agent:
                    agent_activity_attempted = True
                    self.logger.info(f"User {user_id} is an agent, attempting to retrieve agent activity")
                    # Get agent activity (tickets worked on by the user)
                    try:
                        agent_items, agent_summary = self.get_agent_activity_report(
                            agent_id=user_id,
                            days=days
                        )
                    except Exception as e:
                        # Provide detailed error info
                        agent_error = str(e)
                        error_type = type(e).__name__
                        self.logger.error(f"Failed to retrieve agent activity: {error_type}: {agent_error}")
                        
                        # Don't propagate the error - we'll return partial results
                        is_agent = True  # Still indicate that the user is an agent
                        agent_items = []
                        agent_summary = {
                            'total_tickets': 0,
                            'total_responses': 0,
                            'assigned_tickets': 0,
                            'collaborated_tickets': 0,
                            'error': agent_error,
                            'error_type': error_type
                        }
            except Exception as e:
                error_type = type(e).__name__
                self.logger.error(f"Error checking if user is agent: {error_type}: {str(e)}")
                # Continue with just requester activity
        
        # Combine activities
        all_items = requester_items.copy()
        
        # Add agent items avoiding duplicates (same ticket might appear in both lists)
        ticket_ids_seen = set(item.get('ticket_id') for item in all_items if item.get('type') == 'ticket')
        conversation_ids_seen = set(item.get('conversation_id') for item in all_items if item.get('type') == 'conversation' and 'conversation_id' in item)
        
        for item in agent_items:
            if item.get('type') == 'ticket':
                ticket_id = item.get('ticket_id')
                if ticket_id not in ticket_ids_seen:
                    all_items.append(item)
                    ticket_ids_seen.add(ticket_id)
            elif item.get('type') == 'conversation':
                conversation_id = item.get('conversation_id')
                if conversation_id not in conversation_ids_seen:
                    all_items.append(item)
                    conversation_ids_seen.add(conversation_id)
        
        # Sort combined list by date
        all_items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # Create combined summary
        combined_summary = {
            'total_tickets_created': requester_summary.get('total_tickets', 0),
            'total_tickets_worked': agent_summary.get('total_tickets', 0) if is_agent else 0,
            'total_conversations_as_requester': requester_summary.get('total_conversations', 0),
            'total_responses_as_agent': agent_summary.get('total_responses', 0) if is_agent else 0,
            'tickets_assigned': agent_summary.get('assigned_tickets', 0) if is_agent else 0,
            'tickets_collaborated': agent_summary.get('collaborated_tickets', 0) if is_agent else 0,
            'date_range': requester_summary.get('date_range', ''),
            'is_agent': is_agent,
            'agent_activity_attempted': agent_activity_attempted
        }
        
        # Add error information if applicable
        if agent_error:
            combined_summary['agent_error'] = agent_error
            combined_summary['agent_error_type'] = agent_summary.get('error_type', 'Unknown')
            combined_summary['agent_activity_available'] = False
        elif is_agent:
            combined_summary['agent_activity_available'] = True
        
        return all_items, combined_summary, is_agent
        
    def export_comprehensive_activity_to_csv(self, activity_items, summary, output_path):
        """
        Export comprehensive activity report to CSV, including both requester and agent activity.
        
        Args:
            activity_items: List of activity items
            summary: Summary dictionary
            output_path: Output file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Status and priority mapping for human-readable values
            status_map = {
                1: "Open",
                2: "Pending",
                3: "Resolved",
                4: "Closed", 
                5: "New",
                6: "In Progress",
                7: "On Hold"
            }
            
            priority_map = {
                1: "Low",
                2: "Medium",
                3: "High",
                4: "Urgent"
            }
            
            # Prepare data for CSV
            csv_data = []
            
            # Add summary as header rows
            csv_data.append(['User Activity Report'])
            csv_data.append(['Date Range', summary.get('date_range', '')])
            csv_data.append(['Is Agent', 'Yes' if summary.get('is_agent', False) else 'No'])
            csv_data.append(['Total Tickets Created', str(summary.get('total_tickets_created', 0))])
            
            # Include agent summary if applicable
            if summary.get('is_agent', False):
                csv_data.append(['Total Tickets Worked On', str(summary.get('total_tickets_worked', 0))])
                csv_data.append(['Tickets Assigned', str(summary.get('tickets_assigned', 0))])
                csv_data.append(['Tickets Collaborated On', str(summary.get('tickets_collaborated', 0))])
                csv_data.append(['Total Responses as Agent', str(summary.get('total_responses_as_agent', 0))])
            
            csv_data.append(['Total Conversations as Requester', str(summary.get('total_conversations_as_requester', 0))])
            csv_data.append([])  # Empty row
            
            # Add visualization with simple chars for CSV
            visualization = self.get_activity_visualization(activity_items, use_simple_chars=True)
            for line in visualization:
                csv_data.append([line])
            
            csv_data.append([])  # Empty row
            
            # Add column headers - improved headers with role
            headers = [
                'Date', 
                'Type', 
                'Role',
                'Ticket ID', 
                'Subject/Content', 
                'Status',
                'Priority',
                'Last Updated',
                'Notes'
            ]
            csv_data.append(headers)
            
            # Add data rows
            for item in activity_items:
                # Format the date
                created_date = self._format_date(item.get('created_at', ''))
                updated_date = self._format_date(item.get('updated_at', ''))
                role = item.get('role', 'requester')
                
                if item.get('type') == 'ticket':
                    # Convert numeric status and priority to readable text
                    status_val = item.get('status')
                    status_text = status_map.get(status_val, f"Status {status_val}")
                    
                    priority_val = item.get('priority')
                    priority_text = priority_map.get(priority_val, f"Priority {priority_val}")
                    
                    notes = ""
                    if role == 'agent':
                        notes = item.get('agent_role', '')
                    
                    csv_data.append([
                        created_date,
                        'Ticket',
                        role.capitalize(),
                        str(item.get('ticket_id', '')),
                        item.get('subject', ''),
                        status_text,
                        priority_text,
                        updated_date,
                        notes
                    ])
                elif item.get('type') == 'conversation':
                    # Clean the HTML content
                    body = self._clean_html(item.get('body', ''))
                    
                    # Truncate long content
                    if len(body) > 100:
                        body = body[:97] + '...'
                    
                    notes = ""
                    if role == 'agent':
                        notes = item.get('conversation_type', '')
                        
                    csv_data.append([
                        created_date,
                        'Response',
                        role.capitalize(),
                        str(item.get('ticket_id', '')),
                        body,
                        '', # No status for conversations
                        '',  # No priority for conversations
                        updated_date,
                        notes
                    ])
            
            # Write to CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerows(csv_data)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting comprehensive activity report to CSV: {str(e)}")
            return False
    
    def run_api_diagnostics(self, current_user_id=None):
        """
        Run diagnostic tests on API endpoints to verify connectivity and permissions.
        
        Args:
            current_user_id: ID of the current user to use for testing (if available)
            
        Returns:
            Dictionary of diagnostic results
        """
        diagnostics = {
            'timestamp': datetime.datetime.now().isoformat(),
            'endpoints': {},
            'summary': '',
            'status': 'unknown'
        }
        
        try:
            # Test basic tickets endpoint
            self.logger.info("Testing basic tickets endpoint")
            diagnostics['endpoints']['tickets'] = self._test_endpoint('tickets', {'per_page': 1})
            
            # Test agents endpoint
            self.logger.info("Testing agents endpoint")
            diagnostics['endpoints']['agents'] = self._test_endpoint('agents', {'per_page': 1})
            
            # Test tickets with supported parameters
            self.logger.info("Testing tickets with standard filters")
            diagnostics['endpoints']['tickets_standard_filter'] = self._test_endpoint(
                'tickets', 
                {'filter': 'watching', 'per_page': 1}  # This is a supported filter value
            )
            
            # Test tickets with a specific requester_id (which is supported)
            # Use the current user's ID if available, otherwise try ID 1
            requester_id = current_user_id or 1
            self.logger.info(f"Testing tickets with requester_id parameter using ID: {requester_id}")
            diagnostics['endpoints']['tickets_requester'] = self._test_endpoint(
                'tickets', 
                {'requester_id': requester_id, 'per_page': 1}
            )
            
            # Test ticket conversations
            self.logger.info("Testing ticket conversations endpoint")
            # First get a ticket ID
            ticket_id = None
            tickets_result = diagnostics['endpoints']['tickets'].get('response', {})
            if isinstance(tickets_result, dict) and 'tickets' in tickets_result and tickets_result['tickets']:
                ticket_id = tickets_result['tickets'][0].get('id')
                
            if ticket_id:
                diagnostics['endpoints']['ticket_conversations'] = self._test_endpoint(
                    f'tickets/{ticket_id}', 
                    {'include': 'conversations'}
                )
            else:
                diagnostics['endpoints']['ticket_conversations'] = {
                    'success': False,
                    'error': 'No ticket ID available for testing',
                    'status_code': None,
                    'response': None
                }
            
            # Calculate overall status
            success_count = sum(1 for result in diagnostics['endpoints'].values() 
                               if result and result.get('success', False))
            total_count = len(diagnostics['endpoints'])
            
            if success_count == total_count:
                diagnostics['status'] = 'healthy'
                diagnostics['summary'] = 'All API endpoints are accessible and functioning correctly.'
            elif success_count > 0:
                diagnostics['status'] = 'partial'
                diagnostics['summary'] = f'{success_count} of {total_count} endpoints are working. Some functionality may be limited.'
            else:
                diagnostics['status'] = 'failed'
                diagnostics['summary'] = 'All API endpoints failed. Check API key and permissions.'
            
            # Add a note about tested parameters
            diagnostics['tested_parameters'] = {
                'supported_filters': ['watching', 'new_and_my_open', 'spam', 'deleted', 'archived'],
                'supported_query_params': ['requester_id', 'updated_since', 'include'],
                'unsupported_params': ['responder_id', 'filter_with_custom_query']
            }
            
            self.logger.info(f"API diagnostics complete: {diagnostics['status']}")
            return diagnostics
            
        except Exception as e:
            self.logger.error(f"Error running API diagnostics: {str(e)}")
            diagnostics['status'] = 'error'
            diagnostics['summary'] = f'Error running diagnostics: {str(e)}'
            return diagnostics
    
    def _test_endpoint(self, endpoint, params=None):
        """
        Test an API endpoint for accessibility.
        
        Args:
            endpoint: API endpoint to test
            params: Optional query parameters
            
        Returns:
            Dictionary with test results
        """
        result = {
            'success': False,
            'error': None,
            'status_code': None,
            'response': None,
            'params': params  # Include the params used for reference
        }
        
        try:
            # Log what we're testing
            self.logger.info(f"Testing endpoint: {endpoint} with params: {params}")
            
            # Make the request
            response = self.api_client._make_request(
                'GET',
                endpoint,
                params=params,
                workspace_id=None,
                _diagnostic=True  # Flag this as a diagnostic request
            )
            
            # Check if the response is a diagnostics error response
            if isinstance(response, dict) and 'success' in response and not response['success']:
                # This is an error response from diagnostic mode
                result['error'] = response.get('error', 'Unknown error')
                result['status_code'] = response.get('status_code', 500)
                return result
                
            # Otherwise, it's a successful response
            result['success'] = True
            result['response'] = response
            result['status_code'] = 200  # Assuming success
            
            return result
            
        except Exception as e:
            # Get error details
            error_str = str(e)
            result['error'] = error_str
            
            # Try to extract status code if available
            try:
                if 'status code' in error_str.lower():
                    import re
                    status_match = re.search(r'(\d{3})', error_str)
                    if status_match:
                        result['status_code'] = int(status_match.group(1))
            except:
                pass
                
            return result 

    def get_inactive_users_report(self, threshold_days=90, include_agents=True, include_requesters=True, progress_callback=None, test_user_id=None):
        """
        Generate a report of inactive users who haven't logged in within the specified period.
        
        Args:
            threshold_days: Number of days since last login to consider a user inactive
            include_agents: Whether to include agents in the report
            include_requesters: Whether to include requesters in the report
            progress_callback: Optional callback function to report progress
            test_user_id: Optional user ID to use for API capability testing
            
        Returns:
            Tuple of (inactive_users_list, summary)
        """
        self.logger.info(f"Generating inactive users report with threshold of {threshold_days} days")
        inactive_users = []
        start_time = datetime.datetime.now()
        
        # Track statistics for the report
        stats = {
            'total_agents_checked': 0,
            'total_requesters_checked': 0,
            'inactive_agents': 0,
            'inactive_requesters': 0,
            'users_without_login_data': 0,
            'threshold_days': threshold_days
        }
        
        # Calculate the cutoff date for inactivity
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=threshold_days)
        cutoff_date_str = cutoff_date.strftime("%Y-%m-%dT00:00:00Z")
        
        # Flag to track if we're using fallback methods
        using_fallback_methods = False
        
        # Get and check agents
        if include_agents:
            try:
                if progress_callback:
                    progress_callback("Retrieving agent list...")
                    
                agents = self._get_all_agents()
                stats['total_agents_checked'] = len(agents)
                self.logger.info(f"Checking {len(agents)} agents for inactivity")
                
                if progress_callback:
                    progress_callback(f"Found {len(agents)} agents to check")
                
                # Check a sample agent to determine if we have access to audit logs
                if agents and not using_fallback_methods:
                    try:
                        # Use the provided test user ID if available, otherwise use the first agent
                        if test_user_id:
                            test_agent_id = test_user_id
                        else:
                            test_agent_id = agents[0].get('id')
                            
                        if progress_callback:
                            progress_callback(f"Testing API access capabilities with agent {test_agent_id}...")
                            
                        last_login = self._get_user_last_login(test_agent_id)
                        if last_login is None:
                            # Audit logs might not be available, use fallback methods
                            using_fallback_methods = True
                            if progress_callback:
                                progress_callback("Direct login data not available - using alternative activity tracking methods")
                                progress_callback("This may provide less accurate last activity dates")
                    except Exception as e:
                        self.logger.warning(f"Error checking API capabilities: {str(e)}")
                        using_fallback_methods = True
                        if progress_callback:
                            progress_callback("Encountered access restrictions - using alternative tracking methods")
                
                # Process agents in smaller batches to avoid overwhelming the API
                batch_size = 25
                total_batches = (len(agents) + batch_size - 1) // batch_size
                
                for batch_num, batch_start in enumerate(range(0, len(agents), batch_size), 1):
                    batch = agents[batch_start:batch_start + batch_size]
                    self.logger.info(f"Processing agent batch {batch_num}/{total_batches} ({len(batch)} agents)")
                    
                    if progress_callback:
                        progress_callback(f"Processing agent batch {batch_num}/{total_batches} ({len(batch)} agents)")
                    
                    for agent in batch:
                        # Skip processing if the agent was created after the cutoff date
                        # (they can't be inactive if they were just created)
                        created_at = agent.get('created_at')
                        try:
                            if created_at:
                                created_date = datetime.datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
                                if created_date > cutoff_date:
                                    self.logger.debug(f"Skipping recently created agent {agent.get('id')}")
                                    continue
                        except Exception:
                            pass
                            
                        last_login = self._get_user_last_login(agent.get('id'))
                        
                        # If there's no last login data, consider the user inactive
                        if not last_login:
                            stats['users_without_login_data'] += 1
                            inactive_users.append({
                                'id': agent.get('id'),
                                'first_name': agent.get('first_name', ''),
                                'last_name': agent.get('last_name', ''),
                                'email': agent.get('email'),
                                'last_login': None,
                                'days_inactive': 'Unknown',
                                'type': 'Agent',
                                'active': agent.get('active', False),
                                'created_at': agent.get('created_at')
                            })
                            stats['inactive_agents'] += 1
                            continue
                        
                        # Parse the last login date
                        try:
                            last_login_date = datetime.datetime.strptime(last_login, "%Y-%m-%dT%H:%M:%SZ")
                            days_inactive = (datetime.datetime.now() - last_login_date).days
                            
                            # Check if the user is inactive based on the threshold
                            if days_inactive > threshold_days:
                                inactive_users.append({
                                    'id': agent.get('id'),
                                    'first_name': agent.get('first_name', ''),
                                    'last_name': agent.get('last_name', ''),
                                    'email': agent.get('email'),
                                    'last_login': last_login,
                                    'days_inactive': days_inactive,
                                    'type': 'Agent',
                                    'active': agent.get('active', False),
                                    'created_at': agent.get('created_at')
                                })
                                stats['inactive_agents'] += 1
                        except Exception as e:
                            self.logger.error(f"Error parsing last login date for agent {agent.get('id')}: {str(e)}")
                            stats['users_without_login_data'] += 1
                    
                    # Add a small delay between batches to prevent rate limiting
                    if batch_num < total_batches:
                        time.sleep(2)
                        
                if progress_callback and stats['inactive_agents'] > 0:
                    progress_callback(f"Found {stats['inactive_agents']} inactive agents")
                    
            except Exception as e:
                self.logger.error(f"Error retrieving agents: {str(e)}")
                if progress_callback:
                    progress_callback(f"Error retrieving agents: {str(e)}")
                
        # Get and check requesters
        if include_requesters:
            try:
                if progress_callback:
                    progress_callback("Retrieving requester list...")
                    
                requesters = self._get_all_requesters()
                stats['total_requesters_checked'] = len(requesters)
                self.logger.info(f"Checking {len(requesters)} requesters for inactivity")
                
                if progress_callback:
                    progress_callback(f"Found {len(requesters)} requesters to check")
                    if using_fallback_methods:
                        progress_callback("Using alternative activity tracking methods for requesters")
                
                # Process requesters in batches to avoid API rate limits
                batch_size = 20  # Smaller batch size for requesters as there are usually more
                total_batches = (len(requesters) + batch_size - 1) // batch_size
                
                for batch_num, batch_start in enumerate(range(0, len(requesters), batch_size), 1):
                    batch = requesters[batch_start:batch_start + batch_size]
                    self.logger.info(f"Processing requester batch {batch_num}/{total_batches} ({len(batch)} requesters)")
                    
                    if progress_callback:
                        progress_callback(f"Processing requester batch {batch_num}/{total_batches} ({len(batch)} requesters)")
                    
                    for requester in batch:
                        # Skip processing if the requester was created after the cutoff date
                        created_at = requester.get('created_at')
                        try:
                            if created_at:
                                created_date = datetime.datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
                                if created_date > cutoff_date:
                                    self.logger.debug(f"Skipping recently created requester {requester.get('id')}")
                                    continue
                        except Exception:
                            pass
                            
                        last_login = self._get_user_last_login(requester.get('id'))
                        
                        # If there's no last login data, consider the user inactive
                        if not last_login:
                            stats['users_without_login_data'] += 1
                            inactive_users.append({
                                'id': requester.get('id'),
                                'first_name': requester.get('first_name', ''),
                                'last_name': requester.get('last_name', ''),
                                'email': requester.get('primary_email'),
                                'last_login': None,
                                'days_inactive': 'Unknown',
                                'type': 'Requester',
                                'active': requester.get('active', False),
                                'created_at': requester.get('created_at')
                            })
                            stats['inactive_requesters'] += 1
                            continue
                        
                        # Parse the last login date
                        try:
                            last_login_date = datetime.datetime.strptime(last_login, "%Y-%m-%dT%H:%M:%SZ")
                            days_inactive = (datetime.datetime.now() - last_login_date).days
                            
                            # Check if the user is inactive based on the threshold
                            if days_inactive > threshold_days:
                                inactive_users.append({
                                    'id': requester.get('id'),
                                    'first_name': requester.get('first_name', ''),
                                    'last_name': requester.get('last_name', ''),
                                    'email': requester.get('primary_email'),
                                    'last_login': last_login,
                                    'days_inactive': days_inactive,
                                    'type': 'Requester',
                                    'active': requester.get('active', False),
                                    'created_at': requester.get('created_at')
                                })
                                stats['inactive_requesters'] += 1
                        except Exception as e:
                            self.logger.error(f"Error parsing last login date for requester {requester.get('id')}: {str(e)}")
                            stats['users_without_login_data'] += 1
                    
                    # Add a small delay between batches to prevent rate limiting
                    if batch_num < total_batches:
                        time.sleep(2)
                        
                if progress_callback and stats['inactive_requesters'] > 0:
                    progress_callback(f"Found {stats['inactive_requesters']} inactive requesters")
                        
            except Exception as e:
                self.logger.error(f"Error retrieving requesters: {str(e)}")
                if progress_callback:
                    progress_callback(f"Error retrieving requesters: {str(e)}")
        
        # Sort inactive users by days inactive (most inactive first)
        inactive_users.sort(key=lambda x: 999999 if x['days_inactive'] == 'Unknown' else x['days_inactive'], reverse=True)
        
        if progress_callback:
            progress_callback(f"Report generation complete. Found {len(inactive_users)} inactive users total.")
            if using_fallback_methods:
                progress_callback("Note: Direct login tracking not available - used alternative activity tracking methods")
        
        # Generate summary
        end_time = datetime.datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        summary = {
            'total_inactive_users': len(inactive_users),
            'inactive_agents': stats['inactive_agents'],
            'inactive_requesters': stats['inactive_requesters'],
            'total_agents_checked': stats['total_agents_checked'],
            'total_requesters_checked': stats['total_requesters_checked'],
            'users_without_login_data': stats['users_without_login_data'],
            'threshold_days': threshold_days,
            'execution_time_seconds': execution_time,
            'report_generated_at': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'using_alternative_methods': using_fallback_methods
        }
        
        return inactive_users, summary
    
    def export_inactive_users_to_csv(self, inactive_users, summary, output_path):
        """
        Export inactive users report to CSV file.
        
        Args:
            inactive_users: List of inactive user dictionaries
            summary: Report summary dictionary
            output_path: Path to save the CSV file
            
        Returns:
            Boolean indicating success
        """
        try:
            # Ensure directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            # Define CSV fields
            fieldnames = [
                'ID', 'First Name', 'Last Name', 'Email', 'Type', 
                'Account Status', 'Days Inactive', 'Last Login', 'Created At', 
                'Job Title', 'Department', 'Location'
            ]
            
            # Format date nicely for CSV
            def format_date(date_str):
                if not date_str:
                    return "Never"
                    
                try:
                    dt = datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
                    return dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    return date_str
            
            # Write CSV file
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                # Add report metadata as comments
                csvfile.write(f"# Inactive Users Report\n")
                csvfile.write(f"# Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                csvfile.write(f"# Inactivity Threshold: {summary.get('threshold_days', 'Unknown')} days\n")
                csvfile.write(f"# Total Inactive Users: {len(inactive_users)}\n")
                if 'inactive_agents' in summary:
                    csvfile.write(f"# Inactive Agents: {summary.get('inactive_agents', 0)} of {summary.get('total_agents_checked', 0)}\n")
                if 'inactive_requesters' in summary:
                    csvfile.write(f"# Inactive Requesters: {summary.get('inactive_requesters', 0)} of {summary.get('total_requesters_checked', 0)}\n")
                csvfile.write(f"# Users Without Login Data: {summary.get('users_without_login_data', 0)}\n")
                csvfile.write(f"# Execution Time: {summary.get('execution_time_seconds', 0):.2f} seconds\n")
                if summary.get('using_alternative_methods'):
                    csvfile.write(f"# NOTE: Direct login tracking was not available. Alternative activity tracking methods were used.\n")
                    csvfile.write(f"# This may result in less accurate last activity dates, often using the most recent ticket update\n")
                    csvfile.write(f"# or account creation date as a proxy for user activity.\n")
                csvfile.write("\n")
                
                # Write report data
                for user in inactive_users:
                    account_status = 'Active' if user.get('active', False) else 'Inactive'
                    
                    row = {
                        'ID': user.get('id', ''),
                        'First Name': user.get('first_name', ''),
                        'Last Name': user.get('last_name', ''),
                        'Email': user.get('email', ''),
                        'Type': user.get('type', ''),
                        'Account Status': account_status,
                        'Days Inactive': user.get('days_inactive', ''),
                        'Last Login': format_date(user.get('last_login')),
                        'Created At': format_date(user.get('created_at')),
                        'Job Title': user.get('job_title', ''),
                        'Department': user.get('department', ''),
                        'Location': user.get('location', '')
                    }
                    writer.writerow(row)
                    
            self.logger.info(f"Successfully exported inactive users report to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting inactive users report: {str(e)}")
            return False
    
    def _get_all_agents(self):
        """
        Get all agents from FreshService API.
        
        Returns:
            List of agents
        """
        self.logger.info("Getting all agents")
        
        agents = []
        page = 1
        per_page = 100  # Maximum value allowed
        
        while True:
            try:
                result = self.api_client._make_request(
                    'GET',
                    'agents',
                    params={'page': page, 'per_page': per_page},
                    workspace_id=None
                )
                
                if not isinstance(result, dict) or 'agents' not in result:
                    break
                    
                batch = result.get('agents', [])
                if not batch:
                    break
                    
                agents.extend(batch)
                
                # Check if we've reached the last page
                if len(batch) < per_page:
                    break
                    
                page += 1
                
            except Exception as e:
                self.logger.error(f"Error retrieving agents page {page}: {str(e)}")
                break
                
        self.logger.info(f"Retrieved {len(agents)} agents")
        return agents
    
    def _get_all_requesters(self):
        """
        Get all requesters from FreshService API.
        
        Returns:
            List of requesters
        """
        self.logger.info("Getting all requesters")
        
        requesters = []
        page = 1
        per_page = 100  # Maximum value allowed
        
        while True:
            try:
                result = self.api_client._make_request(
                    'GET',
                    'requesters',
                    params={'page': page, 'per_page': per_page},
                    workspace_id=None
                )
                
                if not isinstance(result, dict) or 'requesters' not in result:
                    break
                    
                batch = result.get('requesters', [])
                if not batch:
                    break
                    
                requesters.extend(batch)
                
                # Check if we've reached the last page
                if len(batch) < per_page:
                    break
                    
                page += 1
                
            except Exception as e:
                self.logger.error(f"Error retrieving requesters page {page}: {str(e)}")
                break
                
        self.logger.info(f"Retrieved {len(requesters)} requesters")
        return requesters
    
    def _get_user_last_login(self, user_id):
        """
        Get the last login date for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Last login date string or None if not found
        """
        try:
            # First approach: Try to get user details which sometimes include last_login_at
            result = self.api_client._make_request(
                'GET',
                f'requesters/{user_id}',
                workspace_id=None
            )
            
            if isinstance(result, dict) and 'requester' in result:
                requester = result.get('requester', {})
                # Check for last_login_at field
                if requester.get('last_login_at'):
                    return requester.get('last_login_at')
                
                # Check for updated_at as a fallback
                if requester.get('updated_at'):
                    return requester.get('updated_at')
                    
            # Second approach: Try to get agent details which might include last_login_at
            if user_id:
                try:
                    result = self.api_client._make_request(
                        'GET',
                        f'agents/{user_id}',
                        workspace_id=None
                    )
                    
                    if isinstance(result, dict) and 'agent' in result:
                        agent = result.get('agent', {})
                        # Check for last_login_at field
                        if agent.get('last_login_at'):
                            return agent.get('last_login_at')
                        
                        # Check for updated_at as a fallback
                        if agent.get('updated_at'):
                            return agent.get('updated_at')
                except:
                    # Ignore errors when checking agent details
                    pass
            
            # Third approach: Check recent ticket activity as a proxy for user activity
            # This is less accurate but provides a fallback when audit logs aren't available
            try:
                # For requesters, check their ticket creation dates
                result = self.api_client._make_request(
                    'GET',
                    'tickets',
                    params={
                        'requester_id': user_id,
                        'per_page': 1,
                        'order_type': 'desc',
                        'order_by': 'created_at'
                    },
                    workspace_id=None
                )
                
                if isinstance(result, dict) and 'tickets' in result and result['tickets']:
                    # Return the most recent ticket creation date as a proxy for activity
                    return result['tickets'][0].get('created_at')
            except:
                # Ignore errors when checking ticket activity
                pass
                
            # If we reach here, we couldn't find any login or activity information
            # Fall back to created_at date from user object
            if isinstance(result, dict):
                if 'requester' in result and result['requester'].get('created_at'):
                    return result['requester'].get('created_at')
                elif 'agent' in result and result['agent'].get('created_at'):
                    return result['agent'].get('created_at')
            
            # We couldn't determine last login time
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting last login for user {user_id}: {str(e)}")
            # If all methods fail, return None indicating we couldn't determine activity
            return None 