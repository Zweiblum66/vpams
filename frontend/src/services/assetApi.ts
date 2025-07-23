import { apiClient } from './apiClient';
import { logger } from '../utils/logger';
import {
  Asset,
  AssetFilter,
  AssetSort,
  AssetListResponse,
  AssetUploadRequest,
  AssetUpdateRequest,
  AssetBulkAction,
} from '../types/asset';

export class AssetApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public code?: string
  ) {
    super(message);
    this.name = 'AssetApiError';
  }
}

class AssetApi {
  private readonly baseUrl = '/api/v1/assets';

  async getAssets(
    filter?: AssetFilter,
    sort?: AssetSort,
    page = 1,
    pageSize = 20
  ): Promise<AssetListResponse> {
    try {
      logger.info('AssetApi.getAssets called', {
        filter,
        sort,
        page,
        pageSize,
        actionType: 'asset_api_get_assets',
      });

      const params = new URLSearchParams();
      params.append('page', page.toString());
      params.append('limit', pageSize.toString());

      if (sort) {
        params.append('sort', `${sort.order === 'desc' ? '-' : ''}${sort.field}`);
      }

      if (filter) {
        if (filter.search) params.append('search', filter.search);
        if (filter.types?.length) params.append('types', filter.types.join(','));
        if (filter.status?.length) params.append('status', filter.status.join(','));
        if (filter.tags?.length) params.append('tags', filter.tags.join(','));
        if (filter.projectId) params.append('project_id', filter.projectId);
        if (filter.folderId) params.append('folder_id', filter.folderId);
        if (filter.dateFrom) params.append('created_from', filter.dateFrom);
        if (filter.dateTo) params.append('created_to', filter.dateTo);
        if (filter.sizeMin) params.append('size_min', filter.sizeMin.toString());
        if (filter.sizeMax) params.append('size_max', filter.sizeMax.toString());
        if (filter.createdBy) params.append('created_by', filter.createdBy);
      }

      const response = await apiClient.get<AssetListResponse>(
        `${this.baseUrl}?${params.toString()}`
      );

      logger.info('AssetApi.getAssets successful', {
        total: response.data.total,
        page: response.data.page,
        actionType: 'asset_api_get_assets_success',
      });

      return response.data;
    } catch (error: any) {
      const message = error.response?.data?.message || 'Failed to fetch assets';
      const statusCode = error.response?.status;
      const code = error.response?.data?.code;

      logger.error('AssetApi.getAssets failed', {
        statusCode,
        code,
        message,
        actionType: 'asset_api_get_assets_error',
      }, error);

      throw new AssetApiError(message, statusCode, code);
    }
  }

  async getAsset(id: string): Promise<Asset> {
    try {
      logger.info('AssetApi.getAsset called', {
        assetId: id,
        actionType: 'asset_api_get_asset',
      });

      const response = await apiClient.get<Asset>(`${this.baseUrl}/${id}`);

      logger.info('AssetApi.getAsset successful', {
        assetId: id,
        assetName: response.data.name,
        actionType: 'asset_api_get_asset_success',
      });

      return response.data;
    } catch (error: any) {
      const message = error.response?.data?.message || 'Failed to fetch asset';
      const statusCode = error.response?.status;
      const code = error.response?.data?.code;

      logger.error('AssetApi.getAsset failed', {
        assetId: id,
        statusCode,
        code,
        message,
        actionType: 'asset_api_get_asset_error',
      }, error);

      throw new AssetApiError(message, statusCode, code);
    }
  }

