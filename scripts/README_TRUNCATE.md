# Database Truncation Script

This script provides a safe way to truncate the leads, jobs, and campaigns tables from the database.

## ⚠️ **WARNING**

**This operation is IRREVERSIBLE and will permanently delete ALL data from the specified tables:**
- `leads`
- `jobs` 
- `campaigns`

**Use with extreme caution!**

## Usage

### Running in Docker Container (Recommended)

Since the script needs access to the running database instance, it's designed to be executed inside the Docker container:

```bash
# First, get into the running container
docker-compose exec api bash

# Then run the script
python scripts/truncate_database.py
```

### Running with Non-Interactive Mode

If you need to run the script in a non-interactive environment (like in CI/CD or automated scripts), you can use the `CONFIRM_TRUNCATE` environment variable:

```bash
# In the Docker container
CONFIRM_TRUNCATE=yes python scripts/truncate_database.py
```

### Running Locally (Alternative)

If you prefer to run it locally and have the correct environment variables set:

```bash
# Make sure you have the virtual environment activated and proper env vars
source venv/bin/activate
python scripts/truncate_database.py
```

## What the Script Does

1. **Confirmation**: Prompts for user confirmation before proceeding (unless in non-interactive mode)
2. **Connection**: Connects to the database using the existing app configuration
3. **Truncation**: Executes `TRUNCATE CASCADE` commands in the correct order to handle foreign key constraints:
   - Truncates `leads` table first
   - Truncates `jobs` table second  
   - Truncates `campaigns` table last
4. **Verification**: Counts rows in each table to verify the operation was successful
5. **Logging**: Provides detailed logging throughout the process

## Safety Features

- **User confirmation required** (interactive mode)
- **Environment variable confirmation** (non-interactive mode)
- **Transaction-based**: All operations happen in a single transaction
- **Rollback on error**: If any operation fails, all changes are rolled back
- **Verification step**: Confirms tables are empty after truncation
- **Detailed logging**: Tracks every step of the process

## Foreign Key Handling

The script uses `TRUNCATE CASCADE` which automatically handles foreign key constraints by truncating dependent tables as well. The tables are processed in the correct order:

1. Child tables first (`leads`, `jobs`)
2. Parent tables last (`campaigns`)

## Troubleshooting

### Permission Errors
Make sure the database user has `TRUNCATE` privileges on all tables.

### Connection Errors
Verify that:
- Database is running
- Environment variables are correctly set
- Network connectivity is available

### Foreign Key Constraint Errors
The script uses `CASCADE` which should handle most constraint issues, but if you encounter errors:
- Check for any additional foreign key relationships
- Ensure no other processes are accessing the tables during truncation

## Environment Variables Required

The script uses the same configuration as the main application:
- `POSTGRES_SERVER`
- `POSTGRES_USER` 
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- Or `DATABASE_URL` directly

## Example Output

```
2024-01-15 10:30:00,123 - INFO - Database Truncation Script Started
==================================================
⚠️  WARNING: This will permanently delete ALL data from the following tables:
   - leads
   - jobs
   - campaigns

This operation is IRREVERSIBLE!

Are you sure you want to continue? (yes/no): yes
2024-01-15 10:30:05,456 - INFO - Connecting to database...
2024-01-15 10:30:05,457 - INFO - Database URL: postgresql://user:***@localhost/dbname
2024-01-15 10:30:05,478 - INFO - Starting truncation process...
2024-01-15 10:30:05,479 - INFO - Truncating leads table...
2024-01-15 10:30:05,485 - INFO - Truncating jobs table...
2024-01-15 10:30:05,490 - INFO - Truncating campaigns table...
2024-01-15 10:30:05,495 - INFO - ✅ Successfully truncated all tables!
2024-01-15 10:30:05,496 - INFO - Verifying truncation...
2024-01-15 10:30:05,500 - INFO - Table 'leads': 0 rows remaining
2024-01-15 10:30:05,504 - INFO - ✅ Table 'leads' is empty
2024-01-15 10:30:05,508 - INFO - Table 'jobs': 0 rows remaining
2024-01-15 10:30:05,512 - INFO - ✅ Table 'jobs' is empty
2024-01-15 10:30:05,516 - INFO - Table 'campaigns': 0 rows remaining
2024-01-15 10:30:05,520 - INFO - ✅ Table 'campaigns' is empty
==================================================
2024-01-15 10:30:05,521 - INFO - Database truncation completed successfully! 