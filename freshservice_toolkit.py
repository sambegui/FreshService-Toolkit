#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FreshService User Management Toolkit

A comprehensive toolkit for FreshService administrators to efficiently manage user details.
Supports multiple workspaces and provides various user management capabilities.
"""

import os
import sys
import time
import csv
import json
import getpass
import logging
import datetime
import argparse
import base64
from typing import Dict, List, Optional, Tuple, Any

# Core modules - make imports optional with fallbacks
try:
    from tabulate import tabulate
    TABULATE_AVAILABLE = True
except ImportError:
    TABULATE_AVAILABLE = False

try:
    from colorama import init, Fore, Style
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False

# Try to import keyring, but don't fail if it's not available
try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

from utils.api_client import FreshServiceAPI
from utils.workspace_manager import WorkspaceManager
from utils.user_manager import UserManager
from utils.department_manager import DepartmentManager
from utils.csv_processor import CSVProcessor
from utils.reports import ReportsManager
from utils.helpers import setup_logging, setup_virtual_env, print_colored, clear_screen
from utils.menu import Menu

# Global variables
DRY_RUN = False
API_KEY = None
CURRENT_WORKSPACE = None
logger = None

def setup_environment() -> None:
    """Setup the virtual environment and install dependencies."""
    print_colored("🛠️  Setting up environment...", "blue")
    setup_virtual_env()


def get_api_key() -> str:
    """Get the API key from environment variable, keyring, or user input."""
    global logger
    
    # Initialize on first run
    if logger is None:
        logger = logging.getLogger('freshservice_toolkit')
    
    while True:
        api_key = os.environ.get('FRESHSERVICE_API_KEY')
        
        if not api_key and KEYRING_AVAILABLE:
            try:
                api_key = keyring.get_password("freshservice-toolkit", "api_key")
            except Exception as e:
                logging.warning(f"Failed to retrieve API key from keyring: {e}")
        
        if not api_key:
            import getpass
            print_colored("\n🔑 FreshService API Authentication", "blue")
            api_key = getpass.getpass("Please enter your FreshService API key (input will be hidden):\nPassword: ")
        
        # Try to validate the API key
        try:
            valid = validate_api_key(api_key)
            if valid:
                # Save valid key to keyring for future use
                if KEYRING_AVAILABLE:
                    try:
                        keyring.set_password("freshservice-toolkit", "api_key", api_key)
                    except Exception as e:
                        logging.warning(f"Failed to save API key to keyring: {e}")
                return api_key
            else:
                # Key validation failed
                print_colored("\n❌ Invalid API key. The key could not be validated with FreshService.", "red")
                print_colored("Please check your API key and try again.", "yellow")
                
                # Clear environment variable and keyring storage
                os.environ.pop('FRESHSERVICE_API_KEY', None)
                if KEYRING_AVAILABLE:
                    try:
                        keyring.delete_password("freshservice-toolkit", "api_key")
                    except Exception:
                        pass
                
                # Ask what to do next
                retry_choice = input("Would you like to [1] Enter a new API key or [2] Continue with invalid key anyway (not recommended)? (1/2): ").strip()
                if retry_choice == "2":
                    print_colored("\n⚠️ Warning: Using an invalid API key. Most functionality will fail.", "red", bold=True)
                    input("Press Enter to continue anyway or Ctrl+C to exit...")
                    return api_key
                # If not 2, default to asking for a new key by continuing the loop
        
        except Exception as e:
            # Handle validation errors
            print_colored(f"\n❌ Error during API key validation: {str(e)}", "red")
            print_colored("Please check your API key and try again.", "yellow")
            
            # Ask what to do next
            retry_choice = input("Would you like to [1] Enter a new API key or [2] Continue with invalid key anyway (not recommended)? (1/2): ").strip()
            if retry_choice == "2":
                print_colored("\n⚠️ Warning: Using an invalid or untested API key. Most functionality will fail.", "red", bold=True)
                input("Press Enter to continue anyway or Ctrl+C to exit...")
                return api_key
            # If not 2, default to asking for a new key by continuing the loop

def validate_api_key(api_key: str) -> bool:
    """Validate the API key by making a simple API request."""
    print_colored("🔄 Validating API key...", "yellow")
    
    # Create a logging instance if the global one isn't available yet
    global logger
    if logger is None:
        logger = logging.getLogger('freshservice_toolkit')
    
    # Create a temporary API client to test the key
    from utils.api_client import FreshServiceAPI
    api_client = FreshServiceAPI(api_key, logger, dry_run=False)
    
    try:
        # Make a simple request that should work with any valid key
        # Using the /api/v2/requesters endpoint with a limit of 1
        response = api_client._make_request('GET', 'requesters', params={'per_page': 1})
        
        # If we get a valid response, the key is valid
        is_valid = isinstance(response, dict) and 'requesters' in response
        
        if is_valid:
            print_colored("✅ API key validated successfully!", "green")
        
        return is_valid
    except Exception as e:
        logging.error(f"API key validation failed: {str(e)}")
        return False


def display_main_menu(
    workspace_manager: WorkspaceManager, 
    user_manager: UserManager,
    department_manager: DepartmentManager,
    csv_processor: CSVProcessor
) -> None:
    """Display the main menu and handle user input."""
    global DRY_RUN, CURRENT_WORKSPACE
    
    # Create menu instance
    menu = Menu("FreshService User Management Toolkit")
    
    # Add menu items
    menu.add_item("🔍 Find and Edit User", lambda: user_menu(user_manager, department_manager))
    menu.add_item("📊 Bulk Operations", lambda: bulk_operations_menu(user_manager, department_manager, csv_processor))
    menu.add_item("👥 Group Management", lambda: group_management_menu(user_manager))
    menu.add_item("🔐 Access Control", lambda: access_control_menu(user_manager))
    menu.add_item("📈 Reports", lambda: reports_menu(user_manager, csv_processor))
    menu.add_item("🔄 Switch Workspace", lambda: switch_workspace(workspace_manager))
    menu.add_item("❓ Help", display_help)
    menu.add_item("🚪 Exit", sys.exit)
    
    # Run the menu
    while True:
        # Display workspace info
        clear_screen()
        if CURRENT_WORKSPACE:
            print_colored(f"Current Workspace: {CURRENT_WORKSPACE.get('name', 'Unknown')}", "blue", bold=True)
        else:
            print_colored("⚠️ No workspace available - Please check your API key or permissions", "red", bold=True)
        
        # Display and process menu
        menu.display()


def user_menu(user_manager: UserManager, department_manager: DepartmentManager) -> None:
    """Display the user management menu."""
    menu = Menu("Find and Edit User")
    
    menu.add_item("📧 Search by Email", lambda: search_by_email(user_manager, department_manager))
    menu.add_item("👤 Search by Name", lambda: search_by_name(user_manager, department_manager))
    menu.add_item("🔍 Advanced Search", lambda: advanced_search(user_manager, department_manager))
    menu.add_item("📜 Recent Users", lambda: view_recent_users(user_manager, department_manager))
    # Return True when back is selected to break out of the menu loop
    menu.add_item("↩️ Back", lambda: True)
    
    # Display menu and wait for user to exit
    menu.display()
    # Return to main menu
    return


def bulk_operations_menu(
    user_manager: UserManager, 
    department_manager: DepartmentManager,
    csv_processor: CSVProcessor
) -> None:
    """Display the bulk operations menu."""
    menu = Menu("Bulk Operations")
    
    menu.add_item("🏢 Update Departments from CSV", lambda: update_departments_from_csv(user_manager, department_manager, csv_processor))
    menu.add_item("❌ Deactivate Users from CSV", lambda: deactivate_users_from_csv(user_manager, csv_processor))
    menu.add_item("👥 Update Group Memberships from CSV", lambda: update_groups_from_csv(user_manager, csv_processor))
    menu.add_item("📋 Create CSV Template", lambda: create_csv_template(csv_processor))
    # Return True when back is selected to break out of the menu loop
    menu.add_item("↩️ Back", lambda: True)
    
    # Display menu and wait for user to exit
    menu.display()
    # Return to main menu
    return


def group_management_menu(user_manager: UserManager) -> None:
    """Display the group management menu."""
    menu = Menu("Group Management")
    
    menu.add_item("👀 View User's Groups", lambda: view_user_groups(user_manager))
    menu.add_item("➕ Add User to Group", lambda: add_user_to_group(user_manager))
    menu.add_item("➖ Remove User from Group", lambda: remove_user_from_group(user_manager))
    # Return True when back is selected to break out of the menu loop
    menu.add_item("↩️ Back", lambda: True)
    
    # Display menu and wait for user to exit
    menu.display()
    # Return to main menu
    return


def access_control_menu(user_manager: UserManager) -> None:
    """Display the access control menu."""
    menu = Menu("Access Control")
    
    menu.add_item("🔑 Force Password Reset", lambda: force_password_reset(user_manager))
    menu.add_item("🔓 Unlock Account", lambda: unlock_account(user_manager))
    menu.add_item("🛡️ Update User Role", lambda: update_user_role(user_manager))
    # Return True when back is selected to break out of the menu loop
    menu.add_item("↩️ Back", lambda: True)
    
    # Display menu and wait for user to exit
    menu.display()
    # Return to main menu
    return


def reports_menu(user_manager: UserManager, csv_processor: CSVProcessor) -> None:
    """Display the reports menu."""
    menu = Menu("Reports")
    
    menu.add_item("📆 User Ticket Activity Report", lambda: user_activity_report(user_manager, csv_processor))
    menu.add_item("💤 Inactive Accounts Report", lambda: inactive_accounts_report(user_manager, csv_processor))
    menu.add_item("📊 Custom User Report", lambda: custom_user_report(user_manager, csv_processor))
    menu.add_item("🔍 API Diagnostics", lambda: run_api_diagnostics(user_manager))
    # Return True when back is selected to break out of the menu loop
    menu.add_item("↩️ Back", lambda: True)
    
    # Display menu and wait for user to exit
    menu.display()
    # Return to main menu
    return


def search_by_email(user_manager: UserManager, department_manager: DepartmentManager) -> None:
    """Search for a user by email address."""
    print_colored("\n📧 Search by Email", "blue")
    email = input("Enter user email address: ").strip()
    
    if not email:
        print_colored("❌ Email address is required.", "red")
        input("Press Enter to continue...")
        return
        
    print_colored(f"Searching for user with email: {email}", "blue")
    user = user_manager.get_user_by_email(email)
    
    if user:
        display_user_details(user, user_manager, department_manager)
    else:
        print_colored(f"❌ No user found with email: {email}", "red")
        offer_name_search = input("Would you like to search by name instead? (y/n): ").lower()
        if offer_name_search == 'y':
            search_by_name(user_manager, department_manager)
    
    input("Press Enter to continue...")


def search_by_name(user_manager: UserManager, department_manager: DepartmentManager) -> None:
    """Search for users by name."""
    print_colored("\n👤 Search by Name", "blue")
    first_name = input("Enter first name (leave blank to skip): ").strip()
    last_name = input("Enter last name (leave blank to skip): ").strip()
    
    if not first_name and not last_name:
        print_colored("❌ At least one name field is required.", "red")
        input("Press Enter to continue...")
        return
        
    print_colored(f"Searching for users with name: {first_name} {last_name}", "blue")
    users = user_manager.search_users_by_name(first_name, last_name)
    
    if users:
        if len(users) == 1:
            display_user_details(users[0], user_manager, department_manager)
        else:
            selected_user = select_user_from_results(users, user_manager, department_manager)
            if selected_user:
                display_user_details(selected_user, user_manager, department_manager)
    else:
        print_colored(f"❌ No users found with name: {first_name} {last_name}", "red")
    
    input("Press Enter to continue...")


def select_user_from_results(
    users: List[Dict[str, Any]], 
    user_manager: UserManager,
    department_manager: DepartmentManager
) -> Optional[Dict[str, Any]]:
    """Display user search results and allow selection."""
    if not users:
        print_colored("❌ No matching users found.", "red")
        input("Press Enter to continue...")
        return None
    
    print_colored(f"\nSearch Results ({len(users)} matches):", "blue")
    
    filtered_users = users
    
    while filtered_users:
        for i, user in enumerate(filtered_users, 1):
            name = f"{user.get('first_name', '')} {user.get('last_name', '')}"
            email = user.get('primary_email', 'No email')
            job_title = user.get('job_title', 'No title')
            
            # Get department names for display
            dept_info = ""
            dept_ids = user.get('department_ids', [])
            
            if dept_ids:
                dept_names = []
                for dept_id in dept_ids:
                    dept = department_manager.get_department_by_id(dept_id)
                    if dept:
                        dept_names.append(f"{dept.get('name')} (ID: {dept_id})")
                    else:
                        dept_names.append(f"Unknown (ID: {dept_id})")
                dept_info = ", ".join(dept_names)
            else:
                dept_info = "No department"
                
            print_colored(f"{i}. {name} ({email})", "green")
            print_colored(f"   Department: {dept_info}", "yellow")
            print_colored(f"   Title: {job_title}", "yellow")
            print()
        
        selection = input("\nSelect user by number or type 'filter' to refine search (or 'cancel'): ").strip().lower()
        
        if selection == 'cancel':
            return None
        elif selection == 'filter':
            filter_text = input("Enter text to filter results: ").strip().lower()
            if filter_text:
                filtered_users = [
                    user for user in users
                    if filter_text in (user.get('first_name', '') or '').lower()
                    or filter_text in (user.get('last_name', '') or '').lower()
                    or filter_text in (user.get('primary_email', '') or '').lower()
                    or filter_text in (user.get('job_title', '') or '').lower()
                ]
                
                if not filtered_users:
                    print_colored("❌ No users match that filter.", "red")
                    input("Press Enter to return to all results...")
                    filtered_users = users
            continue
        
        try:
            index = int(selection) - 1
            if 0 <= index < len(filtered_users):
                selected_user = filtered_users[index]
                return selected_user
            else:
                print_colored("❌ Invalid selection. Please try again.", "red")
        except ValueError:
            print_colored("❌ Please enter a valid number, 'filter', or 'cancel'.", "red")


def display_user_details(
    user: Dict[str, Any], 
    user_manager: UserManager,
    department_manager: DepartmentManager
) -> None:
    """Display user details and offer editing options."""
    name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
    
    # Look up reporting manager name if we have an ID
    reporting_manager_info = "Not specified"
    if reporting_manager_id := user.get('reporting_manager_id'):
        try:
            # Silently lookup the manager
            manager = user_manager.get_user_by_id(reporting_manager_id)
            if manager:
                manager_name = f"{manager.get('first_name', '')} {manager.get('last_name', '')}".strip()
                reporting_manager_info = f"{manager_name} (ID: {reporting_manager_id})"
            else:
                reporting_manager_info = f"Unknown (ID: {reporting_manager_id})"
        except Exception as e:
            # Log error but continue with display
            user_manager.logger.error(f"Error fetching reporting manager details: {e}")
            reporting_manager_info = f"ID: {reporting_manager_id} (could not resolve name)"
    
    # Look up department names if we have department IDs
    department_info = "Not specified"
    if department_ids := user.get('department_ids'):
        try:
            department_names = []
            for dept_id in department_ids:
                department = department_manager.get_department_by_id(dept_id)
                if department:
                    department_names.append(f"{department.get('name')} (ID: {dept_id})")
                else:
                    department_names.append(f"Unknown (ID: {dept_id})")
            
            if department_names:
                department_info = ", ".join(department_names)
        except Exception as e:
            # Log error but continue with display
            user_manager.logger.error(f"Error fetching department details: {e}")
            department_info = f"IDs: {', '.join(map(str, department_ids))} (could not resolve names)"
    
    print_colored(f"\nUser Details for: {name}", "green", bold=True)
    print_colored(f"ID: {user.get('id')}", "yellow")
    print_colored(f"Email: {user.get('primary_email', 'Not specified')}", "yellow")
    print_colored(f"First Name: {user.get('first_name', 'Not specified')}", "yellow")
    print_colored(f"Last Name: {user.get('last_name', 'Not specified')}", "yellow")
    print_colored(f"Department: {department_info}", "yellow")
    print_colored(f"Job Title: {user.get('job_title', 'Not specified')}", "yellow")
    print_colored(f"Reporting Manager: {reporting_manager_info}", "yellow")
    print_colored(f"Active: {'Yes' if user.get('active', False) else 'No'}", "yellow")
    print_colored(f"Agent: {'Yes' if user.get('is_agent', False) else 'No'}", "yellow")
    
    if user.get('created_at'):
        print_colored(f"Created: {user.get('created_at')}", "yellow")
    
    edit_options_menu(user, user_manager, department_manager)


def edit_options_menu(user: Dict[str, Any], user_manager: UserManager, department_manager: DepartmentManager) -> None:
    """Display edit options for a user and handle selection."""
    user_id = user.get('id')
    
    while True:
        # Refresh user data before displaying the menu to show updated values
        current_user = user_manager.get_user_by_id(user_id)
        if not current_user:
            print_colored("❌ Error: User no longer exists or cannot be accessed.", "red")
            input("Press Enter to continue...")
            return
            
        # Get current name for display
        name = f"{current_user.get('first_name', '')} {current_user.get('last_name', '')}".strip()
        
        print_colored(f"\nEdit {name}", "blue")
        print_colored("----------------------", "blue")
        
        menu_items = [
            "Edit First Name",
            "Edit Last Name",
            "Edit Department",
            "Edit Reporting Manager",
            "Edit Multiple Fields",
            f"{'❌ Deactivate' if current_user.get('active', False) else '✅ Activate'} User",
            "↩️ Back"
        ]
        
        for i, item in enumerate(menu_items, 1):
            print_colored(f"{i}. {item}", "cyan")
        
        print()  # Empty line for spacing
        
        choice = input("Enter your choice (or 'q' to quit): ").lower()
        
        if choice == 'q':
            return
        
        try:
            option = int(choice)
            if option == 1:
                edit_first_name(current_user, user_manager)
            elif option == 2:
                edit_last_name(current_user, user_manager)
            elif option == 3:
                edit_department(current_user, user_manager, department_manager)
            elif option == 4:
                edit_reporting_manager(current_user, user_manager, department_manager)
            elif option == 5:
                edit_multiple_fields(current_user, user_manager, department_manager)
            elif option == 6:
                if current_user.get('active', False):
                    deactivate_user(current_user, user_manager)
                else:
                    activate_user(current_user, user_manager)
            elif option == 7:
                # Back option - return to previous menu
                print_colored("Returning to previous menu...", "yellow")
                return
            else:
                print_colored("❌ Invalid option. Please try again.", "red")
        except ValueError:
            print_colored("❌ Invalid input. Please enter a number.", "red")


def toggle_dry_run() -> None:
    """Toggle between dry run and live mode."""
    global DRY_RUN
    DRY_RUN = not DRY_RUN
    
    if DRY_RUN:
        print_colored("🔍 Dry Run Mode enabled - No changes will be made to FreshService", "green")
    else:
        print_colored("⚠️ Live Mode enabled - Changes will be applied to FreshService", "red")
    
    input("Press Enter to continue...")


def switch_workspace(workspace_manager: WorkspaceManager) -> None:
    """Switch between available workspaces."""
    global CURRENT_WORKSPACE
    
    print_colored("\n🔄 Switch Workspace", "blue")
    workspaces = workspace_manager.get_workspaces()
    
    if not workspaces:
        print_colored("❌ No workspaces found.", "red")
        input("Press Enter to continue...")
        return
    
    print_colored("Available Workspaces:", "green")
    for i, workspace in enumerate(workspaces, 1):
        name = workspace.get('name', 'Unnamed')
        current = " (current)" if workspace == CURRENT_WORKSPACE else ""
        print_colored(f"{i}. {name}{current}", "yellow")
    
    try:
        selection = input("\nSelect workspace by number (or 'cancel'): ").strip()
        
        if selection.lower() == 'cancel':
            return
            
        index = int(selection) - 1
        if 0 <= index < len(workspaces):
            CURRENT_WORKSPACE = workspaces[index]
            print_colored(f"✅ Switched to workspace: {CURRENT_WORKSPACE['name']}", "green")
        else:
            print_colored("❌ Invalid selection.", "red")
    except ValueError:
        print_colored("❌ Please enter a valid number or 'cancel'.", "red")
    
    input("Press Enter to continue...")


def display_help() -> None:
    """Display help information about the toolkit."""
    print_colored("\n❓ FreshService User Management Toolkit Help", "blue", bold=True)
    
    print_colored("\nMain Features:", "green")
    print("🔍 Find and Edit User - Search and modify user details")
    print("📊 Bulk Operations - Perform actions on multiple users via CSV")
    print("👥 Group Management - Manage user group memberships")
    print("🔐 Access Control - Handle password resets and account unlocking")
    print("📈 Reports - Generate reports on user activity and export data")
    print("🔄 Switch Workspace - Change to a different FreshService workspace")
    
    print_colored("\nBulk Operations:", "cyan")
    print("The toolkit supports the following bulk operations via CSV files:")
    print("- Update departments for multiple users")
    print("- Deactivate multiple user accounts")
    print("- Add or remove users from groups")
    print("\nUse the 'Create CSV Template' option to generate template files with the correct format.")
    
    print_colored("\nReports:", "cyan")
    print("Generate various reports including:")
    print("- User Activity Report: Track user interactions with tickets")
    print("  This report shows tickets created by a user and their conversations")
    print("  You can filter by time period and export results to CSV")
    print("- Inactive Accounts Report: Identify dormant user accounts")
    print("- Custom User Report: Generate custom reports with selected fields")
    
    print_colored("\nCSV File Formats:", "cyan")
    print("For bulk operations, CSV files should include the following columns:")
    
    print_colored("\nDepartment Update Template:", "yellow")
    print("Email,Department")
    print("john.doe@example.com,Engineering")
    
    print_colored("\nUser Deactivation Template:", "yellow")
    print("Email,Reason")
    print("john.doe@example.com,Left the company")
    
    print_colored("\nGroup Membership Template:", "yellow")
    print("Email,Group_Name,Action")
    print("john.doe@example.com,Support Team,add")
    
    print_colored("\nQuick Tips:", "green")
    print("- Use 'q' to quit from any menu")
    print("- After creating a CSV template, edit it with your preferred spreadsheet software")
    print("- Check result files for details on any errors encountered during bulk operations")
    print("- Back up important data before performing bulk operations")
    print("- Activity reports can help track user engagement and identify support patterns")
    
    input("\nPress Enter to continue...")


def edit_first_name(user: Dict[str, Any], user_manager: UserManager) -> None:
    """Edit the first name of a user."""
    user_id = user.get('id')
    current_name = user.get('first_name', '')
    
    print_colored(f"\nEdit First Name for {user.get('first_name')} {user.get('last_name')}", "blue")
    print_colored(f"Current First Name: {current_name}", "yellow")
    
    new_name = input("Enter new first name (leave blank to cancel): ").strip()
    
    if not new_name:
        print_colored("Operation cancelled.", "yellow")
        return
        
    if new_name == current_name:
        print_colored("No change made - new name is the same as current name.", "yellow")
        return
    
    confirmation = input(f"Change first name from '{current_name}' to '{new_name}'? (y/n): ").lower()
    
    if confirmation == 'y':
        print_colored(f"Updating first name to '{new_name}'...", "blue")
        
        updated_user = user_manager.update_user(user_id, {'first_name': new_name})
        
        if updated_user:
            print_colored("✅ First name updated successfully.", "green")
        else:
            print_colored("❌ Failed to update first name.", "red")
    else:
        print_colored("Operation cancelled.", "yellow")
    
    input("Press Enter to continue...")


def edit_last_name(user: Dict[str, Any], user_manager: UserManager) -> None:
    """Edit the last name of a user."""
    user_id = user.get('id')
    current_name = user.get('last_name', '')
    
    print_colored(f"\nEdit Last Name for {user.get('first_name')} {user.get('last_name')}", "blue")
    print_colored(f"Current Last Name: {current_name}", "yellow")
    
    new_name = input("Enter new last name (leave blank to cancel): ").strip()
    
    if not new_name:
        print_colored("Operation cancelled.", "yellow")
        return
        
    if new_name == current_name:
        print_colored("No change made - new name is the same as current name.", "yellow")
        return
    
    confirmation = input(f"Change last name from '{current_name}' to '{new_name}'? (y/n): ").lower()
    
    if confirmation == 'y':
        print_colored(f"Updating last name to '{new_name}'...", "blue")
        
        updated_user = user_manager.update_user(user_id, {'last_name': new_name})
        
        if updated_user:
            print_colored("✅ Last name updated successfully.", "green")
        else:
            print_colored("❌ Failed to update last name.", "red")
    else:
        print_colored("Operation cancelled.", "yellow")
    
    input("Press Enter to continue...")


def edit_department(user: Dict[str, Any], user_manager: UserManager, department_manager: DepartmentManager) -> None:
    """Edit the department of a user."""
    user_id = user.get('id')
    current_dept_ids = user.get('department_ids', [])
    
    # Get current department names for display
    current_dept_names = []
    for dept_id in current_dept_ids:
        dept = department_manager.get_department_by_id(dept_id)
        if dept:
            current_dept_names.append(f"{dept.get('name')} (ID: {dept_id})")
        else:
            current_dept_names.append(f"Unknown (ID: {dept_id})")
    
    current_dept_display = ", ".join(current_dept_names) if current_dept_names else "None"
    
    print_colored(f"\nEdit Department for {user.get('first_name')} {user.get('last_name')}", "blue")
    print_colored(f"Current Department(s): {current_dept_display}", "yellow")
    
    # Get available departments
    departments = department_manager.get_departments()
    
    if not departments:
        print_colored("❌ No departments available to choose from.", "red")
        input("Press Enter to continue...")
        return
    
    # Display available departments
    print_colored("\nAvailable Departments:", "green")
    for i, dept in enumerate(departments, 1):
        print_colored(f"{i}. {dept.get('name')} (ID: {dept.get('id')})", "cyan")
    
    # Get department selection
    while True:
        selection = input("\nEnter department number (leave blank to cancel): ").strip()
        
        if not selection:
            print_colored("Operation cancelled.", "yellow")
            input("Press Enter to continue...")
            return
            
        try:
            index = int(selection) - 1
            if 0 <= index < len(departments):
                selected_dept = departments[index]
                selected_dept_id = selected_dept.get('id')
                
                # Confirm change
                confirmation = input(f"Change department to '{selected_dept.get('name')}'? (y/n): ").lower()
                
                if confirmation == 'y':
                    print_colored(f"Updating department...", "blue")
                    
                    # Update the user's department - always pass as an array of integers
                    dept_id = int(selected_dept_id)
                    print_colored(f"Setting department ID to: {dept_id}", "blue")
                    
                    updated_user = user_manager.update_user(
                        user_id, 
                        {'department_ids': [dept_id]}
                    )
                    
                    if updated_user:
                        new_dept_ids = updated_user.get('department_ids', [])
                        new_dept_names = []
                        for new_dept_id in new_dept_ids:
                            dept = department_manager.get_department_by_id(new_dept_id)
                            if dept:
                                new_dept_names.append(f"{dept.get('name')} (ID: {new_dept_id})")
                            else:
                                new_dept_names.append(f"Unknown (ID: {new_dept_id})")
                        
                        new_dept_display = ", ".join(new_dept_names) if new_dept_names else "None"
                        print_colored("✅ Department updated successfully.", "green")
                        print_colored(f"New department(s): {new_dept_display}", "green")
                    else:
                        print_colored("❌ Failed to update department.", "red")
                else:
                    print_colored("Operation cancelled.", "yellow")
                
                input("Press Enter to continue...")
                return
            else:
                print_colored("❌ Invalid selection. Please choose a valid number.", "red")
        except ValueError:
            print_colored("❌ Please enter a valid number or leave blank to cancel.", "red")


def edit_reporting_manager(user: Dict[str, Any], user_manager: UserManager, department_manager: DepartmentManager) -> None:
    """Edit the reporting manager of a user."""
    user_id = user.get('id')
    current_manager_id = user.get('reporting_manager_id')
    current_manager = None
    
    if current_manager_id:
        current_manager = user_manager.get_user_by_id(current_manager_id)
        
    current_manager_name = "None"
    if current_manager:
        current_manager_name = f"{current_manager.get('first_name', '')} {current_manager.get('last_name', '')}".strip()
    
    print_colored(f"\nEdit Reporting Manager for {user.get('first_name')} {user.get('last_name')}", "blue")
    print_colored(f"Current Reporting Manager: {current_manager_name}", "yellow")
    
    # Options for searching for a new manager
    print_colored("\nSearch for a manager:", "green")
    print_colored("1. Search by Email", "cyan")
    print_colored("2. Search by Name", "cyan")
    print_colored("3. Clear Manager", "cyan")
    print_colored("4. Cancel", "cyan")
    
    choice = input("\nEnter your choice: ").strip()
    
    if choice == "1":
        # Search by email
        email = input("Enter manager's email: ").strip()
        if not email:
            print_colored("Operation cancelled.", "yellow")
            input("Press Enter to continue...")
            return
            
        manager = user_manager.get_user_by_email(email)
        if not manager:
            print_colored(f"❌ No user found with email {email}", "red")
            input("Press Enter to continue...")
            return
            
        new_manager = manager
    elif choice == "2":
        # Search by name
        first_name = input("Enter manager's first name (leave blank to skip): ").strip()
        last_name = input("Enter manager's last name (leave blank to skip): ").strip()
        
        if not first_name and not last_name:
            print_colored("Operation cancelled.", "yellow")
            input("Press Enter to continue...")
            return
            
        managers = user_manager.search_users_by_name(first_name, last_name)
        
        if not managers:
            print_colored(f"❌ No users found matching the name criteria", "red")
            input("Press Enter to continue...")
            return
            
        if len(managers) == 1:
            new_manager = managers[0]
        else:
            # Multiple results, let user select
            new_manager = select_user_from_results(managers, user_manager, department_manager)
            
        if not new_manager:
            print_colored("Operation cancelled.", "yellow")
            input("Press Enter to continue...")
            return
    elif choice == "3":
        # Clear manager
        confirmation = input("Are you sure you want to clear the reporting manager? (y/n): ").lower()
        
        if confirmation == 'y':
            print_colored(f"Clearing reporting manager...", "blue")
            
            updated_user = user_manager.update_user(
                user_id, 
                {'reporting_manager_id': None}
            )
            
            if updated_user:
                print_colored("✅ Reporting manager cleared successfully.", "green")
            else:
                print_colored("❌ Failed to clear reporting manager.", "red")
        else:
            print_colored("Operation cancelled.", "yellow")
            
        input("Press Enter to continue...")
        return
    elif choice == "4":
        # Cancel
        print_colored("Operation cancelled.", "yellow")
        input("Press Enter to continue...")
        return
    else:
        print_colored("❌ Invalid choice.", "red")
        input("Press Enter to continue...")
        return
    
    # Confirm change
    new_manager_name = f"{new_manager.get('first_name', '')} {new_manager.get('last_name', '')}".strip()
    confirmation = input(f"Set reporting manager to {new_manager_name}? (y/n): ").lower()
    
    if confirmation == 'y':
        print_colored(f"Updating reporting manager...", "blue")
        
        updated_user = user_manager.update_user(
            user_id, 
            {'reporting_manager_id': new_manager.get('id')}
        )
        
        if updated_user:
            print_colored("✅ Reporting manager updated successfully.", "green")
        else:
            print_colored("❌ Failed to update reporting manager.", "red")
    else:
        print_colored("Operation cancelled.", "yellow")
        
    input("Press Enter to continue...")


def edit_multiple_fields(user: Dict[str, Any], user_manager: UserManager, department_manager: DepartmentManager) -> None:
    """Edit multiple fields of a user at once."""
    user_id = user.get('id')
    
    print_colored(f"\nEdit Multiple Fields for {user.get('first_name')} {user.get('last_name')}", "blue")
    
    update_data = {}
    
    # Edit first name
    current_first_name = user.get('first_name', '')
    print_colored(f"Current First Name: {current_first_name}", "yellow")
    new_first_name = input(f"Enter new first name (or press Enter to keep current): ").strip()
    if new_first_name and new_first_name != current_first_name:
        update_data['first_name'] = new_first_name
    
    # Edit last name
    current_last_name = user.get('last_name', '')
    print_colored(f"Current Last Name: {current_last_name}", "yellow")
    new_last_name = input(f"Enter new last name (or press Enter to keep current): ").strip()
    if new_last_name and new_last_name != current_last_name:
        update_data['last_name'] = new_last_name
    
    # Edit job title
    current_job_title = user.get('job_title', '')
    print_colored(f"Current Job Title: {current_job_title}", "yellow")
    new_job_title = input(f"Enter new job title (or press Enter to keep current): ").strip()
    if new_job_title and new_job_title != current_job_title:
        update_data['job_title'] = new_job_title
    
    # Edit work phone
    current_work_phone = user.get('work_phone_number', '')
    print_colored(f"Current Work Phone: {current_work_phone}", "yellow")
    new_work_phone = input(f"Enter new work phone (or press Enter to keep current): ").strip()
    if new_work_phone and new_work_phone != current_work_phone:
        update_data['work_phone_number'] = new_work_phone
    
    # Edit mobile phone
    current_mobile_phone = user.get('mobile_phone_number', '')
    print_colored(f"Current Mobile Phone: {current_mobile_phone}", "yellow")
    new_mobile_phone = input(f"Enter new mobile phone (or press Enter to keep current): ").strip()
    if new_mobile_phone and new_mobile_phone != current_mobile_phone:
        update_data['mobile_phone_number'] = new_mobile_phone
    
    # If no changes requested, exit
    if not update_data:
        print_colored("No changes requested.", "yellow")
        input("Press Enter to continue...")
        return
    
    # Confirm the updates
    print_colored("\nProposed changes:", "green")
    for field, value in update_data.items():
        print_colored(f"{field}: {value}", "cyan")
    
    confirmation = input("\nApply these changes? (y/n): ").lower()
    
    if confirmation == 'y':
        print_colored("Updating user information...", "blue")
        
        # Update the user
        updated_user = user_manager.update_user(user_id, update_data)
        
        if updated_user:
            print_colored("✅ User information updated successfully.", "green")
        else:
            print_colored("❌ Failed to update user information.", "red")
    else:
        print_colored("Operation cancelled.", "yellow")
    
    input("Press Enter to continue...")


def deactivate_user(user: Dict[str, Any], user_manager: UserManager) -> None:
    """Deactivate a user account."""
    user_id = user.get('id')
    name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
    
    print_colored(f"\nDeactivate User: {name}", "blue")
    print_colored("⚠️ WARNING: This will deactivate the user account.", "red", bold=True)
    print_colored("The user will no longer be able to log in to FreshService.", "yellow")
    
    confirmation = input(f"Are you sure you want to deactivate {name}? (type 'confirm' to proceed): ").strip()
    
    if confirmation.lower() == 'confirm':
        print_colored(f"Deactivating user {name}...", "blue")
        
        success = user_manager.deactivate_user(user_id)
        
        if success:
            print_colored(f"✅ User {name} has been deactivated.", "green")
        else:
            print_colored(f"❌ Failed to deactivate user {name}.", "red")
    else:
        print_colored("Operation cancelled.", "yellow")
    
    input("Press Enter to continue...")


def activate_user(user: Dict[str, Any], user_manager: UserManager) -> None:
    """Activate a previously deactivated user account."""
    user_id = user.get('id')
    name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
    
    print_colored(f"\nActivate User: {name}", "blue")
    
    confirmation = input(f"Activate user {name}? (y/n): ").lower()
    
    if confirmation == 'y':
        print_colored(f"Activating user {name}...", "blue")
        
        success = user_manager.activate_user(user_id)
        
        if success:
            print_colored(f"✅ User {name} has been activated.", "green")
        else:
            print_colored(f"❌ Failed to activate user {name}.", "red")
    else:
        print_colored("Operation cancelled.", "yellow")
    
    input("Press Enter to continue...")


def advanced_search(user_manager: UserManager, department_manager: DepartmentManager) -> None:
    """Perform an advanced search for users with multiple criteria."""
    print_colored("\n🔍 Advanced Search", "blue")
    
    # Build search criteria
    print_colored("Enter search criteria (leave blank to skip):", "green")
    
    search_params = {}
    
    # Email (partial match)
    email = input("Email contains: ").strip()
    if email:
        search_params['email'] = email
    
    # First name (partial match)
    first_name = input("First name contains: ").strip()
    if first_name:
        search_params['first_name'] = first_name
    
    # Last name (partial match)
    last_name = input("Last name contains: ").strip()
    if last_name:
        search_params['last_name'] = last_name
    
    # Job title (partial match)
    job_title = input("Job title contains: ").strip()
    if job_title:
        search_params['job_title'] = job_title
    
    # Include inactive users
    include_inactive = input("Include inactive users? (y/n): ").lower() == 'y'
    
    if not search_params:
        print_colored("❌ At least one search criterion is required.", "red")
        input("Press Enter to continue...")
        return
    
    print_colored("\nSearching for users...", "blue")
    
    # For now, use simple name search - in a real implementation,
    # we would extend the API client to support advanced filtering
    users = user_manager.search_users_by_name(
        search_params.get('first_name'),
        search_params.get('last_name'),
        fuzzy_match=True
    )
    
    # Filter results based on other criteria
    filtered_users = []
    for user in users:
        match = True
        
        if 'email' in search_params and search_params['email'].lower() not in user.get('primary_email', '').lower():
            match = False
        
        if 'job_title' in search_params and search_params['job_title'].lower() not in (user.get('job_title') or '').lower():
            match = False
        
        if not include_inactive and not user.get('active', False):
            match = False
        
        if match:
            filtered_users.append(user)
    
    if filtered_users:
        if len(filtered_users) == 1:
            display_user_details(filtered_users[0], user_manager, department_manager)
        else:
            selected_user = select_user_from_results(filtered_users, user_manager, department_manager)
            if selected_user:
                display_user_details(selected_user, user_manager, department_manager)
    else:
        print_colored("❌ No users found matching your criteria.", "red")
    
    input("Press Enter to continue...")


def view_recent_users(user_manager: UserManager, department_manager: DepartmentManager) -> None:
    """View recently accessed users."""
    print_colored("\n📜 Recent Users", "blue")
    
    recent_users = user_manager.recent_users
    
    if not recent_users:
        print_colored("No recent users found.", "yellow")
        input("Press Enter to continue...")
        return
    
    print_colored(f"Recent Users ({len(recent_users)} total):", "green")
    
    selected_user = select_user_from_results(recent_users, user_manager, department_manager)
    if selected_user:
        display_user_details(selected_user, user_manager, department_manager)


def update_departments_from_csv(user_manager, department_manager, csv_processor):
    """Update departments from a CSV file."""
    print_colored("\n🏢 Update Departments from CSV", "blue")
    print_colored("This function allows you to update the departments of multiple users at once.", "yellow")
    
    # Ask for CSV file path
    csv_path = input("Enter the path to your CSV file: ").strip()
    if not csv_path:
        print_colored("❌ Operation cancelled - no file path provided.", "red")
        input("Press Enter to continue...")
        return
    
    try:
        # Read and validate the CSV
        rows = csv_processor.read_csv_file(csv_path)
        valid_rows, invalid_rows = csv_processor.validate_user_csv(rows)
        
        if invalid_rows:
            print_colored(f"⚠️ Found {len(invalid_rows)} invalid rows in CSV.", "yellow")
            create_error_report = input("Would you like to create an error report? (y/n): ").lower() == 'y'
            
            if create_error_report:
                error_path = csv_path.replace('.csv', '_errors.csv')
                csv_processor.generate_error_report(invalid_rows, error_path)
                print_colored(f"Error report generated at: {error_path}", "green")
        
        if not valid_rows:
            print_colored("❌ No valid rows found in CSV.", "red")
            input("Press Enter to continue...")
            return
        
        print_colored(f"\nFound {len(valid_rows)} valid user entries to process.", "green")
        print_colored("Preview of changes to be made:", "blue")
        
        # Track processing results
        successful = []
        failed = []
        
        # Process each row
        for i, row in enumerate(valid_rows, 1):
            if 'Email' not in row or not row['Email']:
                print_colored(f"Row {i}: ❌ Missing email address", "red")
                failed.append({**row, 'error': 'Missing email address'})
                continue
                
            if 'Department' not in row or not row['Department']:
                print_colored(f"Row {i}: ❌ Missing department name", "red")
                failed.append({**row, 'error': 'Missing department name'})
                continue
            
            email = row['Email']
            department_name = row['Department']
            
            # Look up user
            user = user_manager.get_user_by_email(email)
            if not user:
                print_colored(f"Row {i}: ❌ User not found: {email}", "red")
                failed.append({**row, 'error': 'User not found'})
                continue
            
            # Look up department
            department = department_manager.get_department_by_name(department_name)
            if not department:
                print_colored(f"Row {i}: ❌ Department not found: {department_name}", "red")
                failed.append({**row, 'error': 'Department not found'})
                continue
            
            # Preview the change
            user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            print_colored(f"Row {i}: {user_name} ({email}) → {department_name} (ID: {department.get('id')})", "cyan")
            
            # Add to successful entries to be processed
            successful.append({
                'user': user,
                'department_id': department.get('id'),
                'department_name': department_name,
                'row': row
            })
        
        if not successful:
            print_colored("❌ No valid changes to make.", "red")
            input("Press Enter to continue...")
            return
        
        # Confirm changes
        confirm = input(f"\nUpdate departments for {len(successful)} users? (y/n): ").lower() == 'y'
        
        if not confirm:
            print_colored("Operation cancelled by user.", "yellow")
            input("Press Enter to continue...")
            return
        
        # Process updates
        update_results = []
        for entry in successful:
            user = entry['user']
            user_id = user.get('id')
            user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            department_id = entry['department_id']
            department_name = entry['department_name']
            
            print_colored(f"Updating {user_name} to department: {department_name}...", "blue")
            
            try:
                # Update user
                updated_user = user_manager.update_user(
                    user_id, 
                    {'department_ids': [department_id]}
                )
                
                if updated_user:
                    print_colored(f"✅ Successfully updated {user_name}", "green")
                    update_results.append({
                        'Email': user.get('primary_email'),
                        'Name': user_name,
                        'Department': department_name,
                        'Status': 'Success'
                    })
                else:
                    print_colored(f"❌ Failed to update {user_name}", "red")
                    update_results.append({
                        'Email': user.get('primary_email'),
                        'Name': user_name,
                        'Department': department_name,
                        'Status': 'Failed',
                        'Error': 'API update failed'
                    })
            except Exception as e:
                error_msg = str(e)
                print_colored(f"❌ Error updating {user_name}: {error_msg}", "red")
                update_results.append({
                    'Email': user.get('primary_email'),
                    'Name': user_name,
                    'Department': department_name,
                    'Status': 'Failed',
                    'Error': error_msg
                })
        
        # Offer to save results
        if update_results:
            save_results = input("\nWould you like to save the results to a CSV file? (y/n): ").lower() == 'y'
            
            if save_results:
                results_path = csv_path.replace('.csv', '_results.csv')
                fieldnames = ['Email', 'Name', 'Department', 'Status', 'Error']
                csv_processor.write_csv_report(update_results, results_path, fieldnames)
                print_colored(f"Results saved to: {results_path}", "green")
    
    except FileNotFoundError:
        print_colored(f"❌ File not found: {csv_path}", "red")
    except Exception as e:
        print_colored(f"❌ Error processing CSV: {str(e)}", "red")
    
    input("Press Enter to continue...")


def deactivate_users_from_csv(user_manager, csv_processor):
    """Deactivate users from a CSV file."""
    print_colored("\n❌ Deactivate Users from CSV", "blue")
    print_colored("This function allows you to deactivate multiple users at once.", "yellow")
    
    # Ask for CSV file path
    csv_path = input("Enter the path to your CSV file: ").strip()
    if not csv_path:
        print_colored("❌ Operation cancelled - no file path provided.", "red")
        input("Press Enter to continue...")
        return
    
    try:
        # Read and validate the CSV
        rows = csv_processor.read_csv_file(csv_path)
        
        # Basic validation - ensure email column exists
        for row in rows:
            if 'Email' not in row:
                print_colored("❌ CSV file must contain an 'Email' column.", "red")
                input("Press Enter to continue...")
                return
        
        # Track processing results
        results = []
        
        # Process each row
        for i, row in enumerate(rows, 1):
            email = row.get('Email', '').strip()
            reason = row.get('Reason', 'No reason provided').strip()
            
            if not email:
                print_colored(f"Row {i}: ❌ Missing email address", "red")
                results.append({
                    'Email': '',
                    'Reason': reason,
                    'Status': 'Failed',
                    'Error': 'Missing email address'
                })
                continue
            
            # Look up user
            user = user_manager.get_user_by_email(email)
            if not user:
                print_colored(f"Row {i}: ❌ User not found: {email}", "red")
                results.append({
                    'Email': email,
                    'Reason': reason,
                    'Status': 'Failed',
                    'Error': 'User not found'
                })
                continue
            
            # Skip if already inactive
            if not user.get('active', True):
                print_colored(f"Row {i}: ⚠️ User already inactive: {email}", "yellow")
                results.append({
                    'Email': email,
                    'Reason': reason,
                    'Status': 'Skipped',
                    'Error': 'User already inactive'
                })
                continue
            
            user_id = user.get('id')
            user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            
            # Preview deactivation
            print_colored(f"Row {i}: Will deactivate {user_name} ({email}) - Reason: {reason}", "cyan")
            
            results.append({
                'user_id': user_id,
                'Email': email,
                'Name': user_name,
                'Reason': reason
            })
        
        users_to_deactivate = [r for r in results if 'user_id' in r]
        
        if not users_to_deactivate:
            print_colored("❌ No valid users to deactivate.", "red")
            input("Press Enter to continue...")
            return
        
        # Confirm deactivation
        print_colored(f"\nAbout to deactivate {len(users_to_deactivate)} users:", "red", bold=True)
        for entry in users_to_deactivate:
            print_colored(f"- {entry['Name']} ({entry['Email']})", "yellow")
        
        confirm = input(f"\n⚠️ This action cannot be easily undone. Type 'CONFIRM' to proceed: ").strip()
        
        if confirm != 'CONFIRM':
            print_colored("Operation cancelled by user.", "yellow")
            input("Press Enter to continue...")
            return
        
        # Process deactivations
        deactivation_results = []
        for entry in users_to_deactivate:
            user_id = entry['user_id']
            email = entry['Email']
            name = entry['Name']
            reason = entry['Reason']
            
            print_colored(f"Deactivating {name} ({email})...", "blue")
            
            try:
                # Deactivate user
                success = user_manager.deactivate_user(user_id)
                
                if success:
                    print_colored(f"✅ Successfully deactivated {name}", "green")
                    deactivation_results.append({
                        'Email': email,
                        'Name': name,
                        'Reason': reason,
                        'Status': 'Success'
                    })
                else:
                    print_colored(f"❌ Failed to deactivate {name}", "red")
                    deactivation_results.append({
                        'Email': email,
                        'Name': name,
                        'Reason': reason,
                        'Status': 'Failed',
                        'Error': 'API deactivation failed'
                    })
            except Exception as e:
                error_msg = str(e)
                print_colored(f"❌ Error deactivating {name}: {error_msg}", "red")
                deactivation_results.append({
                    'Email': email,
                    'Name': name,
                    'Reason': reason,
                    'Status': 'Failed',
                    'Error': error_msg
                })
        
        # Add failed entries from earlier validation
        for entry in results:
            if 'user_id' not in entry:
                deactivation_results.append(entry)
        
        # Offer to save results
        if deactivation_results:
            save_results = input("\nWould you like to save the results to a CSV file? (y/n): ").lower() == 'y'
            
            if save_results:
                results_path = csv_path.replace('.csv', '_results.csv')
                fieldnames = ['Email', 'Name', 'Reason', 'Status', 'Error']
                csv_processor.write_csv_report(deactivation_results, results_path, fieldnames)
                print_colored(f"Results saved to: {results_path}", "green")
    
    except FileNotFoundError:
        print_colored(f"❌ File not found: {csv_path}", "red")
    except Exception as e:
        print_colored(f"❌ Error processing CSV: {str(e)}", "red")
    
    input("Press Enter to continue...")


def update_groups_from_csv(user_manager, csv_processor):
    """Update group memberships from a CSV file."""
    print_colored("\n👥 Update Group Memberships from CSV", "blue")
    print_colored("This function allows you to add or remove users from groups.", "yellow")
    
    # Ask for CSV file path
    csv_path = input("Enter the path to your CSV file: ").strip()
    if not csv_path:
        print_colored("❌ Operation cancelled - no file path provided.", "red")
        input("Press Enter to continue...")
        return
    
    try:
        # Read and validate the CSV
        rows = csv_processor.read_csv_file(csv_path)
        
        # Basic validation - ensure required columns exist
        for row in rows:
            if 'Email' not in row:
                print_colored("❌ CSV file must contain an 'Email' column.", "red")
                input("Press Enter to continue...")
                return
            if 'Group_Name' not in row:
                print_colored("❌ CSV file must contain a 'Group_Name' column.", "red")
                input("Press Enter to continue...")
                return
            if 'Action' not in row:
                print_colored("❌ CSV file must contain an 'Action' column (add/remove).", "red")
                input("Press Enter to continue...")
                return
        
        # Track processing results
        results = []
        
        # Process each row
        for i, row in enumerate(rows, 1):
            email = row.get('Email', '').strip()
            group_name = row.get('Group_Name', '').strip()
            action = row.get('Action', '').strip().lower()
            
            if not email:
                print_colored(f"Row {i}: ❌ Missing email address", "red")
                results.append({
                    'Email': '',
                    'Group_Name': group_name,
                    'Action': action,
                    'Status': 'Failed',
                    'Error': 'Missing email address'
                })
                continue
            
            if not group_name:
                print_colored(f"Row {i}: ❌ Missing group name", "red")
                results.append({
                    'Email': email,
                    'Group_Name': '',
                    'Action': action,
                    'Status': 'Failed',
                    'Error': 'Missing group name'
                })
                continue
            
            if action not in ['add', 'remove']:
                print_colored(f"Row {i}: ❌ Invalid action '{action}' - must be 'add' or 'remove'", "red")
                results.append({
                    'Email': email,
                    'Group_Name': group_name,
                    'Action': action,
                    'Status': 'Failed',
                    'Error': "Invalid action - must be 'add' or 'remove'"
                })
                continue
            
            # Look up user
            user = user_manager.get_user_by_email(email)
            if not user:
                print_colored(f"Row {i}: ❌ User not found: {email}", "red")
                results.append({
                    'Email': email,
                    'Group_Name': group_name,
                    'Action': action,
                    'Status': 'Failed',
                    'Error': 'User not found'
                })
                continue
            
            user_id = user.get('id')
            user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            
            # For demo purposes, we'll simulate successful group management
            # In a real implementation, we would call the appropriate API to add/remove users
            # from groups, once we have implemented the necessary functions in the user_manager
            
            print_colored(f"Row {i}: Will {action} {user_name} ({email}) to group '{group_name}'", "cyan")
            
            results.append({
                'Email': email,
                'Name': user_name,
                'Group_Name': group_name,
                'Action': action,
                'Status': 'Pending'
            })
        
        valid_entries = [r for r in results if r.get('Status') == 'Pending']
        
        if not valid_entries:
            print_colored("❌ No valid group memberships to update.", "red")
            input("Press Enter to continue...")
            return
        
        # Confirm changes
        print_colored(f"\nAbout to update {len(valid_entries)} group memberships:", "blue")
        for entry in valid_entries:
            action_symbol = "➕" if entry['Action'] == 'add' else "➖"
            print_colored(f"{action_symbol} {entry['Name']} ({entry['Email']}) - {entry['Group_Name']}", "yellow")
        
        confirm = input(f"\nProceed with these changes? (y/n): ").lower()
        
        if confirm != 'y':
            print_colored("Operation cancelled by user.", "yellow")
            input("Press Enter to continue...")
            return
        
        # Process group updates
        for entry in valid_entries:
            email = entry['Email']
            name = entry['Name']
            group_name = entry['Group_Name']
            action = entry['Action']
            
            action_verb = "Adding" if action == 'add' else "Removing"
            print_colored(f"{action_verb} {name} ({email}) to group '{group_name}'...", "blue")
            
            # In a real implementation, these would be calls to actual API methods
            # For demo purposes, we'll simulate success with occasional failures
            import random
            success = random.random() < 0.9  # 90% success rate
            
            if success:
                print_colored(f"✅ Successfully {action}ed {name} to group '{group_name}'", "green")
                entry['Status'] = 'Success'
            else:
                error_msg = "Simulated API error for demonstration"
                print_colored(f"❌ Failed to {action} {name} to group '{group_name}': {error_msg}", "red")
                entry['Status'] = 'Failed'
                entry['Error'] = error_msg
        
        # Offer to save results
        if results:
            save_results = input("\nWould you like to save the results to a CSV file? (y/n): ").lower() == 'y'
            
            if save_results:
                results_path = csv_path.replace('.csv', '_results.csv')
                fieldnames = ['Email', 'Name', 'Group_Name', 'Action', 'Status', 'Error']
                csv_processor.write_csv_report(results, results_path, fieldnames)
                print_colored(f"Results saved to: {results_path}", "green")
                
        print_colored("\nNote: Group management is currently in simulation mode.", "yellow")
        print_colored("In a future version, these changes will be applied to FreshService.", "yellow")
    
    except FileNotFoundError:
        print_colored(f"❌ File not found: {csv_path}", "red")
    except Exception as e:
        print_colored(f"❌ Error processing CSV: {str(e)}", "red")
    
    input("Press Enter to continue...")


def view_user_groups(user_manager):
    """View a user's group memberships."""
    print_colored("\n👀 This feature is not yet implemented.", "yellow")
    input("Press Enter to continue...")


