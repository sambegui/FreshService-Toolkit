#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Helper Functions Module

Provides various utility functions for the FreshService User Management Toolkit.
"""

import os
import sys
import logging
import subprocess
import platform
import shutil
from typing import Optional

# Try to import colorama, but don't fail if it's not available
try:
    import colorama
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False

# Check for tabulate
try:
    import tabulate as tabulate_module
    TABULATE_AVAILABLE = True
except ImportError:
    TABULATE_AVAILABLE = False


def setup_logging(log_level: int = logging.INFO) -> logging.Logger:
    """
    Setup and configure logging.
    
    Args:
        log_level: Logging level to use
        
    Returns:
        Configured logger instance
    """
    # First, configure the root logger to ERROR to prevent any INFO messages in console
    logging.basicConfig(level=logging.ERROR)
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure logging
    logger = logging.getLogger('freshservice_toolkit')
    logger.setLevel(log_level)
    
    # Clear existing handlers
    if logger.handlers:
        logger.handlers.clear()
    
    # Create file handler - detailed logging to file
    log_file = os.path.join(log_dir, 'freshservice_toolkit.log')
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    
    # Create console handler - ONLY errors to console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)  # Only errors to console
    
    # Create formatter
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')  # Simplified format for console
    
    file_handler.setFormatter(file_formatter)
    console_handler.setFormatter(console_formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Prevent propagation to parent loggers (important to avoid duplicate logs)
    logger.propagate = False
    
    # Disable all non-error logs for related modules
    for module in ["requests", "urllib3", "freshservice_toolkit", 
                  "utils.api_client", "utils.user_manager", "utils.department_manager",
                  "utils.workspace_manager", "utils.csv_processor", "utils.reports"]:
        logging.getLogger(module).setLevel(logging.ERROR)
    
    # Only have detailed logs in the file, not console
    logger.info("Logging initialized")
    return logger


def setup_virtual_env() -> bool:
    """
    Create a virtual environment and install dependencies if needed.
    
    Returns:
        True if successful, False otherwise
    """
    # Get script directory
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    venv_dir = os.path.join(script_dir, 'venv')
    requirements_file = os.path.join(script_dir, 'requirements.txt')
    
    # Check if virtual environment already exists
    if os.path.exists(venv_dir):
        print_colored("Virtual environment already exists.", "green")
        return True
    
    try:
        # Create virtual environment
        print_colored("Creating virtual environment...", "blue")
        subprocess.check_call([sys.executable, '-m', 'venv', venv_dir])
        
        # Get pip path in the virtual environment
        if platform.system() == 'Windows':
            pip_path = os.path.join(venv_dir, 'Scripts', 'pip')
        else:
            pip_path = os.path.join(venv_dir, 'bin', 'pip')
        
        # Upgrade pip
        print_colored("Upgrading pip...", "blue")
        subprocess.check_call([pip_path, 'install', '--upgrade', 'pip'])
        
        # Install requirements
        if os.path.exists(requirements_file):
            print_colored("Installing dependencies...", "blue")
            subprocess.check_call([pip_path, 'install', '-r', requirements_file])
            print_colored("Virtual environment setup complete.", "green")
            return True
        else:
            print_colored("Requirements file not found. Creating one with default dependencies...", "yellow")
            with open(requirements_file, 'w') as f:
                f.write("requests==2.28.1\n")
                f.write("fuzzywuzzy==0.18.0\n")
                f.write("python-Levenshtein==0.12.2\n")
                f.write("colorama==0.4.6\n")
            
            print_colored("Installing default dependencies...", "blue")
            subprocess.check_call([pip_path, 'install', '-r', requirements_file])
            print_colored("Virtual environment setup complete with default dependencies.", "green")
            return True
            
    except subprocess.CalledProcessError as e:
        print_colored(f"Error setting up virtual environment: {str(e)}", "red")
        return False
    except Exception as e:
        print_colored(f"Unexpected error setting up virtual environment: {str(e)}", "red")
        return False


def print_colored(text: str, color: str, bold: bool = False) -> None:
    """
    Print text in color.
    
    Args:
        text: Text to print
        color: Color to use ('red', 'green', 'yellow', 'blue', 'cyan', 'magenta')
        bold: Whether to print in bold
    """
    if not COLORAMA_AVAILABLE:
        # Fallback if colorama is not installed
        print(text)
        return
        
    try:
        colorama.init()
        
        colors = {
            'red': colorama.Fore.RED,
            'green': colorama.Fore.GREEN,
            'yellow': colorama.Fore.YELLOW,
            'blue': colorama.Fore.BLUE,
            'cyan': colorama.Fore.CYAN,
            'magenta': colorama.Fore.MAGENTA,
            'white': colorama.Fore.WHITE
        }
        
        color_code = colors.get(color.lower(), colorama.Fore.WHITE)
        bold_code = colorama.Style.BRIGHT if bold else ""
        reset = colorama.Style.RESET_ALL
        
        print(f"{bold_code}{color_code}{text}{reset}")
        
    except Exception:
        # Fallback for any other errors
        print(text)


def clear_screen() -> None:
    """Clear the terminal screen."""
    os.system('cls' if platform.system() == 'Windows' else 'clear')


def format_table(data: list, headers: list, padding: int = 2) -> str:
    """
    Format a list of dictionaries as a text table.
    
    Args:
        data: List of dictionaries to format
        headers: List of headers (must match keys in data dictionaries)
        padding: Padding between columns
        
    Returns:
        Formatted table string
    """
    if not data or not headers:
        return ""
    
    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in data:
        for i, header in enumerate(headers):
            if header in row:
                col_widths[i] = max(col_widths[i], len(str(row[header])))
    
    # Add padding
    col_widths = [w + padding for w in col_widths]
    
    # Create header row
    result = ""
    for i, header in enumerate(headers):
        result += header.ljust(col_widths[i])
    result += "\n"
    
    # Add separator
    result += "-" * sum(col_widths) + "\n"
    
    # Add data rows
    for row in data:
        line = ""
        for i, header in enumerate(headers):
            if header in row:
                line += str(row[header]).ljust(col_widths[i])
            else:
                line += "".ljust(col_widths[i])
        result += line + "\n"
    
    return result


def yes_no_prompt(question: str, default: Optional[bool] = None) -> bool:
    """
    Prompt the user for a yes/no answer.
    
    Args:
        question: Question to ask
        default: Default value if the user presses Enter (None means no default)
        
    Returns:
        True for yes, False for no
    """
    valid = {"yes": True, "y": True, "no": False, "n": False}
    
    if default is None:
        prompt = " [y/n] "
    elif default:
        prompt = " [Y/n] "
    else:
        prompt = " [y/N] "
    
    while True:
        print_colored(question + prompt, "cyan")
        choice = input().lower()
        
        if choice == "" and default is not None:
            return default
        elif choice in valid:
            return valid[choice]
        else:
            print_colored("Please respond with 'yes'/'y' or 'no'/'n'", "yellow")


def get_input_with_default(prompt: str, default: Optional[str] = None) -> str:
    """
    Get user input with an optional default value.
    
    Args:
        prompt: Prompt to display
        default: Default value if the user presses Enter
        
    Returns:
        User input or default value
    """
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    
    print_colored(prompt, "cyan", end="")
    response = input().strip()
    
    if not response and default:
        return default
    return response


def is_valid_file_path(path: str) -> bool:
    """
    Check if a file path is valid.
    
    Args:
        path: File path to check
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Check if directory part exists
        dir_name = os.path.dirname(path)
        if dir_name and not os.path.isdir(dir_name):
            return False
        
        # Try to create a test file
        if not os.path.isdir(path):
            with open(path, 'a'):
                pass
            
            # Delete the file if it was created
            if os.path.exists(path) and not os.path.getsize(path):
                os.remove(path)
                
        return True
    except (OSError, IOError):
        return False


def use_tabulate(table_data, headers, tablefmt="grid"):
    """
    Use tabulate module if available, otherwise fall back to built-in formatter.
    
    Args:
        table_data: List of data rows to format
        headers: List of column headers
        tablefmt: Format for tabulate (ignored if tabulate not available)
        
    Returns:
        Formatted table string
    """
    if TABULATE_AVAILABLE:
        return tabulate_module.tabulate(table_data, headers=headers, tablefmt=tablefmt)
    else:
        # Convert data to list of dicts if not already
        if table_data and isinstance(table_data[0], list):
            dict_data = []
            for row in table_data:
                row_dict = {}
                for i, header in enumerate(headers):
                    row_dict[header] = row[i] if i < len(row) else ""
                dict_data.append(row_dict)
            return format_table(dict_data, headers)
        else:
            return format_table(table_data, headers) 