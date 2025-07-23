/**
 * Assets API Service
 * 
 * API client for asset-related operations including
 * CRUD operations, search, and metadata management.
 */

import {Asset, SearchFilters, PaginationParams} from '@/types';
import {apiClient} from './apiClient';

interface AssetsResponse {
  data: Asset[];
  meta: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
  links: {
    self: string;
    next?: string;
    prev?: string;
  };
}

interface AssetResponse {
  data: Asset;
}

interface SearchParams extends PaginationParams {
  query?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  type?: string;
  project_id?: string;
  tags?: string[];
  date_from?: string;
  date_to?: string;
  size_min?: number;
  size_max?: number;
  duration_min?: number;
  duration_max?: number;
}

class AssetsApi {
  /**
   * Get paginated list of assets
   */
  async getAssets(params: SearchParams = {}): Promise<AssetsResponse> {
    const response = await apiClient.get('/api/v1/assets', {
      params: {
        page: params.page || 1,
        limit: params.limit || 20,
        sort_by: params.sort_by || 'created_at',
        sort_order: params.sort_order || 'desc',
        ...params,
      },
    });

    return response.data;
  }

  /**
   * Get detailed information about a specific asset
   */
  async getAssetDetails(assetId: string): Promise<AssetResponse> {
    const response = await apiClient.get(`/api/v1/assets/${assetId}`);
    return response.data;
  }

  /**
   * Search assets with full-text search
   */
  async searchAssets(params: SearchParams): Promise<AssetsResponse> {
    const response = await apiClient.get('/api/v1/assets/search', {
      params,
    });

    return response.data;
  }

  /**
   * Get assets by project
   */
  async getProjectAssets(
    projectId: string,
    params: SearchParams = {}
  ): Promise<AssetsResponse> {
    const response = await apiClient.get(`/api/v1/projects/${projectId}/assets`, {
      params: {
        page: params.page || 1,
        limit: params.limit || 20,
        sort_by: params.sort_by || 'created_at',
        sort_order: params.sort_order || 'desc',
        ...params,
      },
    });

    return response.data;
  }

  /**
   * Get user's favorite assets
   */
  async getFavoriteAssets(params: SearchParams = {}): Promise<AssetsResponse> {
    const response = await apiClient.get('/api/v1/assets/favorites', {
      params: {
        page: params.page || 1,
        limit: params.limit || 20,
        sort_by: params.sort_by || 'updated_at',
        sort_order: params.sort_order || 'desc',
        ...params,
      },
    });

    return response.data;
  }

  /**
   * Get recently viewed assets
   */
  async getRecentAssets(params: SearchParams = {}): Promise<AssetsResponse> {
    const response = await apiClient.get('/api/v1/assets/recent', {
      params: {
        page: params.page || 1,
        limit: params.limit || 20,
        ...params,
      },
    });

    return response.data;
  }

  /**
   * Toggle favorite status of an asset
   */
  async toggleFavorite(assetId: string, isFavorite: boolean): Promise<AssetResponse> {
    const response = await apiClient.post(`/api/v1/assets/${assetId}/favorite`, {
      is_favorite: isFavorite,
    });

    return response.data;
  }

  /**
   * Update asset metadata
   */
  async updateAsset(
    assetId: string,
    updates: Partial<Asset>
  ): Promise<AssetResponse> {
    const response = await apiClient.patch(`/api/v1/assets/${assetId}`, updates);
    return response.data;
  }

  /**
   * Delete an asset
   */
  async deleteAsset(assetId: string): Promise<void> {
    await apiClient.delete(`/api/v1/assets/${assetId}`);
  }

  /**
   * Get asset download URL
   */
  async getDownloadUrl(
    assetId: string,
    quality: 'original' | 'high' | 'medium' | 'low' = 'original'
  ): Promise<{download_url: string; expires_at: string}> {
    const response = await apiClient.post(`/api/v1/assets/${assetId}/download`, {
      quality,
    });

    return response.data;
  }

  /**
   * Get asset preview/proxy URL
   */
  async getPreviewUrl(
    assetId: string,
    quality: 'high' | 'medium' | 'low' = 'medium'
  ): Promise<{preview_url: string; expires_at: string}> {
    const response = await apiClient.get(`/api/v1/assets/${assetId}/preview`, {
      params: {quality},
    });

    return response.data;
  }

