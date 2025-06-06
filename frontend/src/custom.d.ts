// Allow importing .ts files in JavaScript
declare module '*.ts' {
  const content: any;
  export default content;
}

// Allow importing specific exports from apiClient
declare module '../api/apiClient' {
  export function getDashboardStats(): any;
  export function getDistribution(): any;
  export function getGrants(params?: any): any;
  export function searchGrants(filters: any): any;
  export function getGrantById(id: string): any;
  export function getSavedGrants(): any;
  export function saveGrant(id: string): any;
  export function unsaveGrant(id: string): any;
  export function getUserSettings(): any;
  export function updateUserSettings(settings: any): any;
  export function runSearch(): any;
  export function getLastRun(): any;
  export function getRunHistory(): any;
  export const API: any;
  export default any;
}
