// Export the base API
export { baseApi } from './baseApi';

// Export all API slices
export * from './assetApi';
export * from './authApi';
export * from './projectApi';
export * from './searchApi';
export * from './shotlistApi';
export * from './tenantApi';
export * from './userApi';
export * from './workflowApi';

// Export RTK Query hooks for easy access
export {
  // Asset API hooks
  useGetAssetsQuery,
  useGetAssetByIdQuery,
  useCreateAssetMutation,
  useUpdateAssetMutation,
  useDeleteAssetMutation,
  useUploadAssetMutation,
  useDownloadAssetQuery,
  useGetAssetVersionsQuery,
  useCreateAssetVersionMutation,
  useGenerateThumbnailMutation,
  useGetAssetMetadataQuery,
  useUpdateAssetMetadataMutation,
} from './assetApi';

export {
  // Auth API hooks
  useLoginMutation,
  useLogoutMutation,
  useGetCurrentUserQuery,
  useRefreshTokenMutation,
  useRegisterMutation,
  useRequestPasswordResetMutation,
  useResetPasswordMutation,
  useChangePasswordMutation,
  useVerifyEmailMutation,
  useResendVerificationEmailMutation,
  useEnableMFAMutation,
  useConfirmMFAMutation,
  useDisableMFAMutation,
  useVerifyMFAMutation,
  useGenerateBackupCodesMutation,
  useGetExternalAuthProvidersQuery,
  useInitiateExternalAuthMutation,
  useCompleteExternalAuthMutation,
  useLinkExternalAccountMutation,
  useUnlinkExternalAccountMutation,
} from './authApi';

export {
  // Project API hooks
  useGetProjectsQuery,
  useGetProjectByIdQuery,
  useCreateProjectMutation,
  useUpdateProjectMutation,
  useDeleteProjectMutation,
  useGetProjectContainersQuery,
  useCreateContainerMutation,
  useUpdateContainerMutation,
  useDeleteContainerMutation,
  useMoveContainerMutation,
  useGetProjectStatsQuery,
  useExportProjectMutation,
  useArchiveProjectMutation,
  useRestoreProjectMutation,
} from './projectApi';

export {
  // Search API hooks
  usePerformSearchMutation,
  usePerformAdvancedSearchMutation,
  usePerformFilteredSearchMutation,
  usePerformSemanticSearchMutation,
  usePerformVisualSearchMutation,
  useGetSearchSuggestionsQuery,
  useGetSearchHistoryQuery,
  useClearSearchHistoryMutation,
  useGetSavedSearchesQuery,
  useCreateSavedSearchMutation,
  useUpdateSavedSearchMutation,
  useDeleteSavedSearchMutation,
  useExecuteSavedSearchMutation,
  useGetSearchAnalyticsQuery,
  useGetPopularSearchesQuery,
  useGetFacetsQuery,
} from './searchApi';

export {
  // Shotlist API hooks
  useGetShotlistItemsQuery,
  useGetShotlistItemQuery,
  useCreateShotlistItemMutation,
  useUpdateShotlistItemMutation,
  useDeleteShotlistItemMutation,
  useReorderShotlistItemsMutation,
  useDuplicateShotlistItemMutation,
  useAddAssetsToShotlistMutation,
  useGetShotlistStatsQuery,
  useExportShotlistMutation,
  useImportShotlistMutation,
  useSearchShotlistItemsQuery,
} from './shotlistApi';

export {
  // User API hooks
  useGetUsersQuery,
  useGetUserByIdQuery,
  useCreateUserMutation,
  useUpdateUserMutation,
  useDeleteUserMutation,
  useGetUserProfileQuery,
  useUpdateUserProfileMutation,
  useGetRolesQuery,
  useGetRoleByIdQuery,
  useCreateRoleMutation,
  useUpdateRoleMutation,
  useDeleteRoleMutation,
  useGetPermissionsQuery,
  useGetPermissionByIdQuery,
  useCreatePermissionMutation,
  useUpdatePermissionMutation,
  useDeletePermissionMutation,
  useGetGroupsQuery,
  useGetGroupByIdQuery,
  useCreateGroupMutation,
  useUpdateGroupMutation,
  useDeleteGroupMutation,
} from './userApi';

export {
  // Workflow API hooks
  useGetAvailableNodesQuery,
  useGetNodeDetailsQuery,
  useCreateDesignerWorkflowMutation,
  useGetDesignerWorkflowQuery,
  useUpdateDesignerStateMutation,
  useAddNodeMutation,
  useUpdateNodeMutation,
  useDeleteNodeMutation,
  useCreateConnectionMutation,
  useDeleteConnectionMutation,
  useValidateWorkflowMutation,
  useValidateWorkflowRealtimeMutation,
  useExportWorkflowMutation,
  useImportWorkflowMutation,
  useGetDesignerTemplatesQuery,
  useCreateDesignerTemplateMutation,
  usePreviewWorkflowMutation,
  useTestWorkflowMutation,
  useCreateTestCaseMutation,
  useGetTestCasesQuery,
  useUpdateTestCaseMutation,
  useDeleteTestCaseMutation,
  useRunTestCaseMutation,
  useRunAllTestCasesMutation,
  useGetTestResultsQuery,
  useGetTestResultQuery,
  useGetTestDataTemplatesQuery,
  useCreateTestDataTemplateMutation,
  useGetTestCoverageQuery,
  useConvertToExecutableMutation,
  useGetDesignerSettingsQuery,
  useUpdateDesignerSettingsMutation,
} from './workflowApi';