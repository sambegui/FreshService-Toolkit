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

The script requires Python 3.6 or higher and uses several dependencies that are automatically managed.

## Troubleshooting

### macOS Installation Issues
If you encounter dependency issues on macOS after running the setup script, you may need to manually install some packages:

```bash
# Activate the virtual environment
source venv/bin/activate

# Manually install dependencies
pip install requests
pip install Levenshtein

# Now try running the toolkit again
./run_toolkit.sh
```

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
- **📈 Reports**: Generate reports on user activity and export data (WIP)
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

## Security

- 🔑 Your API key is never stored on disk and is only kept in memory during the script's execution
- 🛡️ All API communication happens over HTTPS
- 🚫 The script performs input validation before making API calls

## Logging

Logs are stored in the `logs` directory. Check these logs for detailed information about operation results and any errors encountered.

## Quick Tips

- Press 'q' at any menu to quit the application
- Use the filter option in search results to narrow down large result sets
- Check the logs folder for detailed information about operations and errors

## License

[MIT License](LICENSE) 
