/**
 * Browse Screen
 * 
 * Main asset browsing interface with grid/list views,
 * filtering, sorting, and search functionality.
 */

import React, {useState, useEffect, useCallback} from 'react';
import {
  View,
  StyleSheet,
  FlatList,
  RefreshControl,
  Dimensions,
} from 'react-native';
import {
  Appbar,
  Searchbar,
  SegmentedButtons,
  FAB,
  Text,
  Chip,
  Menu,
  IconButton,
} from 'react-native-paper';
import {useNavigation} from '@react-navigation/native';
import {useDispatch, useSelector} from 'react-redux';
import Icon from 'react-native-vector-icons/MaterialIcons';

import {AppState, Asset, AssetType, SearchFilters} from '@/types';
import {fetchAssets, setAssetFilters, clearAssetFilters} from '@/store/slices/assetsSlice';
import {AssetCard} from '@/components/assets/AssetCard';
import {AssetListItem} from '@/components/assets/AssetListItem';
import {FilterBottomSheet} from '@/components/browse/FilterBottomSheet';
import {SortBottomSheet} from '@/components/browse/SortBottomSheet';
import {EmptyState} from '@/components/common/EmptyState';
import {colors, spacing} from '@/constants/theme';

const {width: screenWidth} = Dimensions.get('window');
const GRID_ITEM_SIZE = (screenWidth - (spacing.md * 3)) / 2;

