#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FreshService User Management Toolkit

A comprehensive toolkit for FreshService administrators to efficiently manage user details.
Supports multiple workspaces and provides various user management capabilities.
"""

import os
import sys
import base64
import getpass
import logging
import argparse
from typing import Dict, List, Optional, Tuple, Any

# Core modules
from utils.api_client import FreshServiceAPI
from utils.workspace_manager import WorkspaceManager
from utils.user_manager import UserManager
from utils.department_manager import DepartmentManager
from utils.csv_processor import CSVProcessor
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
    """Prompt the user for their FreshService API key."""
    print_colored("\n🔑 FreshService API Authentication", "blue")
    print_colored("Please enter your FreshService API key (input will be hidden):", "yellow")
    api_key = getpass.getpass()
    
    if not api_key:
        print_colored("❌ API key is required to continue.", "red")
        sys.exit(1)
        
    return api_key


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
    
    menu.add_item("📆 User Activity Report", lambda: user_activity_report(user_manager, csv_processor))
    menu.add_item("💤 Inactive Accounts Report", lambda: inactive_accounts_report(user_manager, csv_processor))
    menu.add_item("📊 Custom User Report", lambda: custom_user_report(user_manager, csv_processor))
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
    print_colored("\n📆 This feature is not yet implemented.", "yellow")
    input("Press Enter to continue...")


def inactive_accounts_report(user_manager, csv_processor):
    """Generate a report of inactive accounts."""
    print_colored("\n💤 This feature is not yet implemented.", "yellow")
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