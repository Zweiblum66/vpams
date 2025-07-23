import { useState, useEffect } from 'react';
import { MAMSClient } from '../services/mamsClient';
import { Asset, SearchParams } from '../types';

export const useAssets = () => {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    // Listen for real-time updates
    const handleAssetUpdate = (event: CustomEvent) => {
      const updatedAsset = event.detail;
      setAssets(prev => prev.map(asset => 
        asset.id === updatedAsset.id ? updatedAsset : asset
      ));
    };

    window.addEventListener('mams:asset:updated', handleAssetUpdate as any);
    
    return () => {
      window.removeEventListener('mams:asset:updated', handleAssetUpdate as any);
    };
  }, []);

  const searchAssets = async (query?: string, params?: SearchParams) => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await MAMSClient.getInstance().searchAssets({
        query,
        ...params,
        limit: params?.limit || 50,
      });
      
      setAssets(result.assets);
      setTotal(result.total);
    } catch (err) {
      setError(err.message || 'Failed to load assets');
      setAssets([]);
    } finally {
      setLoading(false);
    }
  };

  const refreshAssets = () => {
    searchAssets();
  };

  const getAsset = async (assetId: string) => {
    try {
      const asset = await MAMSClient.getInstance().getAsset(assetId);
      return asset;
    } catch (err) {
      throw new Error('Failed to load asset');
    }
  };

  return {
    assets,
    loading,
    error,
    total,
    searchAssets,
    refreshAssets,
    getAsset,
  };
};