  /**
   * Get asset thumbnail URL
   */
  async getThumbnailUrl(
    assetId: string,
    size: 'small' | 'medium' | 'large' = 'medium'
  ): Promise<{thumbnail_url: string; expires_at: string}> {
    const response = await apiClient.get(`/api/v1/assets/${assetId}/thumbnail`, {
      params: {size},
    });

    return response.data;
  }

  /**
   * Get asset metadata
   */
  async getAssetMetadata(assetId: string): Promise<{data: Record<string, any>}> {
    const response = await apiClient.get(`/api/v1/assets/${assetId}/metadata`);
    return response.data;
  }

  /**
   * Update asset metadata
   */
  async updateAssetMetadata(
    assetId: string,
    metadata: Record<string, any>
  ): Promise<{data: Record<string, any>}> {
    const response = await apiClient.patch(
      `/api/v1/assets/${assetId}/metadata`,
      metadata
    );

    return response.data;
  }

  /**
   * Get asset tags
   */
  async getAssetTags(assetId: string): Promise<{data: Array<{id: string; name: string}>}> {
    const response = await apiClient.get(`/api/v1/assets/${assetId}/tags`);
    return response.data;
  }

  /**
   * Add tags to asset
   */
  async addAssetTags(
    assetId: string,
    tags: string[]
  ): Promise<{data: Array<{id: string; name: string}>}> {
    const response = await apiClient.post(`/api/v1/assets/${assetId}/tags`, {
      tags,
    });

    return response.data;
  }

  /**
   * Remove tags from asset
   */
  async removeAssetTags(assetId: string, tagIds: string[]): Promise<void> {
    await apiClient.delete(`/api/v1/assets/${assetId}/tags`, {
      data: {tag_ids: tagIds},
    });
  }

  /**
   * Get asset versions/revisions
   */
  async getAssetVersions(assetId: string): Promise<{data: Asset[]}> {
    const response = await apiClient.get(`/api/v1/assets/${assetId}/versions`);
    return response.data;
  }

  /**
   * Create new asset version
   */
  async createAssetVersion(
    assetId: string,
    file: File
  ): Promise<AssetResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('version_note', 'Updated from mobile app');

    const response = await apiClient.post(
      `/api/v1/assets/${assetId}/versions`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data;
  }

  /**
   * Get asset statistics
   */
  async getAssetStats(): Promise<{
    total_assets: number;
    total_size: number;
    by_type: Record<string, number>;
    by_project: Record<string, number>;
  }> {
    const response = await apiClient.get('/api/v1/assets/stats');
    return response.data;
  }

  /**
   * Get suggested tags based on asset content
   */
  async getSuggestedTags(assetId: string): Promise<{data: string[]}> {
    const response = await apiClient.get(`/api/v1/assets/${assetId}/suggestions/tags`);
    return response.data;
  }

  /**
   * Get similar assets
   */
  async getSimilarAssets(
    assetId: string,
    limit = 10
  ): Promise<{data: Asset[]}> {
    const response = await apiClient.get(`/api/v1/assets/${assetId}/similar`, {
      params: {limit},
    });

    return response.data;
  }

  /**
   * Bulk operations
   */
  async bulkUpdateAssets(
    assetIds: string[],
    updates: Partial<Asset>
  ): Promise<{success: string[]; failed: string[]}> {
    const response = await apiClient.patch('/api/v1/assets/bulk', {
      asset_ids: assetIds,
      updates,
    });

    return response.data;
  }

  async bulkDeleteAssets(assetIds: string[]): Promise<{success: string[]; failed: string[]}> {
    const response = await apiClient.delete('/api/v1/assets/bulk', {
      data: {asset_ids: assetIds},
    });

    return response.data;
  }

  /**
   * Advanced search with filters
   */
  async advancedSearch(filters: SearchFilters): Promise<AssetsResponse> {
    const response = await apiClient.post('/api/v1/assets/search/advanced', filters);
    return response.data;
  }

  /**
   * Export search results
   */
  async exportSearchResults(
    filters: SearchFilters,
    format: 'csv' | 'json' | 'xml' = 'csv'
  ): Promise<{download_url: string; expires_at: string}> {
    const response = await apiClient.post('/api/v1/assets/export', {
      filters,
      format,
    });

    return response.data;
  }
}

export const assetsApi = new AssetsApi();