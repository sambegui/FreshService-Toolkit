# FreshService User Management Toolkit

A comprehensive toolkit for FreshService administrators to efficiently manage user details. This toolkit provides a command-line interface for performing various user management tasks across multiple FreshService workspaces.

## Features

- 🔍 Find and edit user details with email or name-based search
  - Search by email address
  - Search by first name, last name, or both
  - View detailed user information with resolved department names and reporting managers
  - See whether users are Agents or Requesters
- ✏️ Edit user details with a simple interface
  - Update first name and last name
  - Change department assignment
  - Modify reporting manager relationships
  - Edit multiple fields at once
  - Activate or deactivate users
- 📊 Bulk operations via CSV files
- 👥 Group management for user permissions
- 🔄 Support for multiple FreshService workspaces
- 📋 Advanced reporting capabilities
  - User activity tracking for both Agents and Requesters
  - Inactive accounts reporting based on login history
- 🔑 Secure API key management with validation

## Installation

### Windows
1. Clone this repository:
   ```
   git clone https://github.com/sambegui/FreshService-Toolkit.git
   cd FreshService-Toolkit
   ```
2. Run one of the setup scripts:
   - Command Prompt: `setup_windows.bat`
   - PowerShell: `.\setup_windows.ps1`
3. After setup, run the toolkit:
   - Command Prompt: `run_toolkit.bat`
   - PowerShell: `.\run_toolkit.ps1`

### macOS
1. Clone this repository:
   ```
   git clone https://github.com/sambegui/FreshService-Toolkit.git
   cd FreshService-Toolkit
   ```
2. Make the setup script executable and run it:
   ```
   chmod +x setup_mac.sh
   ./setup_mac.sh
   ```
3. After setup, run the toolkit:
   ```
   ./run_toolkit.sh
   ```

The script requires Python 3.6 or higher and uses several dependencies that are automatically managed. The setup scripts will install all required dependencies in a virtual environment.

## Troubleshooting

### macOS Installation Issues
If you encounter dependency issues on macOS after running the setup script, the most common issues involve the Levenshtein package:

```bash
# Activate the virtual environment
source venv/bin/activate

# Install the macOS-compatible version
pip install python-Levenshtein-wheels

# If that fails, try the standard version
pip install python-Levenshtein

# If that also fails, try the basic Levenshtein package
pip install Levenshtein

# Other common dependencies that might need manual installation
pip install requests
pip install colorama
pip install tabulate
pip install keyring

# Now try running the toolkit again
./run_toolkit.sh
```

If you see import errors for any module, you can install it directly:
```bash
pip install [module_name]
```

### Dependencies

If you encounter errors related to missing modules, you can install all required dependencies using:

```bash
pip install -r requirements.txt
```

Key dependencies include:
- requests: For API communication
- colorama: For colored console output
- tabulate: For formatted table output
- keyring: For secure API key storage

## Requirements

- Python 3.6 or higher
- FreshService API key with appropriate permissions

## Usage

Run the main script:

```
python freshservice_toolkit.py
```

## Main Menu Options

- **🔍 Find and Edit User**: Search and modify user details
  - Search by email
  - Search by name
  - Advanced search
  - View recent users
- **📊 Bulk Operations**: Perform actions on multiple users via CSV
- **👥 Group Management**: Manage user group memberships
- **🔐 Access Control**: Handle password resets and account unlocking
- **📈 Reports**: Generate reports on user activity and export data
  - User Activity Report: Track ticket interactions for agents and requesters
  - Inactive Accounts Report: Identify users who haven't logged in recently
- **🔄 Switch Workspace**: Change to a different FreshService workspace
- **❓ Help**: Display help information
- **🚪 Exit**: Exit the toolkit (use 'q' at any time to quit)

## User Management Features

### Search Options
- Email search - Find users by their exact email address
- Name search - Find users by first name, last name, or both
- Advanced search - Find users using multiple criteria

### User Details
The toolkit displays comprehensive information about users, including:
- Basic information (name, email, job title)
- Department information with resolved department names
- Reporting manager with resolved name
- Agent/Requester status
- Account status (active/inactive)

### Edit Options
Edit user information with a simple interface:
- Update first and last names
- Change department assignment
- Update reporting manager
- Edit multiple fields at once
- Activate or deactivate user accounts

## CSV File Formats

The toolkit supports various CSV formats for bulk operations:

### User Update Template

```
Email,First_Name,Last_Name,Department,Manager_Email,Job_Title
john.doe@example.com,John,Doe,Engineering,jane.smith@example.com,Software Engineer
```

### Department Update Template

```
Email,Department
john.doe@example.com,New Department
```

### Group Membership Template

```
Email,Group_Name,Action
john.doe@example.com,Support Team,add
```

### User Deactivation Template

```
Email,Reason
john.doe@example.com,Left the company
```

## Reports

### User Activity Report
Generates detailed reports on user activity, tracking:
- Requester ticket interactions
- Agent ticket activities
- Last login timestamps
- Communication patterns

### Inactive Accounts Report
Identifies users who haven't logged in for a specified period:
- Configurable inactivity threshold (days)
- Covers both agents and requesters
- Exports results to CSV for review

## Security

- 🔑 API key validation ensures your credentials are valid before proceeding
- 🔒 Your API key is securely stored using the system's credential manager (Windows Credential Locker, macOS Keychain, or Linux Secret Service)
- 🛡️ All API communication happens over HTTPS
- 🚫 The script performs input validation before making API calls

## Logging

- Logs are stored in the `logs` directory with detailed information
- Console output is limited to errors only for a cleaner experience
- Comprehensive debug information is automatically saved to log files

## Quick Tips

- Press 'q' at any menu to quit the application
- Use the filter option in search results to narrow down large result sets
- Check the logs folder for detailed information about operations and errors
- Your API key is securely stored between sessions - no need to enter it each time

## License

[MIT License](LICENSE) 