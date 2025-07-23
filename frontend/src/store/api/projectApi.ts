import { baseApi } from './baseApi';
import { Project, ProjectContainer, CreateProjectRequest, UpdateProjectRequest, PaginatedResponse } from '../../types';

export const projectApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    getProjects: builder.query<PaginatedResponse<Project>, {
      page?: number;
      limit?: number;
      sortBy?: string;
      sortOrder?: 'asc' | 'desc';
      filters?: Record<string, any>;
    }>({
      query: (params = {}) => {
        const searchParams = new URLSearchParams();
        
        if (params.page) searchParams.append('page', params.page.toString());
        if (params.limit) searchParams.append('limit', params.limit.toString());
        if (params.sortBy) searchParams.append('sort', params.sortBy);
        if (params.sortOrder) searchParams.append('order', params.sortOrder);
        
        // Handle filters
        if (params.filters) {
          Object.entries(params.filters).forEach(([key, value]) => {
            if (value !== undefined && value !== null && value !== '') {
              searchParams.append(`filter[${key}]`, value.toString());
            }
          });
        }

        return {
          url: `/projects?${searchParams}`,
          method: 'GET',
        };
      },
      providesTags: (result) =>
        result
          ? [
              ...result.data.map(({ id }) => ({ type: 'Project' as const, id })),
              { type: 'Project', id: 'LIST' },
            ]
          : [{ type: 'Project', id: 'LIST' }],
    }),

    getProjectById: builder.query<Project, string>({
      query: (id) => ({
        url: `/projects/${id}`,
        method: 'GET',
      }),
      providesTags: (result, error, id) => [{ type: 'Project', id }],
    }),

    createProject: builder.mutation<Project, CreateProjectRequest>({
      query: (data) => ({
        url: '/projects',
        method: 'POST',
        body: data,
      }),
      invalidatesTags: [{ type: 'Project', id: 'LIST' }],
    }),

    updateProject: builder.mutation<Project, { id: string; data: UpdateProjectRequest }>({
      query: ({ id, data }) => ({
        url: `/projects/${id}`,
        method: 'PUT',
        body: data,
      }),
      invalidatesTags: (result, error, { id }) => [
        { type: 'Project', id },
        { type: 'Project', id: 'LIST' },
      ],
    }),

    deleteProject: builder.mutation<void, string>({
      query: (id) => ({
        url: `/projects/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: (result, error, id) => [
        { type: 'Project', id },
        { type: 'Project', id: 'LIST' },
      ],
    }),

    getProjectContainers: builder.query<ProjectContainer[], string>({
      query: (projectId) => ({
        url: `/projects/${projectId}/containers`,
        method: 'GET',
      }),
      providesTags: (result, error, projectId) => [
        { type: 'Container', id: `project-${projectId}` },
      ],
    }),

    createContainer: builder.mutation<ProjectContainer, {
      projectId: string;
      name: string;
      type: 'folder' | 'bin' | 'shotlist' | 'sequence';
      parentId?: string;
    }>({
      query: ({ projectId, name, type, parentId }) => ({
        url: `/projects/${projectId}/containers`,
        method: 'POST',
        body: {
          name,
          type,
          parent_id: parentId,
        },
      }),
      invalidatesTags: (result, error, { projectId }) => [
        { type: 'Container', id: `project-${projectId}` },
        { type: 'Project', id: projectId },
      ],
    }),

    updateContainer: builder.mutation<ProjectContainer, {
      id: string;
      name?: string;
      parentId?: string;
    }>({
      query: ({ id, name, parentId }) => ({
        url: `/containers/${id}`,
        method: 'PUT',
        body: {
          name,
          parent_id: parentId,
        },
      }),
      invalidatesTags: (result, error, { id }) => [
        { type: 'Container', id },
        { type: 'Container', id: 'LIST' },
      ],
    }),

    deleteContainer: builder.mutation<void, string>({
      query: (id) => ({
        url: `/containers/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: (result, error, id) => [
        { type: 'Container', id },
        { type: 'Container', id: 'LIST' },
      ],
    }),

    moveContainer: builder.mutation<ProjectContainer, {
      id: string;
      parentId?: string;
    }>({
      query: ({ id, parentId }) => ({
        url: `/containers/${id}/move`,
        method: 'POST',
        body: {
          parent_id: parentId,
        },
      }),
      invalidatesTags: (result, error, { id }) => [
        { type: 'Container', id },
        { type: 'Container', id: 'LIST' },
      ],
    }),

    getProjectStats: builder.query<any, string>({
      query: (id) => ({
        url: `/projects/${id}/stats`,
        method: 'GET',
      }),
      providesTags: (result, error, id) => [{ type: 'Project', id: `${id}-stats` }],
    }),

    exportProject: builder.mutation<Blob, { id: string; format: 'aaf' | 'xml' | 'edl' | 'otio' }>({
      query: ({ id, format }) => ({
        url: `/projects/${id}/export`,
        method: 'POST',
        body: { format },
        responseHandler: (response) => response.blob(),
      }),
    }),

    archiveProject: builder.mutation<Project, string>({
      query: (id) => ({
        url: `/projects/${id}/archive`,
        method: 'POST',
      }),
      invalidatesTags: (result, error, id) => [
        { type: 'Project', id },
        { type: 'Project', id: 'LIST' },
      ],
    }),

    restoreProject: builder.mutation<Project, string>({
      query: (id) => ({
        url: `/projects/${id}/restore`,
        method: 'POST',
      }),
      invalidatesTags: (result, error, id) => [
        { type: 'Project', id },
        { type: 'Project', id: 'LIST' },
      ],
    }),
  }),
});

export const {
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
} = projectApi;