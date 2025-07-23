import { baseApi } from './baseApi';
import { 
  User, 
  UserCreateRequest, 
  UserUpdateRequest, 
  UserProfile,
  Role,
  RoleCreateRequest,
  RoleUpdateRequest,
  Permission,
  PermissionCreateRequest,
  PermissionUpdateRequest,
  Group,
  GroupCreateRequest,
  GroupUpdateRequest,
  PaginatedResponse
} from '../../types';

export const userApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    // User endpoints
    getUsers: builder.query<PaginatedResponse<User>, {
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
        
        if (params.filters) {
          Object.entries(params.filters).forEach(([key, value]) => {
            if (value !== undefined && value !== null && value !== '') {
              searchParams.append(`filter[${key}]`, value.toString());
            }
          });
        }

        return {
          url: `/users?${searchParams}`,
          method: 'GET',
        };
      },
      providesTags: (result) =>
        result
          ? [
              ...result.data.map(({ user_id }) => ({ type: 'User' as const, id: user_id })),
              { type: 'User', id: 'LIST' },
            ]
          : [{ type: 'User', id: 'LIST' }],
    }),

    getUserById: builder.query<User, string>({
      query: (id) => ({
        url: `/users/${id}`,
        method: 'GET',
      }),
      providesTags: (result, error, id) => [{ type: 'User', id }],
    }),

    createUser: builder.mutation<User, UserCreateRequest>({
      query: (data) => ({
        url: '/users',
        method: 'POST',
        body: data,
      }),
      invalidatesTags: [{ type: 'User', id: 'LIST' }],
    }),

    updateUser: builder.mutation<User, { id: string; data: UserUpdateRequest }>({
      query: ({ id, data }) => ({
        url: `/users/${id}`,
        method: 'PUT',
        body: data,
      }),
      invalidatesTags: (result, error, { id }) => [
        { type: 'User', id },
        { type: 'User', id: 'LIST' },
      ],
    }),

    deleteUser: builder.mutation<void, string>({
      query: (id) => ({
        url: `/users/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: (result, error, id) => [
        { type: 'User', id },
        { type: 'User', id: 'LIST' },
      ],
    }),

    getUserProfile: builder.query<UserProfile, string>({
      query: (id) => ({
        url: `/users/${id}/profile`,
        method: 'GET',
      }),
      providesTags: (result, error, id) => [{ type: 'User', id: `${id}-profile` }],
    }),

    updateUserProfile: builder.mutation<UserProfile, { id: string; data: Partial<UserProfile> }>({
      query: ({ id, data }) => ({
        url: `/users/${id}/profile`,
        method: 'PUT',
        body: data,
      }),
      invalidatesTags: (result, error, { id }) => [
        { type: 'User', id: `${id}-profile` },
        { type: 'User', id },
      ],
    }),

    // Role endpoints
    getRoles: builder.query<PaginatedResponse<Role>, {
      page?: number;
      limit?: number;
      sortBy?: string;
      sortOrder?: 'asc' | 'desc';
    }>({
      query: (params = {}) => {
        const searchParams = new URLSearchParams();
        
        if (params.page) searchParams.append('page', params.page.toString());
        if (params.limit) searchParams.append('limit', params.limit.toString());
        if (params.sortBy) searchParams.append('sort', params.sortBy);
        if (params.sortOrder) searchParams.append('order', params.sortOrder);

        return {
          url: `/roles?${searchParams}`,
          method: 'GET',
        };
      },
      providesTags: (result) =>
        result
          ? [
              ...result.data.map(({ role_id }) => ({ type: 'Role' as const, id: role_id })),
              { type: 'Role', id: 'LIST' },
            ]
          : [{ type: 'Role', id: 'LIST' }],
    }),

    getRoleById: builder.query<Role, string>({
      query: (id) => ({
        url: `/roles/${id}`,
        method: 'GET',
      }),
      providesTags: (result, error, id) => [{ type: 'Role', id }],
    }),

    createRole: builder.mutation<Role, RoleCreateRequest>({
      query: (data) => ({
        url: '/roles',
        method: 'POST',
        body: data,
      }),
      invalidatesTags: [{ type: 'Role', id: 'LIST' }],
    }),

    updateRole: builder.mutation<Role, { id: string; data: RoleUpdateRequest }>({
      query: ({ id, data }) => ({
        url: `/roles/${id}`,
        method: 'PUT',
        body: data,
      }),
      invalidatesTags: (result, error, { id }) => [
        { type: 'Role', id },
        { type: 'Role', id: 'LIST' },
      ],
    }),

    deleteRole: builder.mutation<void, string>({
      query: (id) => ({
        url: `/roles/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: (result, error, id) => [
        { type: 'Role', id },
        { type: 'Role', id: 'LIST' },
      ],
    }),

    // Permission endpoints
    getPermissions: builder.query<PaginatedResponse<Permission>, {
      page?: number;
      limit?: number;
      sortBy?: string;
      sortOrder?: 'asc' | 'desc';
    }>({
      query: (params = {}) => {
        const searchParams = new URLSearchParams();
        
        if (params.page) searchParams.append('page', params.page.toString());
        if (params.limit) searchParams.append('limit', params.limit.toString());
        if (params.sortBy) searchParams.append('sort', params.sortBy);
        if (params.sortOrder) searchParams.append('order', params.sortOrder);

        return {
          url: `/permissions?${searchParams}`,
          method: 'GET',
        };
      },
      providesTags: (result) =>
        result
          ? [
              ...result.data.map(({ permission_id }) => ({ type: 'Permission' as const, id: permission_id })),
              { type: 'Permission', id: 'LIST' },
            ]
          : [{ type: 'Permission', id: 'LIST' }],
    }),

    getPermissionById: builder.query<Permission, string>({
      query: (id) => ({
        url: `/permissions/${id}`,
        method: 'GET',
      }),
      providesTags: (result, error, id) => [{ type: 'Permission', id }],
    }),

    createPermission: builder.mutation<Permission, PermissionCreateRequest>({
      query: (data) => ({
        url: '/permissions',
        method: 'POST',
        body: data,
      }),
      invalidatesTags: [{ type: 'Permission', id: 'LIST' }],
    }),

    updatePermission: builder.mutation<Permission, { id: string; data: PermissionUpdateRequest }>({
      query: ({ id, data }) => ({
        url: `/permissions/${id}`,
        method: 'PUT',
        body: data,
      }),
      invalidatesTags: (result, error, { id }) => [
        { type: 'Permission', id },
        { type: 'Permission', id: 'LIST' },
      ],
    }),

    deletePermission: builder.mutation<void, string>({
      query: (id) => ({
        url: `/permissions/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: (result, error, id) => [
        { type: 'Permission', id },
        { type: 'Permission', id: 'LIST' },
      ],
    }),

    // Group endpoints
    getGroups: builder.query<PaginatedResponse<Group>, {
      page?: number;
      limit?: number;
      sortBy?: string;
      sortOrder?: 'asc' | 'desc';
    }>({
      query: (params = {}) => {
        const searchParams = new URLSearchParams();
        
        if (params.page) searchParams.append('page', params.page.toString());
        if (params.limit) searchParams.append('limit', params.limit.toString());
        if (params.sortBy) searchParams.append('sort', params.sortBy);
        if (params.sortOrder) searchParams.append('order', params.sortOrder);

        return {
          url: `/groups?${searchParams}`,
          method: 'GET',
        };
      },
      providesTags: (result) =>
        result
          ? [
              ...result.data.map(({ group_id }) => ({ type: 'Group' as const, id: group_id })),
              { type: 'Group', id: 'LIST' },
            ]
          : [{ type: 'Group', id: 'LIST' }],
    }),

    getGroupById: builder.query<Group, string>({
      query: (id) => ({
        url: `/groups/${id}`,
        method: 'GET',
      }),
      providesTags: (result, error, id) => [{ type: 'Group', id }],
    }),

    createGroup: builder.mutation<Group, GroupCreateRequest>({
      query: (data) => ({
        url: '/groups',
        method: 'POST',
        body: data,
      }),
      invalidatesTags: [{ type: 'Group', id: 'LIST' }],
    }),

    updateGroup: builder.mutation<Group, { id: string; data: GroupUpdateRequest }>({
      query: ({ id, data }) => ({
        url: `/groups/${id}`,
        method: 'PUT',
        body: data,
      }),
      invalidatesTags: (result, error, { id }) => [
        { type: 'Group', id },
        { type: 'Group', id: 'LIST' },
      ],
    }),

    deleteGroup: builder.mutation<void, string>({
      query: (id) => ({
        url: `/groups/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: (result, error, id) => [
        { type: 'Group', id },
        { type: 'Group', id: 'LIST' },
      ],
    }),
  }),
});

export const {
  // User hooks
  useGetUsersQuery,
  useGetUserByIdQuery,
  useCreateUserMutation,
  useUpdateUserMutation,
  useDeleteUserMutation,
  useGetUserProfileQuery,
  useUpdateUserProfileMutation,
  
  // Role hooks
  useGetRolesQuery,
  useGetRoleByIdQuery,
  useCreateRoleMutation,
  useUpdateRoleMutation,
  useDeleteRoleMutation,
  
  // Permission hooks
  useGetPermissionsQuery,
  useGetPermissionByIdQuery,
  useCreatePermissionMutation,
  useUpdatePermissionMutation,
  useDeletePermissionMutation,
  
  // Group hooks
  useGetGroupsQuery,
  useGetGroupByIdQuery,
  useCreateGroupMutation,
  useUpdateGroupMutation,
  useDeleteGroupMutation,
} = userApi;