// MongoDB Database Initialization Script
// This script sets up the MongoDB databases and collections for MAMS

// Switch to admin database to create users
use('admin');

// Create application user
db.createUser({
  user: 'mams_app',
  pwd: 'mams_dev_password',
  roles: [
    { role: 'readWrite', db: 'mams_search' },
    { role: 'readWrite', db: 'mams_metadata' },
    { role: 'readWrite', db: 'mams_assets' },
    { role: 'readWrite', db: 'mams_ai' },
    { role: 'readWrite', db: 'mams_cache' }
  ]
});

// Create read-only user for analytics
db.createUser({
  user: 'mams_readonly',
  pwd: 'mams_readonly_password',
  roles: [
    { role: 'read', db: 'mams_search' },
    { role: 'read', db: 'mams_metadata' },
    { role: 'read', db: 'mams_assets' },
    { role: 'read', db: 'mams_ai' },
    { role: 'read', db: 'mams_cache' }
  ]
});

// Create backup user
db.createUser({
  user: 'mams_backup',
  pwd: 'mams_backup_password',
  roles: [
    { role: 'backup', db: 'admin' },
    { role: 'read', db: 'mams_search' },
    { role: 'read', db: 'mams_metadata' },
    { role: 'read', db: 'mams_assets' },
    { role: 'read', db: 'mams_ai' },
    { role: 'read', db: 'mams_cache' }
  ]
});

print('MongoDB users created successfully!');