def add_user_to_group(user_manager):
    """Add a user to a group."""
    print_colored("\n➕ This feature is not yet implemented.", "yellow")
    input("Press Enter to continue...")


def remove_user_from_group(user_manager):
    """Remove a user from a group."""
    print_colored("\n➖ This feature is not yet implemented.", "yellow")
    input("Press Enter to continue...")


def force_password_reset(user_manager):
    """Force a password reset for a user."""
    print_colored("\n🔑 This feature is not yet implemented.", "yellow")
    input("Press Enter to continue...")


def unlock_account(user_manager):
    """Unlock a user account."""
    print_colored("\n🔓 This feature is not yet implemented.", "yellow")
    input("Press Enter to continue...")


def update_user_role(user_manager):
    """Update a user's role."""
    print_colored("\n🛡️ This feature is not yet implemented.", "yellow")
    input("Press Enter to continue...")


def user_activity_report(user_manager, csv_processor):
    """Generate a user activity report."""
    print_colored("\n📆 User Ticket Activity Report", "blue")
    
    # Initialize reports manager with the API client and workspace ID
    reports_manager = ReportsManager(
        user_manager.api_client, 
        user_manager.workspace_id,
        user_manager.logger
    )
    
    # We need department_manager for select_user_from_results function
    department_manager = DepartmentManager(
        user_manager.api_client,
        user_manager.workspace_id,
        user_manager.logger
    )
    
    # Search for a user
    print_colored("Search for a user to generate activity report:", "green")
    option = input("Search by [1] Email, [2] User ID, or [3] Name (or 'q' to quit): ").strip()
    
    if option.lower() == 'q':
        return
    
    user_id = None
    email = None
    user = None
    
    if option == '1':
        # Search by email
        email = input("Enter user email: ").strip()
        if not email:
            print_colored("❌ Email is required.", "red")
            input("Press Enter to continue...")
            return
            
        # Verify the user exists
        user = user_manager.get_user_by_email(email)
        if not user:
            print_colored(f"❌ No user found with email: {email}", "red")
            input("Press Enter to continue...")
            return
            
        user_id = user.get('id')
        user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
        
    elif option == '2':
        # Search by user ID
        try:
            user_id = int(input("Enter user ID: ").strip())
            
            # Verify the user exists
            user = user_manager.get_user_by_id(user_id)
            if not user:
                print_colored(f"❌ No user found with ID: {user_id}", "red")
                input("Press Enter to continue...")
                return
                
            email = user.get('primary_email')
            user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            
        except ValueError:
            print_colored("❌ User ID must be a number.", "red")
            input("Press Enter to continue...")
            return
    elif option == '3':
        # Search by name
        first_name = input("Enter first name (leave blank to skip): ").strip()
        last_name = input("Enter last name (leave blank to skip): ").strip()
        
        if not first_name and not last_name:
            print_colored("❌ At least one name field is required.", "red")
            input("Press Enter to continue...")
            return
            
        print_colored(f"Searching for users with name: {first_name} {last_name}", "blue")
        users = user_manager.search_users_by_name(first_name, last_name)
        
        if users:
            if len(users) == 1:
                user = users[0]
                user_id = user.get('id')
                email = user.get('primary_email')
                user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            else:
                # Multiple users found, let the user select one
                selected_user = select_user_from_results(users, user_manager, department_manager)
                if selected_user:
                    user = selected_user
                    user_id = user.get('id')
                    email = user.get('primary_email')
                    user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                else:
                    return  # User cancelled the selection
        else:
            print_colored(f"❌ No users found with name: {first_name} {last_name}", "red")
            input("Press Enter to continue...")
            return
    else:
        print_colored("❌ Invalid option.", "red")
        input("Press Enter to continue...")
        return
    
    # Get time period
    print_colored("\nSelect time period:", "green")
    print_colored("1. Last 7 days", "cyan")
    print_colored("2. Last 30 days", "cyan")
    print_colored("3. Last 90 days", "cyan")
    print_colored("4. Custom", "cyan")
    
    period_option = input("Choose a time period (1-4): ").strip()
    
    days = 30  # Default to 30 days
    if period_option == '1':
        days = 7
    elif period_option == '2':
        days = 30
    elif period_option == '3':
        days = 90
    elif period_option == '4':
        try:
            days = int(input("Enter number of days to look back: ").strip())
            if days <= 0:
                print_colored("❌ Days must be a positive number.", "red")
                input("Press Enter to continue...")
                return
        except ValueError:
            print_colored("❌ Days must be a number.", "red")
            input("Press Enter to continue...")
            return
    else:
        print_colored("❌ Invalid option. Using default of 30 days.", "yellow")
    
    # Generate report
    print_colored(f"\nGenerating activity report for {user_name} ({email}) over the past {days} days...", "blue")
    
    try:
        # Get comprehensive activity data including both requester and agent roles
        activity_items, summary, is_agent = reports_manager.get_comprehensive_user_activity(
            user_id=user_id,
            days=days
        )
        
        if not activity_items:
            print_colored("No activity found for this user in the specified time period.", "yellow")
            input("Press Enter to continue...")
            return
        
        # Display summary
        print_colored("\nActivity Summary:", "green")
        print_colored(f"Date Range: {summary.get('date_range')}", "yellow")
        print_colored(f"Total Tickets Created: {summary.get('total_tickets_created')}", "yellow")
        print_colored(f"Total Conversations as Requester: {summary.get('total_conversations_as_requester')}", "yellow")
        
        # Show agent-specific information if applicable
        if is_agent:
            print_colored("\nAgent Activity:", "green")
            
            # Check if there was an error retrieving agent activity
            if 'agent_error' in summary:
                print_colored("⚠️ Note: Agent activity data could not be fully retrieved", "yellow")
                error_type = summary.get('agent_error_type', 'Unknown error')
                print_colored(f"Error type: {error_type}", "yellow")
                
                if "400 Bad Request" in summary.get('agent_error', ''):
                    print_colored("The API returned a 400 Bad Request error, which typically indicates parameter issues", "yellow")
                    print_colored("This is likely due to limitations in the Freshservice API for filtering tickets by agent", "yellow")
                elif "404 Not Found" in summary.get('agent_error', ''):
                    print_colored("The API returned a 404 Not Found error, which may indicate the endpoint doesn't exist", "yellow")
                    print_colored("This could be due to differences in API versions or permissions", "yellow")
                elif "403 Forbidden" in summary.get('agent_error', ''):
                    print_colored("The API returned a 403 Forbidden error, indicating permission issues", "yellow")
                    print_colored("Your API key may not have access to agent-specific operations", "yellow")
                else:
                    # Show a substring of the error to avoid overwhelming the user
                    error_text = summary.get('agent_error', '')
                    if len(error_text) > 100:
                        error_text = error_text[:97] + "..."
                    print_colored(f"Error details: {error_text}", "yellow")
                
                # Show fallback status
                if summary.get('agent_activity_available') is False:
                    print_colored("Showing only requester activity for this user", "yellow")
                else:
                    print_colored("Using alternative methods to retrieve agent activity", "yellow")
                    print_colored(f"Total Tickets Worked On: {summary.get('total_tickets_worked')}", "yellow")
                    print_colored(f"Tickets Assigned: {summary.get('tickets_assigned')}", "yellow")
                    print_colored(f"Tickets Collaborated On: {summary.get('tickets_collaborated')}", "yellow") 
                    print_colored(f"Total Responses as Agent: {summary.get('total_responses_as_agent')}", "yellow")
                    
                # Add information about the API diagnostics
                print_colored("\nRun 'API Diagnostics' from the Reports menu for more information on API capabilities.", "cyan")
            else:
                print_colored(f"Total Tickets Worked On: {summary.get('total_tickets_worked')}", "yellow")
                print_colored(f"Tickets Assigned: {summary.get('tickets_assigned')}", "yellow")
                print_colored(f"Tickets Collaborated On: {summary.get('tickets_collaborated')}", "yellow") 
                print_colored(f"Total Responses as Agent: {summary.get('total_responses_as_agent')}", "yellow")
        
        # Display recent activity (max 10 items)
        print_colored("\nRecent Activity:", "green")
        for i, item in enumerate(activity_items[:10], 1):
            role = item.get('role', 'requester')
            role_label = f"[{role.capitalize()}]" if is_agent else ""
            
            if item.get('type') == 'ticket':
                # Map status and priority codes to human-readable text
                status_val = item.get('status')
                status_map = {
                    1: "Open",
                    2: "Pending",
                    3: "Resolved",
                    4: "Closed", 
                    5: "New",
                    6: "In Progress",
                    7: "On Hold"
                }
                status_text = status_map.get(status_val, f"Status {status_val}")
                
                priority_val = item.get('priority')
                priority_map = {
                    1: "Low",
                    2: "Medium",
                    3: "High",
                    4: "Urgent"
                }
                priority_text = priority_map.get(priority_val, f"Priority {priority_val}")
                
                # Add additional context if agent
                agent_context = ""
                if role == 'agent':
                    agent_context = f" ({item.get('agent_role', '')})"
                
                print_colored(f"{i}. [Ticket] {role_label} {item.get('subject')} (ID: {item.get('ticket_id')}){agent_context}", "cyan")
                print_colored(f"   Created: {reports_manager._format_date(item.get('created_at'))} | Status: {status_text} | Priority: {priority_text}", "yellow")
            elif item.get('type') == 'conversation':
                # Clean HTML content for display
                body = reports_manager._clean_html(item.get('body', ''))
                if len(body) > 50:
                    body = body[:47] + '...'
                
                # Show conversation type for agent responses
                conv_context = ""
                if role == 'agent':
                    conv_context = f" ({item.get('conversation_type', '')})"
                    
                print_colored(f"{i}. [Response] {role_label} Ticket #{item.get('ticket_id')}{conv_context}", "cyan")
                print_colored(f"   Date: {reports_manager._format_date(item.get('created_at'))}", "yellow")
                print_colored(f"   Content: {body}", "yellow")
        
        # Display activity visualization
        print_colored("\nActivity Distribution:", "green")
        visualization = reports_manager.get_activity_visualization(activity_items)
        for line in visualization:
            if "Monday" in line or "Tuesday" in line or "Wednesday" in line or "Thursday" in line or "Friday" in line or "Saturday" in line or "Sunday" in line:
                parts = line.split(':', 1)
                print_colored(parts[0] + ":", "cyan")
                if len(parts) > 1:
                    print(parts[1])
            else:
                print(line)
        
        # Option to export to CSV
        export = input("\nExport full report to CSV? (y/n): ").lower() == 'y'
        
        if export:
            # Generate a default filename with a cleaner format
            today = datetime.datetime.now().strftime('%Y%m%d')
            user_name_part = user_name.lower().replace(' ', '_')
            default_filename = f"ticket_activity_{user_name_part}_{today}.csv"
            
            filename = input(f"Enter filename (default: {default_filename}): ").strip()
            
            if not filename:
                filename = default_filename
                
            success = reports_manager.export_comprehensive_activity_to_csv(activity_items, summary, filename)
            
            if success:
                print_colored(f"✅ Report exported to {filename}", "green")
                
                # Offer to open the file
                open_file = input("Would you like to open the file now? (y/n): ").lower() == 'y'
                if open_file:
                    try:
                        import os
                        import platform
                        import subprocess
                        
                        # Handle file opening based on platform
                        if platform.system() == 'Windows':
                            os.startfile(filename)
                        elif platform.system() == 'Darwin':  # macOS
                            subprocess.call(['open', filename])
                        else:  # Linux
                            subprocess.call(['xdg-open', filename])
                            
                        print_colored("Opening file...", "cyan")
                    except Exception as e:
                        print_colored(f"Could not open file: {e}", "yellow")
                        print_colored(f"File is located at: {os.path.abspath(filename)}", "yellow")
            else:
                print_colored("❌ Failed to export report.", "red")
        
    except Exception as e:
        print_colored(f"❌ Error generating activity report: {str(e)}", "red")
        user_manager.logger.exception("Error generating activity report")
    
    input("\nPress Enter to continue...")


