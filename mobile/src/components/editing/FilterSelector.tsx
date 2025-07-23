/**
 * Filter Selector Component
 * 
 * Interface for selecting and previewing filters
 */

import React, {useState} from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Dimensions,
} from 'react-native';
import {Text} from 'react-native-paper';
import FastImage from 'react-native-fast-image';

import {editingService, Filter} from '@/services/editingService';
import {colors, spacing, typography} from '@/constants/theme';

const {width: screenWidth} = Dimensions.get('window');
const FILTER_SIZE = (screenWidth - spacing.md * 4) / 3;

interface FilterSelectorProps {
  onSelectFilter: (filter: Filter) => void;
}

export const FilterSelector: React.FC<FilterSelectorProps> = ({
  onSelectFilter,
}) => {
  const [selectedCategory, setSelectedCategory] = useState<Filter['category']>('basic');
  const filters = editingService.getFilters();
  
  const categories: Array<{key: Filter['category']; label: string}> = [
    {key: 'basic', label: 'Basic'},
    {key: 'vintage', label: 'Vintage'},
    {key: 'artistic', label: 'Artistic'},
    {key: 'color', label: 'Color'},
  ];

  const filteredFilters = filters.filter(f => f.category === selectedCategory);

  return (
    <View style={styles.container}>
      {/* Category tabs */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.categoryTabs}>
        {categories.map((category) => (
          <TouchableOpacity
            key={category.key}
            style={[
              styles.categoryTab,
              selectedCategory === category.key && styles.categoryTabActive,
            ]}
            onPress={() => setSelectedCategory(category.key)}>
            <Text
              style={[
                styles.categoryTabText,
                selectedCategory === category.key && styles.categoryTabTextActive,
              ]}>
              {category.label}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* Filter grid */}
      <ScrollView
        style={styles.filterGrid}
        contentContainerStyle={styles.filterGridContent}
        showsVerticalScrollIndicator={false}>
        <View style={styles.filtersRow}>
          {filteredFilters.map((filter) => (
            <TouchableOpacity
              key={filter.id}
              style={styles.filterItem}
              onPress={() => onSelectFilter(filter)}>
              <View style={styles.filterPreview}>
                {/* In a real app, this would show a preview with the filter applied */}
                <View style={[
                  styles.filterPreviewPlaceholder,
                  filter.id === 'grayscale' && {backgroundColor: colors.gray600},
                  filter.id === 'sepia' && {backgroundColor: '#704214'},
                  filter.id === 'vintage' && {backgroundColor: '#8B7355'},
                  filter.id === 'noir' && {backgroundColor: colors.black},
                  filter.id === 'vibrant' && {backgroundColor: colors.secondary},
                  filter.id === 'cool' && {backgroundColor: '#4A90E2'},
                  filter.id === 'warm' && {backgroundColor: '#F5A623'},
                ]} />
              </View>
              <Text style={styles.filterName}>{filter.name}</Text>
            </TouchableOpacity>
          ))}
        </View>
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.surface,
  },
  categoryTabs: {
    borderBottomWidth: 1,
    borderBottomColor: colors.gray300,
  },
  categoryTab: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
  },
  categoryTabActive: {
    borderBottomWidth: 2,
    borderBottomColor: colors.primary,
  },
  categoryTabText: {
    ...typography.bodyMedium,
    color: colors.gray600,
  },
  categoryTabTextActive: {
    color: colors.primary,
    fontWeight: '600',
  },
  filterGrid: {
    flex: 1,
  },
  filterGridContent: {
    padding: spacing.md,
  },
  filtersRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  filterItem: {
    width: FILTER_SIZE,
    marginBottom: spacing.md,
  },
  filterPreview: {
    width: FILTER_SIZE,
    height: FILTER_SIZE,
    borderRadius: 8,
    overflow: 'hidden',
    marginBottom: spacing.xs,
  },
  filterPreviewPlaceholder: {
    flex: 1,
    backgroundColor: colors.gray300,
  },
  filterName: {
    ...typography.bodySmall,
    color: colors.onSurface,
    textAlign: 'center',
  },
});