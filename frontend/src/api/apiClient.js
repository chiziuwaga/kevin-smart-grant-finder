// Re-export all functions from the TypeScript file explicitly
import apiClientTS, {
  getDashboardStats,
  getDistribution,
  getGrants,
  searchGrants,
  getGrantById,
  getSavedGrants,
  saveGrant,
  unsaveGrant,
  runSearch,
  getLastRun,
  getRunHistory,
  getUserSettings,
  updateUserSettings
} from './apiClient.ts';

// Named exports
export {
  getDashboardStats,
  getDistribution,
  getGrants,
  searchGrants,
  getGrantById,
  getSavedGrants,
  saveGrant,
  unsaveGrant,
  runSearch,
  getLastRun,
  getRunHistory,
  getUserSettings,
  updateUserSettings
};

// Default export
export default apiClientTS;