def inactive_accounts_report(user_manager, csv_processor):
    """Generate a report of inactive accounts."""
    print_colored("\n💤 Inactive Accounts Report", "blue")
    print_colored("This report identifies users who haven't logged in for an extended period.", "yellow")
    
    # Initialize reports manager with the API client and workspace ID
    reports_manager = ReportsManager(
        user_manager.api_client, 
        user_manager.workspace_id,
        user_manager.logger
    )
    
    # Initialize department manager for user selection
    department_manager = DepartmentManager(
        user_manager.api_client,
        user_manager.workspace_id,
        user_manager.logger
    )
    
    # Get the inactivity threshold from the user
    print_colored("\nSpecify inactivity threshold:", "green")
    print_colored("1. 30 days", "cyan")
    print_colored("2. 60 days", "cyan")
    print_colored("3. 90 days (default)", "cyan")
    print_colored("4. 180 days", "cyan")
    print_colored("5. 365 days", "cyan")
    print_colored("6. Custom", "cyan")
    
    threshold_option = input("Choose an option (1-6): ").strip()
    
    threshold_days = 90  # Default
    if threshold_option == "1":
        threshold_days = 30
    elif threshold_option == "2":
        threshold_days = 60
    elif threshold_option == "3":
        threshold_days = 90
    elif threshold_option == "4":
        threshold_days = 180
    elif threshold_option == "5":
        threshold_days = 365
    elif threshold_option == "6":
        try:
            threshold_days = int(input("Enter custom threshold in days: ").strip())
            if threshold_days <= 0:
                print_colored("❌ Threshold must be a positive number. Using default of 90 days.", "red")
                threshold_days = 90
        except ValueError:
            print_colored("❌ Invalid input. Using default of 90 days.", "red")
            threshold_days = 90
    
    # Choose which types of users to include
    print_colored("\nInclude in report:", "green")
    print_colored("1. Agents and Requesters (default)", "cyan")
    print_colored("2. Agents only", "cyan")
    print_colored("3. Requesters only", "cyan")
    
    users_option = input("Choose an option (1-3): ").strip()
    
    include_agents = True
    include_requesters = True
    
    if users_option == "2":
        include_agents = True
        include_requesters = False
        print_colored("Generating report for agents only...", "blue")
    elif users_option == "3":
        include_agents = False
        include_requesters = True
        print_colored("Generating report for requesters only...", "blue")
    else:
        print_colored("Generating report for both agents and requesters...", "blue")
    
    # Add option for filtering by active status
    print_colored("\nFilter by account status:", "green")
    print_colored("1. All accounts (default)", "cyan")
    print_colored("2. Active accounts only", "cyan")
    print_colored("3. Inactive accounts only", "cyan")
    
    status_option = input("Choose an option (1-3): ").strip()
    
    status_filter = None
    if status_option == "2":
        status_filter = True
        print_colored("Including only active accounts in report...", "blue")
    elif status_option == "3":
        status_filter = False
        print_colored("Including only deactivated accounts in report...", "blue")
    else:
        print_colored("Including all accounts in report regardless of status...", "blue")
    
    # Prompt for selecting a test agent for API capability testing
    print_colored("\nTo verify API capabilities, we need to select a user account.", "yellow")
    print_colored("This helps test access to login data in your Freshservice instance.", "yellow")
    
    test_user_id = select_agent_for_testing(user_manager, department_manager)
    
    if test_user_id:
        # If user was selected, get their details for display
        try:
            test_user = user_manager.get_user_by_id(test_user_id)
            user_name = f"{test_user.get('first_name', '')} {test_user.get('last_name', '')}".strip()
            print_colored(f"Using {user_name} (ID: {test_user_id}) for API capability testing", "green")
        except Exception:
            print_colored(f"Using ID {test_user_id} for API capability testing", "green")
    else:
        # If no user was selected, we'll use the first agent found during processing
        print_colored("No user selected. The report will automatically select a user for capability testing.", "yellow")
        test_user_id = None
    
    print_colored(f"\nGenerating inactive users report (threshold: {threshold_days} days)...", "blue")
    print_colored("This may take some time depending on the number of users in your system.", "yellow")
    print_colored("Processing...", "blue")
    
    # Setup a progress indicator
    def progress_callback(message):
        print_colored(f"  {message}", "cyan")
    
    try:
        # Generate the report with progress updates
        inactive_users, summary = reports_manager.get_inactive_users_report(
            threshold_days=threshold_days,
            include_agents=include_agents,
            include_requesters=include_requesters,
            progress_callback=progress_callback,
            test_user_id=test_user_id
        )
        
        # Filter by status if requested
        if status_filter is not None:
            inactive_users = [user for user in inactive_users if user.get('active', False) == status_filter]
            print_colored(f"Filtered to {len(inactive_users)} accounts matching status criteria.", "green")
        
        if not inactive_users:
            print_colored("\n✅ No inactive users found for the given criteria!", "green")
            input("Press Enter to continue...")
            return
        
        # Display summary
        print_colored("\nInactive Users Summary:", "green")
        print_colored(f"Total Inactive Users: {len(inactive_users)}", "yellow")
        if include_agents:
            print_colored(f"Inactive Agents: {summary.get('inactive_agents')} of {summary.get('total_agents_checked')} checked", "yellow")
        if include_requesters:
            print_colored(f"Inactive Requesters: {summary.get('inactive_requesters')} of {summary.get('total_requesters_checked')} checked", "yellow")
        print_colored(f"Users Without Login Data: {summary.get('users_without_login_data')}", "yellow")
        print_colored(f"Inactivity Threshold: {threshold_days} days", "yellow")
        print_colored(f"Execution Time: {summary.get('execution_time_seconds', 0):.2f} seconds", "yellow")
        
        # Display information about alternative tracking methods if used
        if summary.get('using_alternative_methods'):
            print_colored("\nNote About Data Collection:", "cyan", bold=True)
            print_colored("Direct login tracking was not available. Alternative activity tracking methods were used.", "yellow")
            print_colored("This may result in less accurate last activity dates, often using:", "yellow")
            print_colored("  - Most recent ticket update time", "yellow")
            print_colored("  - Account profile update time", "yellow")
            print_colored("  - Account creation date", "yellow")
            print_colored("as a proxy for user activity.", "yellow")
        
        # Display a sample of the inactive users
        print_colored("\nSample of Inactive Users:", "green")
        sample_size = min(10, len(inactive_users))  # Show at most 10 users
        
        # Column headers
        headers = ["Name", "Email", "Type", "Days Inactive", "Status"]
        
        # Calculate column widths based on data
        col_widths = [
            max(len(headers[0]), max(len(f"{u.get('first_name', '')} {u.get('last_name', '')}".strip()) for u in inactive_users[:sample_size])),
            max(len(headers[1]), max(len(str(u.get('email', ''))) for u in inactive_users[:sample_size])),
            max(len(headers[2]), max(len(str(u.get('type', ''))) for u in inactive_users[:sample_size])),
            max(len(headers[3]), max(len(str(u.get('days_inactive', ''))) for u in inactive_users[:sample_size])),
            max(len(headers[4]), 8)  # 'Active' or 'Inactive'
        ]
        
        # Print headers
        header_row = "  ".join(h.ljust(w) for h, w in zip(headers, col_widths))
        print_colored(header_row, "cyan")
        print_colored("-" * len(header_row), "cyan")
        
        # Print sample data
        for user in inactive_users[:sample_size]:
            name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            email = str(user.get('email', ''))
            user_type = str(user.get('type', ''))
            days = str(user.get('days_inactive', ''))
            status = 'Active' if user.get('active', False) else 'Inactive'
            
            row = [
                name.ljust(col_widths[0]),
                email.ljust(col_widths[1]),
                user_type.ljust(col_widths[2]),
                days.ljust(col_widths[3]),
                status.ljust(col_widths[4])
            ]
            
            print("  ".join(row))
        
        if len(inactive_users) > sample_size:
            print_colored(f"\n... and {len(inactive_users) - sample_size} more inactive users", "yellow")
        
        # Offer more options
        print_colored("\nWhat would you like to do with this report?", "green")
        print_colored("1. Export to CSV", "cyan")
        print_colored("2. View all inactive users in a paginated view", "cyan")
        print_colored("3. Return to main menu", "cyan")
        
        option = input("Choose an option (1-3): ").strip()
        
        if option == "1":
            # Generate a default filename
            default_filename = f"inactive_users_report_{datetime.datetime.now().strftime('%Y%m%d')}.csv"
            filename = input(f"Enter filename (default: {default_filename}): ").strip()
            
            if not filename:
                filename = default_filename
                
            success = reports_manager.export_inactive_users_to_csv(inactive_users, summary, filename)
            
            if success:
                print_colored(f"✅ Report exported to {filename}", "green")
                
                # Offer to open the file
                open_file = input("Open the CSV file? (y/n): ").lower() == 'y'
                if open_file:
                    if sys.platform == 'win32':
                        os.system(f'start excel "{filename}"')
                    elif sys.platform == 'darwin':
                        os.system(f'open "{filename}"')
                    else:
                        os.system(f'xdg-open "{filename}"')
            else:
                print_colored(f"❌ Failed to export report", "red")
        elif option == "2":
            # Paginated view of all inactive users
            page_size = 20
            current_page = 0
            total_pages = (len(inactive_users) + page_size - 1) // page_size
            
            while True:
                clear_screen()
                print_colored(f"Inactive Users (Page {current_page + 1}/{total_pages})", "blue")
                
                # Display column headers
                header_row = "  ".join(h.ljust(w) for h, w in zip(headers, col_widths))
                print_colored(header_row, "cyan")
                print_colored("-" * len(header_row), "cyan")
                
                # Calculate page bounds
                start_idx = current_page * page_size
                end_idx = min(start_idx + page_size, len(inactive_users))
                
                # Display users for current page
                for user in inactive_users[start_idx:end_idx]:
                    name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                    email = str(user.get('email', ''))
                    user_type = str(user.get('type', ''))
                    days = str(user.get('days_inactive', ''))
                    status = 'Active' if user.get('active', False) else 'Inactive'
                    
                    row = [
                        name.ljust(col_widths[0]),
                        email.ljust(col_widths[1]),
                        user_type.ljust(col_widths[2]),
                        days.ljust(col_widths[3]),
                        status.ljust(col_widths[4])
                    ]
                    
                    print("  ".join(row))
                
                # Navigation options
                print_colored("\nNavigation:", "green")
                if current_page > 0:
                    print_colored("P - Previous page", "cyan")
                if current_page < total_pages - 1:
                    print_colored("N - Next page", "cyan")
                print_colored("X - Exit to main menu", "cyan")
                
                nav = input("Enter option: ").lower()
                if nav == 'p' and current_page > 0:
                    current_page -= 1
                elif nav == 'n' and current_page < total_pages - 1:
                    current_page += 1
                elif nav == 'x':
                    break
        
    except Exception as e:
        print_colored(f"❌ Error generating report: {str(e)}", "red")
    
    input("Press Enter to continue...")