export const BrowseScreen: React.FC = () => {
  const navigation = useNavigation();
  const dispatch = useDispatch();
  
  const {
    items: assetItems,
    isLoading,
    error,
    filters,
    hasNextPage,
    currentPage,
  } = useSelector((state: AppState) => state.assets);

  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [searchQuery, setSearchQuery] = useState('');
  const [showFilterSheet, setShowFilterSheet] = useState(false);
  const [showSortSheet, setShowSortSheet] = useState(false);
  const [showSortMenu, setShowSortMenu] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  // Convert assets object to array
  const assets = Object.values(assetItems);
  const activeFilters = Object.values(filters).flat().length;

  useEffect(() => {
    loadAssets();
  }, [filters]);

  const loadAssets = useCallback(
    async (page = 1, append = false) => {
      try {
        await dispatch(
          fetchAssets({
            page,
            limit: 20,
            search: searchQuery,
            filters,
            append,
          }) as any
        ).unwrap();
      } catch (error) {
        console.error('Failed to load assets:', error);
      }
    },
    [dispatch, searchQuery, filters]
  );

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    await loadAssets(1, false);
    setRefreshing(false);
  }, [loadAssets]);

  const handleLoadMore = useCallback(() => {
    if (hasNextPage && !isLoading) {
      loadAssets(currentPage + 1, true);
    }
  }, [hasNextPage, isLoading, currentPage, loadAssets]);

  const handleSearch = useCallback(
    (query: string) => {
      setSearchQuery(query);
      if (query.trim()) {
        // Debounce search
        const timer = setTimeout(() => {
          loadAssets(1, false);
        }, 500);
        return () => clearTimeout(timer);
      } else {
        loadAssets(1, false);
      }
    },
    [loadAssets]
  );

  const handleAssetPress = useCallback(
    (asset: Asset) => {
      navigation.navigate('AssetDetail' as never, {assetId: asset.id} as never);
    },
    [navigation]
  );

  const handleUploadPress = useCallback(() => {
    navigation.navigate('Upload' as never);
  }, [navigation]);

  const handleFilterApply = useCallback(
    (newFilters: SearchFilters) => {
      dispatch(setAssetFilters(newFilters));
      setShowFilterSheet(false);
    },
    [dispatch]
  );

  const handleClearFilters = useCallback(() => {
    dispatch(clearAssetFilters());
  }, [dispatch]);

  const renderAssetItem = useCallback(
    ({item}: {item: Asset}) => {
      if (viewMode === 'grid') {
        return (
          <AssetCard
            asset={item}
            onPress={() => handleAssetPress(item)}
            size={GRID_ITEM_SIZE}
          />
        );
      } else {
        return (
          <AssetListItem
            asset={item}
            onPress={() => handleAssetPress(item)}
          />
        );
      }
    },
    [viewMode, handleAssetPress]
  );

  const renderHeader = () => (
    <View style={styles.header}>
      {/* Search Bar */}
      <Searchbar
        placeholder="Search assets..."
        value={searchQuery}
        onChangeText={handleSearch}
        style={styles.searchBar}
        icon="search"
        clearIcon="close"
      />

      {/* Filter and Sort Controls */}
      <View style={styles.controls}>
        <View style={styles.leftControls}>
          {/* Active Filters */}
          {activeFilters > 0 && (
            <Chip
              mode="outlined"
              onPress={handleClearFilters}
              onClose={handleClearFilters}
              style={styles.filterChip}>
              {activeFilters} filter{activeFilters > 1 ? 's' : ''}
            </Chip>
          )}
        </View>

        <View style={styles.rightControls}>
          {/* View Mode Toggle */}
          <SegmentedButtons
            value={viewMode}
            onValueChange={setViewMode}
            buttons={[
              {
                value: 'grid',
                icon: 'grid-view',
                style: styles.segmentButton,
              },
              {
                value: 'list',
                icon: 'view-list',
                style: styles.segmentButton,
              },
            ]}
            style={styles.viewToggle}
          />

          {/* Filter Button */}
          <IconButton
            icon="filter-list"
            mode="outlined"
            onPress={() => setShowFilterSheet(true)}
            style={styles.filterButton}
          />

          {/* Sort Menu */}
          <Menu
            visible={showSortMenu}
            onDismiss={() => setShowSortMenu(false)}
            anchor={
              <IconButton
                icon="sort"
                mode="outlined"
                onPress={() => setShowSortMenu(true)}
                style={styles.sortButton}
              />
            }>
            <Menu.Item
              title="Name"
              leadingIcon="sort-alphabetical-ascending"
              onPress={() => {
                dispatch(setAssetFilters({...filters, sort_by: 'name', sort_order: 'asc'}));
                setShowSortMenu(false);
              }}
            />
            <Menu.Item
              title="Date Created"
              leadingIcon="calendar-clock"
              onPress={() => {
                dispatch(setAssetFilters({...filters, sort_by: 'created_at', sort_order: 'desc'}));
                setShowSortMenu(false);
              }}
            />
            <Menu.Item
              title="File Size"
              leadingIcon="file-document-outline"
              onPress={() => {
                dispatch(setAssetFilters({...filters, sort_by: 'file_size', sort_order: 'desc'}));
                setShowSortMenu(false);
              }}
            />
            <Menu.Item
              title="Relevance"
              leadingIcon="star"
              onPress={() => {
                dispatch(setAssetFilters({...filters, sort_by: 'relevance', sort_order: 'desc'}));
                setShowSortMenu(false);
              }}
            />
          </Menu>
        </View>
      </View>
    </View>
  );

  const renderEmptyState = () => {
    if (searchQuery || activeFilters > 0) {
      return (
        <EmptyState
          icon="search-off"
          title="No assets found"
          message="Try adjusting your search terms or filters"
          actionLabel="Clear Filters"
          onAction={activeFilters > 0 ? handleClearFilters : undefined}
        />
      );
    }

    return (
      <EmptyState
        icon="cloud-upload"
        title="No assets yet"
        message="Start by uploading your first media file"
        actionLabel="Upload Asset"
        onAction={handleUploadPress}
      />
    );
  };

  const renderFooter = () => {
    if (!isLoading || assets.length === 0) return null;

    return (
      <View style={styles.loadingFooter}>
        <Text>Loading more assets...</Text>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <Appbar.Header style={styles.appBar}>
        <Appbar.Content title="Browse Assets" />
        <Appbar.Action
          icon="search"
          onPress={() => navigation.navigate('Search' as never)}
        />
      </Appbar.Header>

      <FlatList
        data={assets}
        renderItem={renderAssetItem}
        keyExtractor={(item) => item.id}
        numColumns={viewMode === 'grid' ? 2 : 1}
        key={viewMode} // Force re-render when view mode changes
        contentContainerStyle={[
          styles.listContainer,
          assets.length === 0 && styles.emptyContainer,
        ]}
        columnWrapperStyle={viewMode === 'grid' ? styles.gridRow : undefined}
        ItemSeparatorComponent={
          viewMode === 'list' ? () => <View style={styles.listSeparator} /> : undefined
        }
        ListHeaderComponent={renderHeader}
        ListEmptyComponent={renderEmptyState}
        ListFooterComponent={renderFooter}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            colors={[colors.primary]}
          />
        }
        onEndReached={handleLoadMore}
        onEndReachedThreshold={0.1}
        removeClippedSubviews={true}
        maxToRenderPerBatch={10}
        windowSize={10}
        initialNumToRender={8}
      />

      {/* Floating Action Button */}
      <FAB
        icon="plus"
        label="Upload"
        style={styles.fab}
        onPress={handleUploadPress}
      />

      {/* Filter Bottom Sheet */}
      <FilterBottomSheet
        visible={showFilterSheet}
        filters={filters}
        onApply={handleFilterApply}
        onDismiss={() => setShowFilterSheet(false)}
      />

      {/* Sort Bottom Sheet */}
      <SortBottomSheet
        visible={showSortSheet}
        currentSort={filters.sort_by}
        currentOrder={filters.sort_order}
        onApply={(sortBy, sortOrder) => {
          dispatch(setAssetFilters({...filters, sort_by: sortBy, sort_order: sortOrder}));
          setShowSortSheet(false);
        }}
        onDismiss={() => setShowSortSheet(false)}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  appBar: {
    backgroundColor: colors.primary,
  },
  header: {
    padding: spacing.md,
    backgroundColor: colors.background,
  },
  searchBar: {
    marginBottom: spacing.md,
  },
  controls: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  leftControls: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
  },
  rightControls: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  filterChip: {
    marginRight: spacing.sm,
  },
  viewToggle: {
    marginRight: spacing.sm,
  },
  segmentButton: {
    minWidth: 40,
  },
  filterButton: {
    marginRight: spacing.xs,
  },
  sortButton: {
    marginLeft: spacing.xs,
  },
  listContainer: {
    flexGrow: 1,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
  },
  gridRow: {
    justifyContent: 'space-between',
    paddingHorizontal: spacing.md,
    marginBottom: spacing.md,
  },
  listSeparator: {
    height: spacing.sm,
  },
  loadingFooter: {
    padding: spacing.lg,
    alignItems: 'center',
  },
  fab: {
    position: 'absolute',
    margin: spacing.md,
    right: 0,
    bottom: 0,
  },
});