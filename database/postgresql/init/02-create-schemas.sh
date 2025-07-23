#!/bin/bash
set -e

# Execute all schema files in order
for schema_file in /schemas/*.sql; do
    echo "Executing $schema_file..."
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$schema_file"
done

echo "All schemas created successfully!"