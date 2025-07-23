import React from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Badge,
  Divider,
} from '@mui/material';
import {
  ExpandMore as ExpandIcon,
  Category as CategoryIcon,
  Label as TagIcon,
  Person as PersonIcon,
  CalendarToday as DateIcon,
} from '@mui/icons-material';
import AssetCard from '../assets/AssetCard';
import AssetListItem from '../assets/AssetListItem';
import { Asset } from '../../types/asset';
import { SearchFacet, SearchResponse } from '../../services/searchApi';

interface SearchResultsProps {
  results: SearchResponse;
  viewMode: 'grid' | 'list';
  loading?: boolean;
  onAssetClick: (asset: Asset) => void;
  onAssetSelect?: (asset: Asset, selected: boolean) => void;
  selectedAssets?: Set<string>;
  onFacetClick?: (field: string, value: string) => void;
  showFacets?: boolean;
}

const SearchResults: React.FC<SearchResultsProps> = ({
  results,
  viewMode,
  loading = false,
  onAssetClick,
  onAssetSelect,
  selectedAssets = new Set(),
  onFacetClick,
  showFacets = true,
}) => {
  const getFacetIcon = (field: string) => {
    switch (field) {
      case 'type':
        return <CategoryIcon fontSize="small" />;
      case 'tags':
        return <TagIcon fontSize="small" />;
      case 'createdBy':
        return <PersonIcon fontSize="small" />;
      case 'createdAt':
        return <DateIcon fontSize="small" />;
      default:
        return null;
    }
  };

  const formatFacetLabel = (field: string) => {
    switch (field) {
      case 'type':
        return 'Asset Types';
      case 'tags':
        return 'Tags';
      case 'createdBy':
        return 'Created By';
      case 'createdAt':
        return 'Date Created';
      default:
        return field.charAt(0).toUpperCase() + field.slice(1);
    }
  };

  const renderFacets = () => {
    if (!showFacets || !results.facets || results.facets.length === 0) {
      return null;
    }

    return (
      <Box sx={{ mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Refine Results
        </Typography>
        {results.facets.map((facet) => (
          <Accordion key={facet.field} defaultExpanded>
            <AccordionSummary expandIcon={<ExpandIcon />}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {getFacetIcon(facet.field)}
                <Typography>{formatFacetLabel(facet.field)}</Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <List dense>
                {facet.values.slice(0, 10).map((value) => (
                  <ListItem key={value.value} disablePadding>
                    <ListItemButton
                      onClick={() => onFacetClick?.(facet.field, value.value)}
                    >
                      <ListItemText primary={value.value} />
                      <Badge badgeContent={value.count} color="default" />
                    </ListItemButton>
                  </ListItem>
                ))}
                {facet.values.length > 10 && (
                  <ListItem>
                    <ListItemText
                      secondary={`+${facet.values.length - 10} more`}
                    />
                  </ListItem>
                )}
              </List>
            </AccordionDetails>
          </Accordion>
        ))}
      </Box>
    );
  };

  const renderResults = () => {
    if (results.assets.length === 0) {
      return (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" color="text.secondary">
            No results found
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Try adjusting your search terms or filters
          </Typography>
        </Paper>
      );
    }

    if (viewMode === 'grid') {
      return (
        <Grid container spacing={2}>
          {results.assets.map((asset) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={asset.id}>
              <AssetCard
                asset={asset}
                onClick={() => onAssetClick(asset)}
                onSelect={onAssetSelect ? (selected) => onAssetSelect(asset, selected) : undefined}
                selected={selectedAssets.has(asset.id)}
                highlight={results.highlights?.[asset.id]}
              />
            </Grid>
          ))}
        </Grid>
      );
    }

    return (
      <Paper>
        <List>
          {results.assets.map((asset, index) => (
            <React.Fragment key={asset.id}>
              {index > 0 && <Divider />}
              <AssetListItem
                asset={asset}
                onClick={() => onAssetClick(asset)}
                onSelect={onAssetSelect ? (selected) => onAssetSelect(asset, selected) : undefined}
                selected={selectedAssets.has(asset.id)}
                highlight={results.highlights?.[asset.id]}
              />
            </React.Fragment>
          ))}
        </List>
      </Paper>
    );
  };

  return (
    <Box>
      {/* Search Metadata */}
      <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
        <Typography variant="body2" color="text.secondary">
          {results.total} results found
        </Typography>
        {results.queryTime && (
          <Chip
            label={`${results.queryTime}ms`}
            size="small"
            variant="outlined"
          />
        )}
      </Box>

      {/* Main Content */}
      <Grid container spacing={3}>
        {showFacets && results.facets && results.facets.length > 0 && (
          <Grid item xs={12} md={3}>
            {renderFacets()}
          </Grid>
        )}
        <Grid item xs={12} md={showFacets && results.facets?.length ? 9 : 12}>
          {renderResults()}
        </Grid>
      </Grid>
    </Box>
  );
};

export default SearchResults;