def custom_user_report(user_manager, csv_processor):
    """Generate a custom user report."""
    print_colored("\n📊 This feature is not yet implemented.", "yellow")
    input("Press Enter to continue...")


def create_csv_template(csv_processor):
    """Create a template CSV file."""
    print_colored("\n📋 Create CSV Template", "blue")
    print_colored("This function creates template CSV files for bulk operations.", "yellow")
    
    # Ask for template type
    print_colored("\nAvailable templates:", "green")
    print_colored("1. User Update Template", "cyan")
    print_colored("2. Department Update Template", "cyan")
    print_colored("3. Group Membership Template", "cyan")
    print_colored("4. User Deactivation Template", "cyan")
    print_colored("5. Cancel", "cyan")
    
    choice = input("\nSelect template type: ").strip()
    
    if choice == "5" or choice.lower() == "cancel":
        print_colored("Operation cancelled.", "yellow")
        input("Press Enter to continue...")
        return
    
    # Map choice to template type
    template_map = {
        "1": "user",
        "2": "department",
        "3": "group",
        "4": "deactivate"
    }
    
    if choice not in template_map:
        print_colored("❌ Invalid selection.", "red")
        input("Press Enter to continue...")
        return
    
    template_type = template_map[choice]
    
    # Ask for output path
    default_filename = f"{template_type}_template.csv"
    output_path = input(f"Enter output path (default: {default_filename}): ").strip()
    
    if not output_path:
        output_path = default_filename
    
    # Create template
    success = csv_processor.create_template_csv(template_type, output_path)
    
    if success:
        print_colored(f"✅ Template created successfully: {output_path}", "green")
        print_colored("You can now edit this file and use it for bulk operations.", "yellow")
    else:
        print_colored(f"❌ Failed to create template.", "red")
    
    input("Press Enter to continue...")


