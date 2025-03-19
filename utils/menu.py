#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Menu Module

Provides interactive menu functionality for the FreshService User Management Toolkit.
"""

import sys
from typing import List, Dict, Callable, Any

from .helpers import print_colored, clear_screen


class Menu:
    """
    Simple menu class for displaying options and handling user selection.
    """
    
    def __init__(self, title: str):
        """
        Initialize a menu with a title.
        
        Args:
            title: The menu title to display
        """
        self.title = title
        self.items = []
        
    def add_item(self, text: str, action: callable) -> None:
        """
        Add a menu item.
        
        Args:
            text: Text to display for the menu item
            action: Function to call when the item is selected
        """
        self.items.append((text, action))
        
    def display(self) -> None:
        """
        Display the menu and handle user selection.
        """
        while True:
            print_colored(f"\n{self.title}", "blue", bold=True)
            print_colored("-" * len(self.title), "blue")
            
            for i, (text, _) in enumerate(self.items, 1):
                print_colored(f"{i}. {text}", "cyan")
            
            choice = input("\nEnter your choice (or 'q' to quit): ").strip().lower()
            
            # Check for quit command
            if choice == 'q':
                print_colored("\n👋 Goodbye!", "green")
                sys.exit(0)
                
            # Process numeric input
            try:
                option = int(choice)
                if 1 <= option <= len(self.items):
                    # Execute the menu item's action
                    result = self.items[option-1][1]()
                    # If the action returns True, break out of the menu loop
                    if result is True:
                        return
                else:
                    print_colored("❌ Invalid option. Please try again.", "red")
                    input("Press Enter to continue...")
            except ValueError:
                print_colored("❌ Please enter a valid number or 'q' to quit.", "red")
                input("Press Enter to continue...")


class SelectionMenu(Menu):
    """
    A menu specifically for selecting items from a list.
    Returns the selected item instead of executing a function.
    """
    
    def __init__(self, title: str, items: List[Any], display_func: Callable[[Any], str] = str):
        """
        Initialize a selection menu.
        
        Args:
            title: Menu title to display
            items: List of items to select from
            display_func: Function to convert items to display strings
        """
        super().__init__(title)
        self.selection_items = items
        self.display_func = display_func
        
        # Add items with functions that return the selected item
        for i, item in enumerate(items):
            display_text = self.display_func(item)
            self.add_item(display_text, lambda i=i: self.selection_items[i])
    
    def get_selection(self) -> Any:
        """
        Display the menu and get the selected item.
        
        Returns:
            Selected item or None if cancelled
        """
        return self.display()


class PaginatedMenu(Menu):
    """
    A menu with pagination for displaying large lists of items.
    """
    
    def __init__(self, title: str, items_per_page: int = 10):
        """
        Initialize a paginated menu.
        
        Args:
            title: Menu title to display
            items_per_page: Number of items to display per page
        """
        super().__init__(title)
        self.items_per_page = items_per_page
        self.current_page = 1
        self.total_pages = 1
    
    def display(self) -> None:
        """
        Display the menu with pagination and handle user input.
        """
        # Calculate total pages
        self.total_pages = (len(self.items) + self.items_per_page - 1) // self.items_per_page
        
        while True:
            # Calculate items for current page
            start_idx = (self.current_page - 1) * self.items_per_page
            end_idx = min(start_idx + self.items_per_page, len(self.items))
            current_items = self.items[start_idx:end_idx]
            
            # Display the menu title and pagination info
            print_colored(f"\n{self.title} - Page {self.current_page}/{self.total_pages}", "blue", bold=True)
            print_colored('-' * len(self.title), "blue")
            
            # Display menu items for current page
            for i, (title, _) in enumerate(current_items, start_idx + 1):
                print_colored(f"{i}. {title}", "yellow")
            
            # Display pagination options
            print_colored("\nNavigation:", "cyan")
            if self.current_page > 1:
                print_colored("p - Previous page", "cyan")
            if self.current_page < self.total_pages:
                print_colored("n - Next page", "cyan")
            print_colored("q - Return to previous menu", "cyan")
            
            # Get user selection
            try:
                choice = input("\nEnter your choice: ").strip().lower()
                
                # Check for navigation commands
                if choice == 'q':
                    return
                elif choice == 'p' and self.current_page > 1:
                    self.current_page -= 1
                    continue
                elif choice == 'n' and self.current_page < self.total_pages:
                    self.current_page += 1
                    continue
                
                # Try to convert to index
                try:
                    index = int(choice) - 1
                    
                    # Validate index
                    if 0 <= index < len(self.items):
                        # Call the selected function
                        result = self.items[index][1]()
                        
                        # If the function returns a value, break the loop
                        if result is not None:
                            return result
                    else:
                        print_colored(f"Invalid choice: {choice}. Please enter a number between 1 and {len(self.items)}.", "red")
                        input("\nPress Enter to continue...")
                        
                except ValueError:
                    print_colored(f"Invalid input: {choice}. Please enter a valid option.", "red")
                    input("\nPress Enter to continue...")
                    
            except KeyboardInterrupt:
                print_colored("\n\nOperation cancelled.", "yellow")
                return
            except Exception as e:
                print_colored(f"An error occurred: {str(e)}", "red")
                input("\nPress Enter to continue...") 