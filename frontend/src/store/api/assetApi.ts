import { baseApi } from './baseApi';
import { Asset, CreateAssetRequest, UpdateAssetRequest, PaginatedResponse } from '../../types';

export const assetApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    getAssets: builder.query<PaginatedResponse<Asset>, {
      page?: number;
      limit?: number;
      sortBy?: string;
      sortOrder?: 'asc' | 'desc';
      filters?: Record<string, any>;
      search?: string;
    }>({
      query: (params = {}) => {
        const searchParams = new URLSearchParams();
        
        if (params.page) searchParams.append('page', params.page.toString());
        if (params.limit) searchParams.append('limit', params.limit.toString());
        if (params.sortBy) searchParams.append('sort', params.sortBy);
        if (params.sortOrder) searchParams.append('order', params.sortOrder);
        if (params.search) searchParams.append('search', params.search);
        
        // Handle filters
        if (params.filters) {
          Object.entries(params.filters).forEach(([key, value]) => {
            if (value !== undefined && value !== null && value !== '') {
              searchParams.append(`filter[${key}]`, value.toString());
            }
          });
        }

        return {
          url: `/assets?${searchParams}`,
          method: 'GET',
        };
      },
      providesTags: (result) =>
        result
          ? [
              ...result.data.map(({ id }) => ({ type: 'Asset' as const, id })),
              { type: 'Asset', id: 'LIST' },
            ]
          : [{ type: 'Asset', id: 'LIST' }],
    }),

    getAssetById: builder.query<Asset, string>({
      query: (id) => ({
        url: `/assets/${id}`,
        method: 'GET',
      }),
      providesTags: (result, error, id) => [{ type: 'Asset', id }],
    }),

    createAsset: builder.mutation<Asset, CreateAssetRequest>({
      query: (data) => ({
        url: '/assets',
        method: 'POST',
        body: data,
      }),
      invalidatesTags: [{ type: 'Asset', id: 'LIST' }],
    }),

    updateAsset: builder.mutation<Asset, { id: string; data: UpdateAssetRequest }>({
      query: ({ id, data }) => ({
        url: `/assets/${id}`,
        method: 'PUT',
        body: data,
      }),
      invalidatesTags: (result, error, { id }) => [
        { type: 'Asset', id },
        { type: 'Asset', id: 'LIST' },
      ],
    }),

    deleteAsset: builder.mutation<void, string>({
      query: (id) => ({
        url: `/assets/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: (result, error, id) => [
        { type: 'Asset', id },
        { type: 'Asset', id: 'LIST' },
      ],
    }),

    uploadAsset: builder.mutation<Asset, { file: File; metadata: CreateAssetRequest }>({
      query: ({ file, metadata }) => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('metadata', JSON.stringify(metadata));

        return {
          url: '/assets/upload',
          method: 'POST',
          body: formData,
        };
      },
      invalidatesTags: [{ type: 'Asset', id: 'LIST' }],
    }),

    downloadAsset: builder.query<Blob, string>({
      query: (id) => ({
        url: `/assets/${id}/download`,
        method: 'GET',
        responseHandler: (response) => response.blob(),
      }),
    }),

    getAssetVersions: builder.query<any[], string>({
      query: (id) => ({
        url: `/assets/${id}/versions`,
        method: 'GET',
      }),
      providesTags: (result, error, id) => [{ type: 'Asset', id: `${id}-versions` }],
    }),

    createAssetVersion: builder.mutation<any, { id: string; file: File }>({
      query: ({ id, file }) => {
        const formData = new FormData();
        formData.append('file', file);

        return {
          url: `/assets/${id}/versions`,
          method: 'POST',
          body: formData,
        };
      },
      invalidatesTags: (result, error, { id }) => [
        { type: 'Asset', id },
        { type: 'Asset', id: `${id}-versions` },
      ],
    }),

    generateThumbnail: builder.mutation<{ thumbnail_url: string }, { id: string; timestamp?: number }>({
      query: ({ id, timestamp }) => ({
        url: `/assets/${id}/thumbnail${timestamp ? `?timestamp=${timestamp}` : ''}`,
        method: 'POST',
      }),
      invalidatesTags: (result, error, { id }) => [{ type: 'Asset', id }],
    }),

    getAssetMetadata: builder.query<any, string>({
      query: (id) => ({
        url: `/assets/${id}/metadata`,
        method: 'GET',
      }),
      providesTags: (result, error, id) => [{ type: 'Metadata', id }],
    }),

    updateAssetMetadata: builder.mutation<any, { id: string; metadata: Record<string, any> }>({
      query: ({ id, metadata }) => ({
        url: `/assets/${id}/metadata`,
        method: 'PUT',
        body: metadata,
      }),
      invalidatesTags: (result, error, { id }) => [
        { type: 'Metadata', id },
        { type: 'Asset', id },
      ],
    }),
  }),
});

export const {
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
} = assetApi;