import React, { useCallback, useEffect, useRef } from 'react';
import {
  VariableSizeList as List,
  ListChildComponentProps,
  VariableSizeListProps,
} from 'react-window';
import InfiniteLoader from 'react-window-infinite-loader';
import AutoSizer from 'react-virtualized-auto-sizer';
import { Box, CircularProgress, Typography } from '@mui/material';

interface VirtualizedListProps<T> {
  /** Array of items to display */
  items: T[];
  /** Total count of items (for infinite loading) */
  itemCount?: number;
  /** Function to render each item */
  renderItem: (item: T, index: number, style: React.CSSProperties) => React.ReactNode;
  /** Function to get item height */
  getItemHeight?: (index: number) => number;
  /** Function to check if item is loaded */
  isItemLoaded?: (index: number) => boolean;
  /** Function to load more items */
  loadMoreItems?: (startIndex: number, stopIndex: number) => Promise<void>;
  /** Threshold for triggering loadMore */
  threshold?: number;
  /** Loading state */
  loading?: boolean;
  /** Empty state component */
  emptyComponent?: React.ReactNode;
  /** Error state component */
  errorComponent?: React.ReactNode;
  /** Whether there are more items to load */
  hasMore?: boolean;
  /** Overscan count for better scrolling performance */
  overscanCount?: number;
  /** Custom className */
  className?: string;
  /** Custom styles */
  style?: React.CSSProperties;
}

/**
 * High-performance virtualized list component for large datasets
 */
export function VirtualizedList<T>({
  items,
  itemCount,
  renderItem,
  getItemHeight = () => 80, // Default item height
  isItemLoaded = (index) => index < items.length,
  loadMoreItems = async () => {},
  threshold = 15,
  loading = false,
  emptyComponent,
  errorComponent,
  hasMore = false,
  overscanCount = 5,
  className,
  style,
}: VirtualizedListProps<T>) {
  const listRef = useRef<List>(null);
  const itemHeightCache = useRef<Map<number, number>>(new Map());

  // Calculate total item count
  const totalItemCount = itemCount || items.length;
  const effectiveItemCount = hasMore ? totalItemCount + 1 : totalItemCount;

  // Get cached item height or calculate
  const getCachedItemHeight = useCallback((index: number) => {
    if (itemHeightCache.current.has(index)) {
      return itemHeightCache.current.get(index)!;
    }
    const height = getItemHeight(index);
    itemHeightCache.current.set(index, height);
    return height;
  }, [getItemHeight]);

  // Handle item height changes
  const handleItemHeightChange = useCallback((index: number, height: number) => {
    const previousHeight = itemHeightCache.current.get(index);
    if (previousHeight !== height) {
      itemHeightCache.current.set(index, height);
      if (listRef.current) {
        listRef.current.resetAfterIndex(index);
      }
    }
  }, []);

  // Check if an item is loaded
  const isLoaded = useCallback((index: number) => {
    return hasMore ? index < items.length : isItemLoaded(index);
  }, [hasMore, items.length, isItemLoaded]);

  // Render individual item
  const Item = useCallback(({ index, style }: ListChildComponentProps) => {
    // Show loading indicator for last item if loading more
    if (hasMore && index === items.length) {
      return (
        <Box
          style={style}
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            p: 2,
          }}
        >
          <CircularProgress size={24} />
          <Typography variant="body2" sx={{ ml: 2 }}>
            Loading more...
          </Typography>
        </Box>
      );
    }

    // Render actual item
    if (index < items.length) {
      return (
        <MeasuredItem
          index={index}
          style={style}
          onHeightChange={handleItemHeightChange}
        >
          {renderItem(items[index], index, style)}
        </MeasuredItem>
      );
    }

    return null;
  }, [hasMore, items, renderItem, handleItemHeightChange]);

  // Handle empty state
  if (!loading && items.length === 0) {
    return (
      <Box
        className={className}
        style={style}
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          minHeight: 200,
        }}
      >
        {emptyComponent || (
          <Typography variant="body1" color="text.secondary">
            No items to display
          </Typography>
        )}
      </Box>
    );
  }

  // Handle error state
  if (errorComponent) {
    return (
      <Box
        className={className}
        style={style}
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          minHeight: 200,
        }}
      >
        {errorComponent}
      </Box>
    );
  }

  return (
    <Box className={className} style={{ height: '100%', width: '100%', ...style }}>
      <AutoSizer>
        {({ height, width }) => (
          <InfiniteLoader
            isItemLoaded={isLoaded}
            itemCount={effectiveItemCount}
            loadMoreItems={loadMoreItems}
            threshold={threshold}
          >
            {({ onItemsRendered, ref }) => (
              <List
                ref={(list) => {
                  ref(list);
                  listRef.current = list;
                }}
                height={height}
                width={width}
                itemCount={effectiveItemCount}
                itemSize={getCachedItemHeight}
                onItemsRendered={onItemsRendered}
                overscanCount={overscanCount}
                estimatedItemSize={80}
              >
                {Item}
              </List>
            )}
          </InfiniteLoader>
        )}
      </AutoSizer>
    </Box>
  );
}

/**
 * Component to measure and report item height changes
 */
interface MeasuredItemProps {
  index: number;
  style: React.CSSProperties;
  onHeightChange: (index: number, height: number) => void;
  children: React.ReactNode;
}

const MeasuredItem: React.FC<MeasuredItemProps> = ({
  index,
  style,
  onHeightChange,
  children,
}) => {
  const itemRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (itemRef.current) {
      const resizeObserver = new ResizeObserver(([entry]) => {
        if (entry.contentRect.height > 0) {
          onHeightChange(index, entry.contentRect.height);
        }
      });

      resizeObserver.observe(itemRef.current);

      return () => {
        resizeObserver.disconnect();
      };
    }
  }, [index, onHeightChange]);

  return (
    <div ref={itemRef} style={style}>
      {children}
    </div>
  );
};

export default VirtualizedList;