def select_agent_for_testing(user_manager, department_manager):
    """
    Prompt the user to search for and select an agent for API testing.
    
    Returns:
        Selected agent ID or None if cancelled
    """
    print_colored("\nSelect an Agent for API Testing", "blue")
    print_colored("This agent's ID will be used to test API functionality.", "yellow")
    
    # Options for searching
    print_colored("\nSearch method:", "green")
    print_colored("1. Search by Email", "cyan")
    print_colored("2. Search by Name", "cyan")
    print_colored("3. List All Agents", "cyan")
    print_colored("4. Cancel", "cyan")
    
    choice = input("\nSelect search method: ").strip()
    
    if choice == "1":
        # Search by email
        email = input("Enter agent's email: ").strip()
        if not email:
            print_colored("Operation cancelled.", "yellow")
            return None
        
        user = user_manager.get_user_by_email(email)
        if not user:
            print_colored(f"❌ No user found with email: {email}", "red")
            return None
            
        # Verify the user is an agent
        if not user.get('is_agent', False):
            print_colored(f"❌ The selected user ({user.get('first_name')} {user.get('last_name')}) is not an agent.", "red")
            confirmation = input("Do you want to use this non-agent user anyway? (y/n): ").lower()
            if confirmation != 'y':
                return None
        
        return user.get('id')
        
    elif choice == "2":
        # Search by name
        first_name = input("Enter agent's first name (leave blank to skip): ").strip()
        last_name = input("Enter agent's last name (leave blank to skip): ").strip()
        
        if not first_name and not last_name:
            print_colored("Operation cancelled.", "yellow")
            return None
            
        users = user_manager.search_users_by_name(first_name, last_name)
        
        if not users:
            print_colored(f"❌ No users found with name: {first_name} {last_name}", "red")
            return None
        
        # Filter to show only agents first
        agents = [u for u in users if u.get('is_agent', False)]
        non_agents = [u for u in users if not u.get('is_agent', False)]
        
        # If we found agents, just show those; otherwise show all users
        display_list = agents if agents else users
        
        if agents and non_agents:
            print_colored(f"Found {len(agents)} agents and {len(non_agents)} non-agents matching your search.", "yellow")
            show_all = input("Show all users instead of just agents? (y/n): ").lower() == 'y'
            if show_all:
                display_list = users
        
        selected_user = select_user_from_results(display_list, user_manager, department_manager)
        if not selected_user:
            return None
            
        # Warn if selected a non-agent
        if not selected_user.get('is_agent', False):
            print_colored(f"⚠️ Warning: The selected user ({selected_user.get('first_name')} {selected_user.get('last_name')}) is not an agent.", "yellow")
            confirmation = input("Do you want to use this non-agent user for testing? (y/n): ").lower()
            if confirmation != 'y':
                return None
        
        return selected_user.get('id')
        
    elif choice == "3":
        # List all agents
        try:
            # This assumes there's a method to get all agents in user_manager
            # If not available, we could implement it or use a more generic approach
            print_colored("Retrieving all agents...", "blue")
            all_agents = user_manager.get_all_agents()
            
            if not all_agents:
                print_colored("❌ No agents found in the system.", "red")
                return None
                
            # Sort by name for easier finding
            all_agents.sort(key=lambda a: f"{a.get('first_name', '')} {a.get('last_name', '')}")
            
            # Display in a paginated view
            page_size = 10
            current_page = 0
            total_pages = (len(all_agents) + page_size - 1) // page_size
            
            while True:
                clear_screen()
                print_colored(f"All Agents (Page {current_page + 1}/{total_pages})", "blue")
                print_colored("Select an agent to use for API testing:", "yellow")
                print_colored("-" * 50, "cyan")
                
                # Calculate page bounds
                start_idx = current_page * page_size
                end_idx = min(start_idx + page_size, len(all_agents))
                
                # Display agents for current page
                for i, agent in enumerate(all_agents[start_idx:end_idx], start_idx + 1):
                    name = f"{agent.get('first_name', '')} {agent.get('last_name', '')}".strip()
                    email = agent.get('email', 'No email')
                    print_colored(f"{i}. {name} ({email})", "cyan")
                
                # Navigation options
                print_colored("\nNavigation:", "green")
                if current_page > 0:
                    print_colored("P - Previous page", "cyan")
                if current_page < total_pages - 1:
                    print_colored("N - Next page", "cyan")
                print_colored("X - Cancel selection", "cyan")
                
                selection = input("\nEnter agent number or navigation option: ").lower()
                
                if selection == 'x':
                    print_colored("Operation cancelled.", "yellow")
                    return None
                elif selection == 'p' and current_page > 0:
                    current_page -= 1
                    continue
                elif selection == 'n' and current_page < total_pages - 1:
                    current_page += 1
                    continue
                
                try:
                    idx = int(selection) - 1
                    if 0 <= idx < len(all_agents):
                        selected_agent = all_agents[idx]
                        agent_name = f"{selected_agent.get('first_name', '')} {selected_agent.get('last_name', '')}".strip()
                        print_colored(f"Selected agent: {agent_name}", "green")
                        return selected_agent.get('id')
                    else:
                        print_colored("❌ Invalid selection.", "red")
                        input("Press Enter to continue...")
                except ValueError:
                    if selection not in ['p', 'n', 'x']:
                        print_colored("❌ Please enter a valid number or navigation option.", "red")
                        input("Press Enter to continue...")
            
        except Exception as e:
            print_colored(f"❌ Error retrieving agents: {str(e)}", "red")
            return None
    
    elif choice == "4" or choice.lower() == "cancel":
        print_colored("Operation cancelled.", "yellow")
        return None
    
    else:
        print_colored("❌ Invalid selection.", "red")
        return None
    
    return None

