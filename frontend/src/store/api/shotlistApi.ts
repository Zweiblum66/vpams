import { baseApi } from './baseApi';
import { ShotlistItem, CreateShotlistItemRequest, Asset } from '../../types';

export interface ShotlistItemUpdate {
  id: string;
  in_point?: number;
  out_point?: number;
  title?: string;
  description?: string;
  notes?: string;
  color?: string;
  order?: number;
}

export interface ShotlistItemReorder {
  id: string;
  new_order: number;
}

export interface ShotlistExportRequest {
  shotlist_id: string;
  format: 'aaf' | 'xml' | 'edl' | 'otio' | 'csv';
  include_metadata?: boolean;
  include_thumbnails?: boolean;
}

export interface ShotlistStats {
  total_items: number;
  total_duration: number;
  avg_duration: number;
  min_duration: number;
  max_duration: number;
  unique_assets: number;
  by_asset_type: Record<string, number>;
  created_at: string;
  updated_at: string;
}

export const shotlistApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    // Get shotlist items
    getShotlistItems: builder.query<ShotlistItem[], string>({
      query: (shotlistId) => `/shotlists/${shotlistId}/items`,
      providesTags: (result, error, shotlistId) => [
        { type: 'ShotlistItem', id: `shotlist-${shotlistId}` },
        ...(result?.map(({ id }) => ({ type: 'ShotlistItem' as const, id })) || []),
      ],
    }),

    // Get single shotlist item
    getShotlistItem: builder.query<ShotlistItem, { shotlistId: string; itemId: string }>({
      query: ({ shotlistId, itemId }) => `/shotlists/${shotlistId}/items/${itemId}`,
      providesTags: (result, error, { itemId }) => [
        { type: 'ShotlistItem', id: itemId },
      ],
    }),

    // Create shotlist item
    createShotlistItem: builder.mutation<ShotlistItem, { shotlistId: string; item: CreateShotlistItemRequest }>({
      query: ({ shotlistId, item }) => ({
        url: `/shotlists/${shotlistId}/items`,
        method: 'POST',
        body: item,
      }),
      invalidatesTags: (result, error, { shotlistId }) => [
        { type: 'ShotlistItem', id: `shotlist-${shotlistId}` },
      ],
    }),

    // Update shotlist item
    updateShotlistItem: builder.mutation<ShotlistItem, { shotlistId: string; item: ShotlistItemUpdate }>({
      query: ({ shotlistId, item }) => ({
        url: `/shotlists/${shotlistId}/items/${item.id}`,
        method: 'PUT',
        body: item,
      }),
      invalidatesTags: (result, error, { shotlistId, item }) => [
        { type: 'ShotlistItem', id: item.id },
        { type: 'ShotlistItem', id: `shotlist-${shotlistId}` },
      ],
    }),

    // Delete shotlist item
    deleteShotlistItem: builder.mutation<void, { shotlistId: string; itemId: string }>({
      query: ({ shotlistId, itemId }) => ({
        url: `/shotlists/${shotlistId}/items/${itemId}`,
        method: 'DELETE',
      }),
      invalidatesTags: (result, error, { shotlistId, itemId }) => [
        { type: 'ShotlistItem', id: itemId },
        { type: 'ShotlistItem', id: `shotlist-${shotlistId}` },
      ],
    }),

    // Reorder shotlist items
    reorderShotlistItems: builder.mutation<ShotlistItem[], { shotlistId: string; items: ShotlistItemReorder[] }>({
      query: ({ shotlistId, items }) => ({
        url: `/shotlists/${shotlistId}/items/reorder`,
        method: 'POST',
        body: { items },
      }),
      invalidatesTags: (result, error, { shotlistId }) => [
        { type: 'ShotlistItem', id: `shotlist-${shotlistId}` },
      ],
    }),

    // Duplicate shotlist item
    duplicateShotlistItem: builder.mutation<ShotlistItem, { shotlistId: string; itemId: string }>({
      query: ({ shotlistId, itemId }) => ({
        url: `/shotlists/${shotlistId}/items/${itemId}/duplicate`,
        method: 'POST',
      }),
      invalidatesTags: (result, error, { shotlistId }) => [
        { type: 'ShotlistItem', id: `shotlist-${shotlistId}` },
      ],
    }),

    // Add multiple assets to shotlist
    addAssetsToShotlist: builder.mutation<ShotlistItem[], { shotlistId: string; assetIds: string[] }>({
      query: ({ shotlistId, assetIds }) => ({
        url: `/shotlists/${shotlistId}/items/bulk-add`,
        method: 'POST',
        body: { asset_ids: assetIds },
      }),
      invalidatesTags: (result, error, { shotlistId }) => [
        { type: 'ShotlistItem', id: `shotlist-${shotlistId}` },
      ],
    }),

    // Get shotlist statistics
    getShotlistStats: builder.query<ShotlistStats, string>({
      query: (shotlistId) => `/shotlists/${shotlistId}/stats`,
      providesTags: (result, error, shotlistId) => [
        { type: 'ShotlistStats', id: shotlistId },
      ],
    }),

    // Export shotlist
    exportShotlist: builder.mutation<Blob, ShotlistExportRequest>({
      query: ({ shotlist_id, format, include_metadata, include_thumbnails }) => ({
        url: `/shotlists/${shotlist_id}/export`,
        method: 'POST',
        body: {
          format,
          include_metadata,
          include_thumbnails,
        },
        responseHandler: (response) => response.blob(),
      }),
    }),

    // Import shotlist
    importShotlist: builder.mutation<{ imported_count: number; errors: string[] }, { shotlistId: string; file: File; format: string }>({
      query: ({ shotlistId, file, format }) => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('format', format);
        
        return {
          url: `/shotlists/${shotlistId}/import`,
          method: 'POST',
          body: formData,
        };
      },
      invalidatesTags: (result, error, { shotlistId }) => [
        { type: 'ShotlistItem', id: `shotlist-${shotlistId}` },
      ],
    }),

    // Search within shotlist
    searchShotlistItems: builder.query<ShotlistItem[], { shotlistId: string; query: string }>({
      query: ({ shotlistId, query }) => ({
        url: `/shotlists/${shotlistId}/items/search`,
        params: { q: query },
      }),
      providesTags: (result, error, { shotlistId }) => [
        { type: 'ShotlistItem', id: `shotlist-${shotlistId}-search` },
      ],
    }),
  }),
});

export const {
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
} = shotlistApi;