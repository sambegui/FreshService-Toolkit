#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FreshService User Management Toolkit - Utilities Package

This package contains utility modules for the FreshService User Management Toolkit.
"""

# Import key components for easier access
from .api_client import FreshServiceAPI
from .workspace_manager import WorkspaceManager
from .user_manager import UserManager
from .department_manager import DepartmentManager
from .csv_processor import CSVProcessor
from .helpers import (
    setup_logging,
    setup_virtual_env,
    print_colored,
    clear_screen,
    format_table,
    yes_no_prompt,
    get_input_with_default,
    is_valid_file_path
)
from .menu import Menu, SelectionMenu, PaginatedMenu

__all__ = [
    'FreshServiceAPI',
    'WorkspaceManager',
    'UserManager',
    'DepartmentManager',
    'CSVProcessor',
    'setup_logging',
    'setup_virtual_env',
    'print_colored',
    'clear_screen',
    'format_table',
    'yes_no_prompt',
    'get_input_with_default',
    'is_valid_file_path',
    'Menu',
    'SelectionMenu',
    'PaginatedMenu',
] 