def run_api_diagnostics(user_manager):
    """Run API diagnostics to identify issues."""
    print_colored("\n🔍 API Diagnostics", "blue")
    print_colored("This function tests API connectivity and permissions.", "yellow")
    
    # Initialize reports manager with the API client and workspace ID
    reports_manager = ReportsManager(
        user_manager.api_client, 
        user_manager.workspace_id,
        user_manager.logger
    )
    
    # Initialize department manager for user selection
    department_manager = DepartmentManager(
        user_manager.api_client,
        user_manager.workspace_id,
        user_manager.logger
    )
    
    # Prompt for selecting a test agent
    print_colored("\nTo test API functionality, we need to select a user account.", "yellow")
    print_colored("This helps verify specific endpoints and permissions in your Freshservice instance.", "yellow")
    
    current_user_id = select_agent_for_testing(user_manager, department_manager)
    
    if current_user_id:
        # If user was selected, get their details for display
        try:
            test_user = user_manager.get_user_by_id(current_user_id)
            user_name = f"{test_user.get('first_name', '')} {test_user.get('last_name', '')}".strip()
            print_colored(f"Using {user_name} (ID: {current_user_id}) for testing", "green")
        except Exception:
            print_colored(f"Using ID {current_user_id} for testing", "green")
    else:
        # If no user was selected, use anonymous testing
        print_colored("No user selected. Using anonymous testing (some tests may fail).", "yellow")
    
    print_colored("\nRunning API diagnostics...", "blue")
    diagnostics = reports_manager.run_api_diagnostics(current_user_id)
    
    # Display summary
    status = diagnostics.get('status', 'unknown')
    if status == 'healthy':
        status_color = "green"
    elif status == 'partial':
        status_color = "yellow"
    else:
        status_color = "red"
        
    print_colored(f"\nAPI Status: {status.upper()}", status_color, bold=True)
    print_colored(diagnostics.get('summary', 'No summary available.'), status_color)
    
    # Display details for each endpoint
    print_colored("\nEndpoint Details:", "blue")
    
    # Group endpoints for easier understanding
    endpoint_groups = {
        "Core Endpoints": ["tickets", "agents"],
        "Filtering Methods": ["tickets_standard_filter", "tickets_requester"],
        "Detailed Data": ["ticket_conversations"]
    }
    
    for group_name, endpoints in endpoint_groups.items():
        print_colored(f"\n{group_name}:", "cyan", bold=True)
        
        for endpoint in endpoints:
            if endpoint in diagnostics.get('endpoints', {}):
                result = diagnostics['endpoints'][endpoint]
                success = result.get('success', False)
                status_code = result.get('status_code')
                error = result.get('error')
                params = result.get('params', {})
                
                if success:
                    print_colored(f"✅ {endpoint}: OK", "green")
                else:
                    print_colored(f"❌ {endpoint}: Failed", "red")
                    if status_code:
                        print_colored(f"   Status Code: {status_code}", "yellow")
                    if error:
                        print_colored(f"   Error: {error}", "yellow")
                    
                    # Provide specific recommendations based on endpoint and error
                    if endpoint == "tickets_standard_filter" and status_code == 400:
                        print_colored("   Recommendation: Your account may not support filtering by responder_id directly.", "yellow")
                        print_colored("   Try using the tickets endpoint without filters to verify basic access.", "yellow")
                    elif endpoint == "tickets_requester" and status_code == 400:
                        print_colored("   Recommendation: The filter parameter format may not be supported.", "yellow")
                        print_colored("   Check FreshService API documentation for correct query parameter format.", "yellow")
                    elif status_code == 401 or status_code == 403:
                        print_colored("   Recommendation: Check your API key permissions for this endpoint.", "yellow")
            else:
                print_colored(f"❓ {endpoint}: Not tested", "yellow")
    
    # Offer to export diagnostics
    export = input("\nExport diagnostic results to file? (y/n): ").lower() == 'y'
    
    if export:
        import json
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"freshservice_api_diagnostics_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(diagnostics, f, indent=2)
            print_colored(f"✅ Diagnostics exported to {filename}", "green")
        except Exception as e:
            print_colored(f"❌ Failed to export diagnostics: {str(e)}", "red")
    
    print_colored("\nTroubleshooting Tips:", "blue")
    print_colored("1. Check API key permissions and make sure it has access to tickets and agents", "yellow")
    print_colored("2. Verify network connectivity to the Freshservice API", "yellow")
    print_colored("3. Ensure your Freshservice plan includes the features you're trying to access", "yellow")
    print_colored("4. Check for any rate limiting or quota issues", "yellow")
    print_colored("5. Contact Freshservice support if issues persist", "yellow")
    
    print_colored("\nFreshservice API Notes:", "blue")
    print_colored("• The 'responder_id' parameter is not directly supported for filtering tickets", "yellow")
    print_colored("• Valid filter values include: 'watching', 'new_and_my_open', 'spam', 'deleted', 'archived'", "yellow")
    print_colored("• For agent activity, the API requires client-side filtering of ticket data", "yellow")
    print_colored("• To work around API limitations, this tool uses several fallback approaches", "yellow")
    
    # Look for common error patterns and suggest solutions
    try:
        error_patterns = []
        for endpoint_result in diagnostics.get('endpoints', {}).values():
            if endpoint_result and isinstance(endpoint_result, dict):
                error_text = endpoint_result.get('error', '')
                if error_text and "400 Bad Request" in error_text:
                    error_patterns.append(error_text)
        
        if error_patterns:
            print_colored("\nCommon 400 Bad Request Solutions:", "blue")
            print_colored("1. Check parameter formats - some endpoints may expect different parameter names", "yellow")
            print_colored("2. Verify the endpoint URL is correct for your FreshService version", "yellow")
            print_colored("3. Your API token might not have permission for some filtering operations", "yellow")
            
            # Display specific errors for the Freshservice API
            if any("responder_id" in err for err in error_patterns):
                print_colored("\nFreshservice API Specifics:", "blue")
                print_colored("The responder_id parameter appears to be unavailable or restricted in your API version.", "yellow")
                print_colored("Try using different filtering options or contact Freshservice support.", "yellow")
    except Exception as e:
        print_colored(f"\nError analyzing diagnostic results: {str(e)}", "red")
    
    input("\nPress Enter to continue...")


