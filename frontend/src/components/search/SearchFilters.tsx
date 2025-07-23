import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Button,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Slider,
  FormControlLabel,
  Checkbox,
  IconButton,
  Tooltip,
  Grid,
} from '@mui/material';
import {
  ExpandMore as ExpandIcon,
  Clear as ClearIcon,
  Save as SaveIcon,
  RestoreOutlined as ResetIcon,
} from '@mui/icons-material';
import { AssetType, AssetStatus, AssetFilter } from '../../types/asset';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';

interface SearchFiltersProps {
  filters: AssetFilter;
  onFiltersChange: (filters: AssetFilter) => void;
  onClearFilters: () => void;
  onSaveFilter?: (name: string) => void;
  availableTags?: string[];
  availableProjects?: Array<{ id: string; name: string }>;
  availableUsers?: Array<{ id: string; name: string }>;
}

const SearchFilters: React.FC<SearchFiltersProps> = ({
  filters,
  onFiltersChange,
  onClearFilters,
  onSaveFilter,
  availableTags = [],
  availableProjects = [],
  availableUsers = [],
}) => {
  const [expanded, setExpanded] = useState<string | false>('basic');
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [filterName, setFilterName] = useState('');

  const handleAccordionChange = (panel: string) => (_: React.SyntheticEvent, isExpanded: boolean) => {
    setExpanded(isExpanded ? panel : false);
  };

  const handleFilterChange = (field: keyof AssetFilter, value: any) => {
    onFiltersChange({
      ...filters,
      [field]: value,
    });
  };

  const handleSizeRangeChange = (_: Event, newValue: number | number[]) => {
    const [min, max] = newValue as number[];
    handleFilterChange('sizeMin', min * 1024 * 1024); // Convert MB to bytes
    handleFilterChange('sizeMax', max * 1024 * 1024);
  };

  const formatFileSize = (bytes: number) => {
    return `${Math.round(bytes / (1024 * 1024))} MB`;
  };

  const activeFilterCount = Object.entries(filters).filter(([_, value]) => {
    if (Array.isArray(value)) return value.length > 0;
    return value !== undefined && value !== null && value !== '';
  }).length;

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Paper sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="h6">Advanced Filters</Typography>
            {activeFilterCount > 0 && (
              <Chip label={`${activeFilterCount} active`} size="small" color="primary" />
            )}
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            {onSaveFilter && (
              <Tooltip title="Save Filter">
                <IconButton size="small" onClick={() => setSaveDialogOpen(true)}>
                  <SaveIcon />
                </IconButton>
              </Tooltip>
            )}
            <Tooltip title="Clear All Filters">
              <IconButton size="small" onClick={onClearFilters}>
                <ClearIcon />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        {/* Basic Filters */}
        <Accordion expanded={expanded === 'basic'} onChange={handleAccordionChange('basic')}>
          <AccordionSummary expandIcon={<ExpandIcon />}>
            <Typography>Basic Filters</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Asset Type</InputLabel>
                  <Select
                    multiple
                    value={filters.types || []}
                    onChange={(e) => handleFilterChange('types', e.target.value)}
                    renderValue={(selected) => (
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {(selected as AssetType[]).map((value) => (
                          <Chip key={value} label={value} size="small" />
                        ))}
                      </Box>
                    )}
                  >
                    {Object.values(AssetType).map((type) => (
                      <MenuItem key={type} value={type}>
                        {type}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Status</InputLabel>
                  <Select
                    multiple
                    value={filters.status || []}
                    onChange={(e) => handleFilterChange('status', e.target.value)}
                    renderValue={(selected) => (
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {(selected as AssetStatus[]).map((value) => (
                          <Chip key={value} label={value} size="small" />
                        ))}
                      </Box>
                    )}
                  >
                    {Object.values(AssetStatus).map((status) => (
                      <MenuItem key={status} value={status}>
                        {status}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Tags</InputLabel>
                  <Select
                    multiple
                    value={filters.tags || []}
                    onChange={(e) => handleFilterChange('tags', e.target.value)}
                    renderValue={(selected) => (
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {(selected as string[]).map((value) => (
                          <Chip key={value} label={value} size="small" />
                        ))}
                      </Box>
                    )}
                  >
                    {availableTags.map((tag) => (
                      <MenuItem key={tag} value={tag}>
                        {tag}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Project</InputLabel>
                  <Select
                    value={filters.projectId || ''}
                    onChange={(e) => handleFilterChange('projectId', e.target.value || undefined)}
                  >
                    <MenuItem value="">All Projects</MenuItem>
                    {availableProjects.map((project) => (
                      <MenuItem key={project.id} value={project.id}>
                        {project.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
            </Grid>
          </AccordionDetails>
        </Accordion>

        {/* Date Filters */}
        <Accordion expanded={expanded === 'date'} onChange={handleAccordionChange('date')}>
          <AccordionSummary expandIcon={<ExpandIcon />}>
            <Typography>Date Range</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <DatePicker
                  label="From Date"
                  value={filters.dateFrom ? new Date(filters.dateFrom) : null}
                  onChange={(newValue) => handleFilterChange('dateFrom', newValue?.toISOString())}
                  renderInput={(params) => <TextField {...params} fullWidth />}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <DatePicker
                  label="To Date"
                  value={filters.dateTo ? new Date(filters.dateTo) : null}
                  onChange={(newValue) => handleFilterChange('dateTo', newValue?.toISOString())}
                  renderInput={(params) => <TextField {...params} fullWidth />}
                />
              </Grid>
            </Grid>
          </AccordionDetails>
        </Accordion>

        {/* Advanced Filters */}
        <Accordion expanded={expanded === 'advanced'} onChange={handleAccordionChange('advanced')}>
          <AccordionSummary expandIcon={<ExpandIcon />}>
            <Typography>Advanced</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <Typography gutterBottom>File Size (MB)</Typography>
                <Slider
                  value={[
                    (filters.sizeMin || 0) / (1024 * 1024),
                    (filters.sizeMax || 10000 * 1024 * 1024) / (1024 * 1024),
                  ]}
                  onChange={handleSizeRangeChange}
                  valueLabelDisplay="auto"
                  valueLabelFormat={formatFileSize}
                  min={0}
                  max={10000}
                  marks={[
                    { value: 0, label: '0 MB' },
                    { value: 100, label: '100 MB' },
                    { value: 1000, label: '1 GB' },
                    { value: 10000, label: '10 GB' },
                  ]}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Created By</InputLabel>
                  <Select
                    value={filters.createdBy || ''}
                    onChange={(e) => handleFilterChange('createdBy', e.target.value || undefined)}
                  >
                    <MenuItem value="">All Users</MenuItem>
                    {availableUsers.map((user) => (
                      <MenuItem key={user.id} value={user.id}>
                        {user.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Folder</InputLabel>
                  <Select
                    value={filters.folderId || ''}
                    onChange={(e) => handleFilterChange('folderId', e.target.value || undefined)}
                  >
                    <MenuItem value="">All Folders</MenuItem>
                    <MenuItem value="root">Root</MenuItem>
                    {/* Add folder options here */}
                  </Select>
                </FormControl>
              </Grid>
            </Grid>
          </AccordionDetails>
        </Accordion>

        {/* Applied Filters Summary */}
        {activeFilterCount > 0 && (
          <Box sx={{ mt: 2, p: 2, backgroundColor: 'action.hover', borderRadius: 1 }}>
            <Typography variant="subtitle2" gutterBottom>
              Applied Filters:
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {filters.types && filters.types.length > 0 && (
                <Chip
                  label={`Types: ${filters.types.join(', ')}`}
                  onDelete={() => handleFilterChange('types', [])}
                  size="small"
                />
              )}
              {filters.status && filters.status.length > 0 && (
                <Chip
                  label={`Status: ${filters.status.join(', ')}`}
                  onDelete={() => handleFilterChange('status', [])}
                  size="small"
                />
              )}
              {filters.tags && filters.tags.length > 0 && (
                <Chip
                  label={`Tags: ${filters.tags.join(', ')}`}
                  onDelete={() => handleFilterChange('tags', [])}
                  size="small"
                />
              )}
              {filters.dateFrom && (
                <Chip
                  label={`From: ${new Date(filters.dateFrom).toLocaleDateString()}`}
                  onDelete={() => handleFilterChange('dateFrom', undefined)}
                  size="small"
                />
              )}
              {filters.dateTo && (
                <Chip
                  label={`To: ${new Date(filters.dateTo).toLocaleDateString()}`}
                  onDelete={() => handleFilterChange('dateTo', undefined)}
                  size="small"
                />
              )}
            </Box>
          </Box>
        )}
      </Paper>
    </LocalizationProvider>
  );
};

export default SearchFilters;