# Google Cloud SQL Connection Guide

## Prerequisites
1. A Google Cloud Platform (GCP) account
2. A Cloud SQL PostgreSQL instance
3. Proper IAM permissions

## Step 1: Create a Service Account
1. Go to the [GCP Console](https://console.cloud.google.com/)
2. Navigate to "IAM & Admin" > "Service Accounts"
3. Click "Create Service Account"
4. Enter a name and description for your service account
5. Click "Create and Continue"
6. Assign the following roles:
   - Cloud SQL Client
   - Cloud SQL Editor (if you need write access)
7. Click "Done"

## Step 2: Generate Service Account Key
1. Find your newly created service account in the list
2. Click the three dots menu (⋮) and select "Manage keys"
3. Click "Add Key" > "Create new key"
4. Select JSON format
5. Click "Create"
6. Save the downloaded JSON file as `credentials.json` in your `Backend` directory

## Step 3: Configure Cloud SQL Instance
1. Go to the Cloud SQL instances page
2. Select your instance
3. Go to "Connections" > "Networking"
4. Add your application's IP address to the authorized networks
   - For local development, you might need to add your home IP address
   - For production, use private IP if possible

## Step 4: Update Environment Variables
Update your `.env` file with the correct values:

```
DB_INSTANCE=your-project-id:region:instance-name
DB_USER=postgres
DB_PASS=your-actual-password
DB_NAME=postgres
```

Make sure your `DB_INSTANCE` follows the format: `project-id:region:instance-name`

## Step 5: Restart Your Application
```bash
docker-compose down
docker-compose up -d
```

## Troubleshooting

### Password Authentication Failed
- Double-check your password in the `.env` file
- Verify the user exists in your Cloud SQL instance

### Connection Timeout
- Check network connectivity
- Ensure your IP is authorized in Cloud SQL

### Permission Denied
- Verify your service account has the necessary roles
- Check that your `credentials.json` file is properly mounted in Docker 