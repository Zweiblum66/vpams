import { ROUTES } from './routes';

// Navigation utilities for programmatic navigation
export class Navigation {
  // Asset routes
  static assets() {
    return ROUTES.ASSETS;
  }

  static assetDetail(id: string) {
    return ROUTES.ASSET_DETAIL.replace(':id', id);
  }

  static assetEdit(id: string) {
    return ROUTES.ASSET_EDIT.replace(':id', id);
  }

  static assetUpload() {
    return ROUTES.ASSET_UPLOAD;
  }

  static assetAdvanced() {
    return ROUTES.ASSET_ADVANCED;
  }

  // Project routes
  static projects() {
    return ROUTES.PROJECTS;
  }

  static projectDetail(id: string) {
    return ROUTES.PROJECT_DETAIL.replace(':id', id);
  }

  static projectEdit(id: string) {
    return ROUTES.PROJECT_EDIT.replace(':id', id);
  }

  static projectCreate() {
    return ROUTES.PROJECT_CREATE;
  }

  // Search routes
  static search(query?: string) {
    return query ? `${ROUTES.SEARCH}?q=${encodeURIComponent(query)}` : ROUTES.SEARCH;
  }

  static searchResults(query: string) {
    return `${ROUTES.SEARCH_RESULTS}?q=${encodeURIComponent(query)}`;
  }

  static savedSearches() {
    return ROUTES.SAVED_SEARCHES;
  }

  // User routes
  static users() {
    return ROUTES.USERS;
  }

  static userDetail(id: string) {
    return ROUTES.USER_DETAIL.replace(':id', id);
  }

  static userEdit(id: string) {
    return ROUTES.USER_EDIT.replace(':id', id);
  }

  static userCreate() {
    return ROUTES.USER_CREATE;
  }

  // Role routes
  static roles() {
    return ROUTES.ROLES;
  }

  static roleDetail(id: string) {
    return ROUTES.ROLE_DETAIL.replace(':id', id);
  }

  static roleEdit(id: string) {
    return ROUTES.ROLE_EDIT.replace(':id', id);
  }

  static roleCreate() {
    return ROUTES.ROLE_CREATE;
  }

  // Group routes
  static groups() {
    return ROUTES.GROUPS;
  }

  static groupDetail(id: string) {
    return ROUTES.GROUP_DETAIL.replace(':id', id);
  }

  static groupEdit(id: string) {
    return ROUTES.GROUP_EDIT.replace(':id', id);
  }

  static groupCreate() {
    return ROUTES.GROUP_CREATE;
  }

  // Permission routes
  static permissions() {
    return ROUTES.PERMISSIONS;
  }

  static permissionDetail(id: string) {
    return ROUTES.PERMISSION_DETAIL.replace(':id', id);
  }

  static permissionEdit(id: string) {
    return ROUTES.PERMISSION_EDIT.replace(':id', id);
  }

  static permissionCreate() {
    return ROUTES.PERMISSION_CREATE;
  }

  // Tenant routes
  static tenants() {
    return ROUTES.TENANTS;
  }

  static tenantDetail(tenantId: string, section?: string) {
    const path = ROUTES.TENANT_DETAIL.replace(':tenantId', tenantId);
    return section ? `${path}?section=${section}` : path;
  }

  // System routes
  static dashboard() {
    return ROUTES.DASHBOARD;
  }

  static inheritance() {
    return ROUTES.INHERITANCE;
  }

  static settings() {
    return ROUTES.SETTINGS;
  }

  static profile() {
    return ROUTES.PROFILE;
  }

  // Auth routes
  static login() {
    return ROUTES.LOGIN;
  }

  static register() {
    return ROUTES.REGISTER;
  }

  static forgotPassword() {
    return ROUTES.FORGOT_PASSWORD;
  }

  static resetPassword(token?: string) {
    return token ? `${ROUTES.RESET_PASSWORD}?token=${token}` : ROUTES.RESET_PASSWORD;
  }

  // Error routes
  static notFound() {
    return ROUTES.NOT_FOUND;
  }

  static unauthorized() {
    return ROUTES.UNAUTHORIZED;
  }

  static serverError() {
    return ROUTES.SERVER_ERROR;
  }
}

// Hook for programmatic navigation
export { Navigation as nav };