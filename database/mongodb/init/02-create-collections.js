// Create collections for all databases
print('Creating MongoDB collections...');

// Load and execute all schema files
const schemaFiles = [
  '/schemas/02-search-collections.js',
  '/schemas/03-metadata-collections.js',
  '/schemas/04-assets-collections.js',
  '/schemas/05-ai-collections.js',
  '/schemas/06-cache-collections.js'
];

schemaFiles.forEach(file => {
  print(`Executing ${file}...`);
  load(file);
});

print('All MongoDB collections created successfully!');