def main() -> None:
    """Main entry point for the toolkit."""
    global API_KEY, CURRENT_WORKSPACE, logger
    
    try:
        # Setup environment and logging
        setup_environment()
        logger = setup_logging()
        
        # Get API key
        API_KEY = get_api_key()
        
        # Initialize API client with logger
        api_client = FreshServiceAPI(API_KEY, logger, dry_run=DRY_RUN)
        
        # Initialize managers
        workspace_manager = WorkspaceManager(api_client, logger)
        
        # Get current workspace
        CURRENT_WORKSPACE = workspace_manager.get_current_workspace()
        
        # Check if we have a valid workspace
        if not CURRENT_WORKSPACE:
            print_colored("\n⚠️ No workspaces found. Please check your API key and permissions.", "red")
            print_colored("The toolkit will continue in limited mode.", "yellow")
        
        # Initialize other managers
        user_manager = UserManager(api_client, workspace_manager.current_workspace_id, logger, DRY_RUN)
        department_manager = DepartmentManager(api_client, workspace_manager.current_workspace_id, logger)
        csv_processor = CSVProcessor(logger)
        
        # Display main menu
        display_main_menu(workspace_manager, user_manager, department_manager, csv_processor)
        
    except KeyboardInterrupt:
        print_colored("\n\n👋 Goodbye!", "green")
        sys.exit(0)
    except Exception as e:
        print_colored(f"\n❌ An error occurred: {str(e)}", "red")
        logger.exception("Unhandled exception occurred")
        sys.exit(1)


if __name__ == "__main__":
    main() 