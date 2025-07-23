import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
  Button,
  Collapse,
  IconButton,
  InputAdornment,
  Slider,
  FormGroup,
  FormControlLabel,
  Checkbox,
} from '@mui/material';
import {
  Search as SearchIcon,
  FilterList as FilterIcon,
  Clear as ClearIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
} from '@mui/icons-material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';

import { AssetType, AssetStatus, AssetFilter } from '../../types/asset';

interface AssetFiltersProps {
  filter: AssetFilter;
  onChange: (filter: AssetFilter) => void;
  onClear: () => void;
  availableTags?: string[];
  expandable?: boolean;
}

const AssetFilters: React.FC<AssetFiltersProps> = ({
  filter,
  onChange,
  onClear,
  availableTags = [],
  expandable = true,
}) => {
  const [expanded, setExpanded] = useState(!expandable);
  const [fileSizeRange, setFileSizeRange] = useState<[number, number]>([0, 1000]); // MB

  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChange({ ...filter, search: event.target.value });
  };

  const handleTypeChange = (type: AssetType) => {
    const types = filter.types || [];
    const newTypes = types.includes(type)
      ? types.filter(t => t !== type)
      : [...types, type];
    onChange({ ...filter, types: newTypes });
  };

  const handleStatusChange = (event: SelectChangeEvent<AssetStatus[]>) => {
    const value = event.target.value;
    onChange({
      ...filter,
      status: typeof value === 'string' ? [value as AssetStatus] : value,
    });
  };

  const handleTagsChange = (event: SelectChangeEvent<string[]>) => {
    const value = event.target.value;
    onChange({
      ...filter,
      tags: typeof value === 'string' ? value.split(',') : value,
    });
  };

  const handleDateFromChange = (date: Date | null) => {
    onChange({ ...filter, dateFrom: date?.toISOString() });
  };

  const handleDateToChange = (date: Date | null) => {
    onChange({ ...filter, dateTo: date?.toISOString() });
  };

  const handleFileSizeChange = (event: Event, newValue: number | number[]) => {
    const [min, max] = newValue as number[];
    setFileSizeRange([min, max]);
    onChange({
      ...filter,
      sizeMin: min * 1024 * 1024, // Convert MB to bytes
      sizeMax: max * 1024 * 1024,
    });
  };

  const hasActiveFilters = () => {
    return (
      filter.search ||
      (filter.types && filter.types.length > 0) ||
      (filter.status && filter.status.length > 0) ||
      (filter.tags && filter.tags.length > 0) ||
      filter.dateFrom ||
      filter.dateTo ||
      filter.sizeMin ||
      filter.sizeMax
    );
  };

  const assetTypes = [
    { value: AssetType.VIDEO, label: 'Video' },
    { value: AssetType.AUDIO, label: 'Audio' },
    { value: AssetType.IMAGE, label: 'Image' },
    { value: AssetType.DOCUMENT, label: 'Document' },
    { value: AssetType.OTHER, label: 'Other' },
  ];

  const assetStatuses = [
    { value: AssetStatus.READY, label: 'Ready' },
    { value: AssetStatus.PROCESSING, label: 'Processing' },
    { value: AssetStatus.UPLOADING, label: 'Uploading' },
    { value: AssetStatus.ERROR, label: 'Error' },
    { value: AssetStatus.ARCHIVED, label: 'Archived' },
  ];

  return (
    <Paper sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <FilterIcon />
          <Typography variant="h6">Filters</Typography>
          {hasActiveFilters() && (
            <Chip
              label="Active"
              size="small"
              color="primary"
              onDelete={onClear}
            />
          )}
        </Box>
        {expandable && (
          <IconButton onClick={() => setExpanded(!expanded)} size="small">
            {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
        )}
      </Box>

      {/* Search Field - Always Visible */}
      <TextField
        fullWidth
        variant="outlined"
        placeholder="Search assets..."
        value={filter.search || ''}
        onChange={handleSearchChange}
        sx={{ mb: 2 }}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon />
            </InputAdornment>
          ),
          endAdornment: filter.search && (
            <InputAdornment position="end">
              <IconButton
                size="small"
                onClick={() => onChange({ ...filter, search: '' })}
              >
                <ClearIcon />
              </IconButton>
            </InputAdornment>
          ),
        }}
      />

      <Collapse in={expanded}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {/* Asset Types */}
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              Asset Type
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              {assetTypes.map((type) => (
                <Chip
                  key={type.value}
                  label={type.label}
                  onClick={() => handleTypeChange(type.value)}
                  color={filter.types?.includes(type.value) ? 'primary' : 'default'}
                  variant={filter.types?.includes(type.value) ? 'filled' : 'outlined'}
                />
              ))}
            </Box>
          </Box>

          {/* Status Filter */}
          <FormControl fullWidth>
            <InputLabel>Status</InputLabel>
            <Select
              multiple
              value={filter.status || []}
              onChange={handleStatusChange}
              renderValue={(selected) => (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {selected.map((value) => (
                    <Chip
                      key={value}
                      label={assetStatuses.find(s => s.value === value)?.label}
                      size="small"
                    />
                  ))}
                </Box>
              )}
            >
              {assetStatuses.map((status) => (
                <MenuItem key={status.value} value={status.value}>
                  <Checkbox checked={filter.status?.includes(status.value) || false} />
                  {status.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* Tags Filter */}
          {availableTags.length > 0 && (
            <FormControl fullWidth>
              <InputLabel>Tags</InputLabel>
              <Select
                multiple
                value={filter.tags || []}
                onChange={handleTagsChange}
                renderValue={(selected) => (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {selected.map((value) => (
                      <Chip key={value} label={value} size="small" />
                    ))}
                  </Box>
                )}
              >
                {availableTags.map((tag) => (
                  <MenuItem key={tag} value={tag}>
                    <Checkbox checked={filter.tags?.includes(tag) || false} />
                    {tag}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}

          {/* Date Range */}
          <LocalizationProvider dateAdapter={AdapterDateFns}>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <DatePicker
                label="From Date"
                value={filter.dateFrom ? new Date(filter.dateFrom) : null}
                onChange={handleDateFromChange}
                slotProps={{
                  textField: {
                    fullWidth: true,
                    size: 'small',
                  },
                }}
              />
              <DatePicker
                label="To Date"
                value={filter.dateTo ? new Date(filter.dateTo) : null}
                onChange={handleDateToChange}
                slotProps={{
                  textField: {
                    fullWidth: true,
                    size: 'small',
                  },
                }}
              />
            </Box>
          </LocalizationProvider>

          {/* File Size Range */}
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              File Size (MB)
            </Typography>
            <Box sx={{ px: 2 }}>
              <Slider
                value={fileSizeRange}
                onChange={handleFileSizeChange}
                valueLabelDisplay="auto"
                min={0}
                max={1000}
                marks={[
                  { value: 0, label: '0' },
                  { value: 250, label: '250' },
                  { value: 500, label: '500' },
                  { value: 750, label: '750' },
                  { value: 1000, label: '1GB' },
                ]}
              />
            </Box>
          </Box>

          {/* Clear Filters Button */}
          {hasActiveFilters() && (
            <Button
              variant="outlined"
              onClick={onClear}
              startIcon={<ClearIcon />}
              fullWidth
            >
              Clear All Filters
            </Button>
          )}
        </Box>
      </Collapse>
    </Paper>
  );
};

export default AssetFilters;