  async uploadAsset(request: AssetUploadRequest): Promise<Asset> {
    try {
      logger.info('AssetApi.uploadAsset called', {
        fileName: request.file.name,
        fileSize: request.file.size,
        fileType: request.file.type,
        actionType: 'asset_api_upload_asset',
      });

      const formData = new FormData();
      formData.append('file', request.file);
      if (request.name) formData.append('name', request.name);
      if (request.tags?.length) formData.append('tags', JSON.stringify(request.tags));
      if (request.projectId) formData.append('project_id', request.projectId);
      if (request.folderId) formData.append('folder_id', request.folderId);
      if (request.metadata) formData.append('metadata', JSON.stringify(request.metadata));

      const response = await apiClient.post<Asset>(`${this.baseUrl}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      logger.info('AssetApi.uploadAsset successful', {
        assetId: response.data.id,
        assetName: response.data.name,
        actionType: 'asset_api_upload_asset_success',
      });

      return response.data;
    } catch (error: any) {
      const message = error.response?.data?.message || 'Failed to upload asset';
      const statusCode = error.response?.status;
      const code = error.response?.data?.code;

      logger.error('AssetApi.uploadAsset failed', {
        fileName: request.file.name,
        statusCode,
        code,
        message,
        actionType: 'asset_api_upload_asset_error',
      }, error);

      throw new AssetApiError(message, statusCode, code);
    }
  }

  async updateAsset(id: string, request: AssetUpdateRequest): Promise<Asset> {
    try {
      logger.info('AssetApi.updateAsset called', {
        assetId: id,
        updates: Object.keys(request),
        actionType: 'asset_api_update_asset',
      });

      const response = await apiClient.patch<Asset>(`${this.baseUrl}/${id}`, request);

      logger.info('AssetApi.updateAsset successful', {
        assetId: id,
        assetName: response.data.name,
        actionType: 'asset_api_update_asset_success',
      });

      return response.data;
    } catch (error: any) {
      const message = error.response?.data?.message || 'Failed to update asset';
      const statusCode = error.response?.status;
      const code = error.response?.data?.code;

      logger.error('AssetApi.updateAsset failed', {
        assetId: id,
        statusCode,
        code,
        message,
        actionType: 'asset_api_update_asset_error',
      }, error);

      throw new AssetApiError(message, statusCode, code);
    }
  }

  async deleteAsset(id: string): Promise<void> {
    try {
      logger.info('AssetApi.deleteAsset called', {
        assetId: id,
        actionType: 'asset_api_delete_asset',
      });

      await apiClient.delete(`${this.baseUrl}/${id}`);

      logger.info('AssetApi.deleteAsset successful', {
        assetId: id,
        actionType: 'asset_api_delete_asset_success',
      });
    } catch (error: any) {
      const message = error.response?.data?.message || 'Failed to delete asset';
      const statusCode = error.response?.status;
      const code = error.response?.data?.code;

      logger.error('AssetApi.deleteAsset failed', {
        assetId: id,
        statusCode,
        code,
        message,
        actionType: 'asset_api_delete_asset_error',
      }, error);

      throw new AssetApiError(message, statusCode, code);
    }
  }

  async bulkAction(action: AssetBulkAction): Promise<void> {
    try {
      logger.info('AssetApi.bulkAction called', {
        action: action.action,
        assetCount: action.assetIds.length,
        actionType: 'asset_api_bulk_action',
      });

      await apiClient.post(`${this.baseUrl}/bulk/${action.action}`, {
        asset_ids: action.assetIds,
        ...action.data,
      });

      logger.info('AssetApi.bulkAction successful', {
        action: action.action,
        assetCount: action.assetIds.length,
        actionType: 'asset_api_bulk_action_success',
      });
    } catch (error: any) {
      const message = error.response?.data?.message || `Failed to ${action.action} assets`;
      const statusCode = error.response?.status;
      const code = error.response?.data?.code;

      logger.error('AssetApi.bulkAction failed', {
        action: action.action,
        assetCount: action.assetIds.length,
        statusCode,
        code,
        message,
        actionType: 'asset_api_bulk_action_error',
      }, error);

      throw new AssetApiError(message, statusCode, code);
    }
  }

  async downloadAsset(id: string): Promise<Blob> {
    try {
      logger.info('AssetApi.downloadAsset called', {
        assetId: id,
        actionType: 'asset_api_download_asset',
      });

      const response = await apiClient.get(`${this.baseUrl}/${id}/download`, {
        responseType: 'blob',
      });

      logger.info('AssetApi.downloadAsset successful', {
        assetId: id,
        size: response.data.size,
        actionType: 'asset_api_download_asset_success',
      });

      return response.data;
    } catch (error: any) {
      const message = error.response?.data?.message || 'Failed to download asset';
      const statusCode = error.response?.status;
      const code = error.response?.data?.code;

      logger.error('AssetApi.downloadAsset failed', {
        assetId: id,
        statusCode,
        code,
        message,
        actionType: 'asset_api_download_asset_error',
      }, error);

      throw new AssetApiError(message, statusCode, code);
    }
  }

  async getThumbnail(id: string, size: 'small' | 'medium' | 'large' = 'medium'): Promise<string> {
    return `${this.baseUrl}/${id}/thumbnail?size=${size}`;
  }

  async getPreview(id: string): Promise<string> {
    return `${this.baseUrl}/${id}/preview`;
  }
}

export const assetApi = new AssetApi();