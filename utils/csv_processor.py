#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CSV Processor Module

Handles CSV file processing for bulk user operations.
"""

import csv
import logging
import os
from typing import Dict, List, Optional, Any, Tuple


class CSVProcessor:
    """
    Processes CSV files for bulk operations.
    Handles validation, parsing, and error reporting.
    """
    
    def __init__(self, logger: logging.Logger):
        """
        Initialize the CSV processor.
        
        Args:
            logger: Logger instance
        """
        self.logger = logger
    
    def read_csv_file(self, file_path: str) -> List[Dict[str, str]]:
        """
        Read and parse a CSV file.
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            List of dictionaries representing rows in the CSV
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file is not a valid CSV
        """
        if not os.path.exists(file_path):
            error_msg = f"CSV file not found: {file_path}"
            self.logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        try:
            self.logger.info(f"Reading CSV file: {file_path}")
            
            with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                # Validate header row
                if reader.fieldnames is None:
                    error_msg = f"CSV file has no header row: {file_path}"
                    self.logger.error(error_msg)
                    raise ValueError(error_msg)
                
                # Read all rows
                rows = list(reader)
                
                if not rows:
                    self.logger.warning(f"CSV file is empty: {file_path}")
                else:
                    self.logger.info(f"Successfully read {len(rows)} rows from CSV")
                
                return rows
                
        except csv.Error as e:
            error_msg = f"Error parsing CSV file {file_path}: {str(e)}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
    
    def validate_user_csv(self, rows: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        """
        Validate CSV data for user operations.
        
        Args:
            rows: List of dictionaries representing CSV rows
            
        Returns:
            Tuple of (valid_rows, invalid_rows)
        """
        valid_rows = []
        invalid_rows = []
        
        for i, row in enumerate(rows, start=2):  # Start from 2 to account for header row
            row_num = i  # For error reporting
            validation_errors = []
            
            # Check if row has email or first name + last name
            has_email = 'Email' in row and row['Email'].strip()
            has_names = ('First_Name' in row and row['First_Name'].strip() and
                        'Last_Name' in row and row['Last_Name'].strip())
            
            if not (has_email or has_names):
                validation_errors.append("Row must have either Email or both First_Name and Last_Name")
            
            # Validate email format if provided
            if has_email and not self._is_valid_email(row['Email'].strip()):
                validation_errors.append(f"Invalid email format: {row['Email']}")
            
            # Additional validation for other fields can be added here
            
            # Add row to appropriate list based on validation
            if validation_errors:
                error_row = row.copy()
                error_row['_errors'] = validation_errors
                error_row['_row_num'] = row_num
                invalid_rows.append(error_row)
                self.logger.warning(f"Invalid CSV row {row_num}: {', '.join(validation_errors)}")
            else:
                valid_rows.append(row)
        
        self.logger.info(f"CSV validation: {len(valid_rows)} valid rows, {len(invalid_rows)} invalid rows")
        return valid_rows, invalid_rows
    
    def generate_error_report(self, invalid_rows: List[Dict[str, str]], output_path: str) -> bool:
        """
        Generate a CSV report of validation errors.
        
        Args:
            invalid_rows: List of dictionaries with validation errors
            output_path: Path to save the error report
            
        Returns:
            True if successful, False otherwise
        """
        if not invalid_rows:
            self.logger.info("No errors to report")
            return True
        
        try:
            self.logger.info(f"Generating error report: {output_path}")
            
            # Get all field names from the rows
            fieldnames = set()
            for row in invalid_rows:
                fieldnames.update(key for key in row.keys() if not key.startswith('_'))
            
            # Add error column and row number column
            fieldnames = sorted(list(fieldnames))
            fieldnames = ['Row'] + fieldnames + ['Errors']
            
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for row in invalid_rows:
                    output_row = {
                        'Row': row.get('_row_num', 'Unknown'),
                        'Errors': '; '.join(row.get('_errors', []))
                    }
                    
                    # Copy other fields
                    for key in fieldnames:
                        if key not in ['Row', 'Errors'] and key in row:
                            output_row[key] = row[key]
                    
                    writer.writerow(output_row)
            
            self.logger.info(f"Error report generated with {len(invalid_rows)} rows")
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating CSV error report: {str(e)}")
            return False
    
    def write_csv_report(self, data: List[Dict[str, Any]], output_path: str, fieldnames: Optional[List[str]] = None) -> bool:
        """
        Write data to a CSV file.
        
        Args:
            data: List of dictionaries to write
            output_path: Path to save the CSV file
            fieldnames: Optional list of field names to include
            
        Returns:
            True if successful, False otherwise
        """
        if not data:
            self.logger.warning("No data to write to CSV")
            return False
        
        try:
            self.logger.info(f"Writing CSV report: {output_path}")
            
            # Determine field names if not provided
            if fieldnames is None:
                fieldnames = set()
                for row in data:
                    fieldnames.update(row.keys())
                fieldnames = sorted(list(fieldnames))
            
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            
            self.logger.info(f"CSV report generated with {len(data)} rows")
            return True
            
        except Exception as e:
            self.logger.error(f"Error writing CSV report: {str(e)}")
            return False
    
    def create_template_csv(self, template_type: str, output_path: str) -> bool:
        """
        Create a CSV template file.
        
        Args:
            template_type: Type of template to create ('user', 'department', 'group')
            output_path: Path to save the template
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Creating {template_type} CSV template: {output_path}")
            
            # Define fields for different template types
            templates = {
                'user': ['Email', 'First_Name', 'Last_Name', 'Department', 'Manager_Email', 'Job_Title'],
                'department': ['Email', 'Department'],
                'group': ['Email', 'Group_Name', 'Action'],  # Action: add or remove
                'deactivate': ['Email', 'Reason']
            }
            
            if template_type not in templates:
                self.logger.error(f"Unknown template type: {template_type}")
                return False
            
            fieldnames = templates[template_type]
            
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                # Add sample row for guidance
                sample_row = {}
                if template_type == 'user':
                    sample_row = {
                        'Email': 'john.doe@example.com',
                        'First_Name': 'John',
                        'Last_Name': 'Doe',
                        'Department': 'Engineering',
                        'Manager_Email': 'jane.smith@example.com',
                        'Job_Title': 'Software Engineer'
                    }
                elif template_type == 'department':
                    sample_row = {
                        'Email': 'john.doe@example.com',
                        'Department': 'New Department'
                    }
                elif template_type == 'group':
                    sample_row = {
                        'Email': 'john.doe@example.com',
                        'Group_Name': 'Support Team',
                        'Action': 'add'  # or 'remove'
                    }
                elif template_type == 'deactivate':
                    sample_row = {
                        'Email': 'john.doe@example.com',
                        'Reason': 'Left the company'
                    }
                
                writer.writerow(sample_row)
            
            self.logger.info(f"CSV template created: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating CSV template: {str(e)}")
            return False
    
    def _is_valid_email(self, email: str) -> bool:
        """
        Simple email validation.
        
        Args:
            email: Email to validate
            
        Returns:
            True if valid, False otherwise
        """
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email)) 