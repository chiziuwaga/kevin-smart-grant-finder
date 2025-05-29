// Re-export all functions from the TypeScript file
// This allows JavaScript files to import from this file without .ts extension
export * from './apiClient';

// Re-export the default export
import apiClient from './apiClient';
export default apiClient;