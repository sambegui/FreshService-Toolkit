FreshService User Management Toolkit
Create a Python script that serves as a toolkit for FreshService administrators to efficiently manage user details. The script should focus on user editing capabilities while supporting multiple workspaces.

## Core Requirements:
- 🔑 The script should prompt for the FreshService API key each time it runs
- 🖥️ Designed for MacOS environment 
- 🛠️ Automatically create a virtual environment (venv) and install all necessary dependencies
- 📋 Provide a central menu interface with options for different user management tasks
- 🔄 Include functionality to update user details and deactivate users
- 🔁 Loop through users systematically when performing bulk operations
- 📊 Process CSV files containing user emails for batch operations
- 🧪 Implement a "dry run" mode to simulate actions without making actual API changes
- ⚠️ Implement proper rate limiting to respect API constraints
- 💾 Include error handling and logging

## Key Functionality Requirements:

### 1. Workspace Management:
- On startup, discover and list all available FreshService workspaces
- Present workspace selection as a menu option
- Allow switching between workspaces during script execution
- Remember recently used workspaces for quick access

### 2. User Lookup & Editing:
- Provide multiple lookup methods:
  - Lookup by email address (e.g., john.doe@example.com)
  - Lookup by first and last name (e.g., "John Doe")
  - When multiple matches are found for name-based search, present a selection menu
- Present current user details before editing
- Enable editing of specific user attributes:
  - First name
  - Last name
  - Department (selected from a dynamically populated menu)
  - Reporting manager (with search/lookup functionality)
- Validate changes before submission
- Show before/after comparison of changed fields

### 3. Name-Based User Search:
- Accept first name, last name, or both as search parameters
- Implement fuzzy matching to handle slight variations in spelling
- When multiple users match the criteria, display a numbered list of results with:
  - Full name
  - Email address
  - Department
  - Job title (if available)
- Allow selection from multiple results via number selection
- Support additional filtering if too many results are returned
- Remember recent searches for quick access

### 4. Department Management:
- Fetch and cache all available departments from the current workspace
- Present departments as a selectable menu when editing user details
- Support department search/filtering for large department lists
- Show department hierarchy if available

### 5. Bulk User Operations:
- Update department details for users from a CSV file
- Deactivate users in bulk from a CSV file
- Allow filtering inactive users and performing operations on them
- Support batch operations with pause/resume capability

### 6. Group & Team Management:
- Add/remove users from groups
- View group memberships for a specific user
- Batch update group memberships via CSV

### 7. Access & Authentication Control:
- Force password resets for selected users
- Unlock accounts that have been locked
- Update user roles and permissions

### 8. Reporting & Analytics:
- Generate user activity reports (last login, ticket count)
- Export customized user reports to CSV/Excel
- Identify inactive accounts based on custom thresholds

## Technical Implementation Details:
1. Use Python's `requests` library for API interactions
2. Authentication should use Base64 encoded API key in format: `{api_key}:X`
3. API endpoints to include:
   - `GET /api/v2/workspaces` - To fetch all workspaces
   - `GET /api/v2/users` - To fetch users with email or name filtering
   - `GET /api/v2/departments` - To fetch all departments
   - `PUT /api/v2/users/{user_id}` - To update user details
   - `DELETE /api/v2/users/{user_id}` - To deactivate users
   - Additional endpoints for groups, roles, and reporting
4. Use `pandas` or `csv` module to process CSV files with user data
5. Implement fuzzy matching for name-based searches using `fuzzywuzzy` or similar library

## User Lookup Workflows:

### Email-Based Lookup:
1. User enters email address to look up (e.g., john.doe@example.com)
2. Script performs direct API query with email filter
3. If user found, display details and proceed to editing options
4. If no match, offer to search by name instead

### Name-Based Lookup:
1. User enters first name, last name, or both
2. Script queries API with name filters and fuzzy matching
3. If single match found, display user details and proceed to editing
4. If multiple matches found:
   - Display numbered list of matching users with email and department
   - Allow selection by number
   - Support additional filtering if list is too long
5. If no matches found, offer feedback and alternative search options

## User Editing Workflow:
1. After successful user lookup (by email or name):
2. Script fetches and displays current user details
3. Script presents options for fields to edit:
   - First Name
   - Last Name
   - Department (shows menu of available departments)
   - Reporting Manager (allows search by name/email)
4. For department selection:
   - Fetch all departments from current workspace
   - Present as numbered menu with search/filter option
   - Allow selection by number or name
5. For reporting manager:
   - Allow search by name or email
   - Present matching results as a menu
   - Select by number or confirm manually entered email
6. Display summary of changes before submission
7. Submit changes (or simulate in dry run mode)
8. Present confirmation with before/after details

## Dry Run Mode:
1. Include a global flag/toggle for dry run mode that can be set at startup
2. When in dry run mode:
   - Display "🔍 DRY RUN" indicator in all console outputs
   - Log all API calls that would be made without actually executing them
   - Show preview of data that would be sent in each request
   - Report expected outcomes based on current data
3. Allow switching between dry run and live mode from the main menu
4. Generate a detailed simulation report after dry run operations

## CSV Processing Capabilities:
1. Support CSV templates for user editing:
   - Email (required if no name provided)
   - First Name (required if no email provided)
   - Last Name (required if no email provided)
   - Department (optional)
   - Reporting Manager Email (optional)
2. Allow partial updates (only specified fields in CSV are updated)
3. Validate CSV data before processing:
   - Email format validation
   - Department existence check
   - Manager email format and existence validation
4. Generate error reports for invalid entries
5. Process valid entries and report results

## User Experience:
- Clean, color-coded terminal UI with emoji indicators
- Interactive selection menus for workspaces, departments, and managers
- Progress bars for bulk operations
- Confirmation prompts before irreversible actions
- Detailed error messages with suggested fixes
- Command history and quick repeat functionality
- Tabbed interface for displaying multiple search results

## Sample Menu Structure:
1. Main Menu:
   - 🔍 Find and Edit User
   - 📊 Bulk Operations
   - 👥 Group Management
   - 🔐 Access Control
   - 📈 Reports
   - 🔄 Switch Workspace
   - ⚙️ Settings (Toggle Dry Run)
   - ❓ Help
   - 🚪 Exit

2. Find and Edit User:
   - 📧 Search by Email
   - 👤 Search by Name
   - 🔍 Advanced Search
   - 📜 Recent Users

3. User Search Results:
   - Display matched users in tabular format
   - Allow sorting by column
   - Enable selection for editing

4. Edit User:
   - Change First Name
   - Change Last Name
   - Change Department
   - Change Reporting Manager
   - Update Multiple Fields

## Sample Workflow - Name-Based User Search:
1. From main menu, select "Find and Edit User"
2. Select "Search by Name"
3. Enter name information:
   - First Name: John
   - Last Name: [Optional, left blank]
4. View search results:
   Search Results for "John" (5 matches):
   
John Doe (john.doe@example.com)
      Department: Engineering | Title: Developer
   
John Smith (john.smith@example.com)
      Department: Marketing | Title: Marketing Specialist
   
Johnny Walker (johnny.walker@example.com)
      Department: Sales | Title: Account Executive
   
John Williams (john.williams@example.com)
      Department: Finance | Title: Financial Analyst
   
Jonathan Davis (jonathan.davis@example.com)
      Department: IT | Title: System Administrator
   
   Select user by number or refine search: _
5. Enter selection (e.g., "1" for John Doe)
6. Proceed to user editing workflow with selected user

Please provide the complete Python script with detailed comments explaining each major component. Include sample CSV formats that would work with the script.