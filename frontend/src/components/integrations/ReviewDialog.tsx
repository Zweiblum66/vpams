/**
 * Review Dialog for Rating API Integrations
 */

import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Typography,
  Box,
  Rating,
  Alert
} from '@mui/material';
import { LoadingButton } from '@mui/lab';
import { Star, RateReview } from '@mui/icons-material';

import { APIListing } from '../../types/integration';


interface ReviewDialogProps {
  open: boolean;
  onClose: () => void;
  listing: APIListing;
  onSubmit: (rating: number, review?: string) => void;
  isSubmitting: boolean;
}

export const ReviewDialog: React.FC<ReviewDialogProps> = ({
  open,
  onClose,
  listing,
  onSubmit,
  isSubmitting
}) => {
  const [rating, setRating] = useState<number>(0);
  const [review, setReview] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = () => {
    if (rating === 0) {
      setError('Please select a rating');
      return;
    }

    setError('');
    onSubmit(rating, review || undefined);
  };

  const handleClose = () => {
    setRating(0);
    setReview('');
    setError('');
    onClose();
  };

  const ratingLabels: { [index: string]: string } = {
    1: 'Poor',
    2: 'Fair',
    3: 'Good',
    4: 'Very Good',
    5: 'Excellent'
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={2}>
          <RateReview color="primary" />
          <Box>
            <Typography variant="h6">Rate & Review</Typography>
            <Typography variant="body2" color="text.secondary">
              {listing.name}
            </Typography>
          </Box>
        </Box>
      </DialogTitle>

      <DialogContent>
        <Alert severity="info" sx={{ mb: 3 }}>
          Share your experience with this integration to help other users make informed decisions.
        </Alert>

        <Box mb={3}>
          <Typography variant="subtitle2" gutterBottom>
            Overall Rating *
          </Typography>
          <Box display="flex" alignItems="center" gap={2}>
            <Rating
              size="large"
              value={rating}
              onChange={(_, newValue) => {
                setRating(newValue || 0);
                setError('');
              }}
            />
            {rating > 0 && (
              <Typography variant="body2" color="text.secondary">
                {ratingLabels[rating.toString()]}
              </Typography>
            )}
          </Box>
          {error && (
            <Typography variant="caption" color="error" sx={{ mt: 1 }}>
              {error}
            </Typography>
          )}
        </Box>

        <Box mb={3}>
          <Typography variant="subtitle2" gutterBottom>
            Review (Optional)
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={4}
            value={review}
            onChange={(e) => setReview(e.target.value)}
            placeholder="Share your thoughts about this integration..."
            helperText={`${review.length}/500 characters`}
            inputProps={{ maxLength: 500 }}
          />
        </Box>

        <Box display="flex" alignItems="center" gap={2} p={2} bgcolor="grey.50" borderRadius={1}>
          <Box>
            <Typography variant="body2" fontWeight="medium">
              Current Rating: {listing.rating_average.toFixed(1)}/5
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Based on {listing.rating_count} reviews
            </Typography>
          </Box>
          <Box flexGrow={1}>
            <Rating
              value={listing.rating_average}
              precision={0.1}
              readOnly
              size="small"
            />
          </Box>
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose} disabled={isSubmitting}>
          Cancel
        </Button>
        <LoadingButton
          onClick={handleSubmit}
          variant="contained"
          startIcon={<Star />}
          loading={isSubmitting}
        >
          Submit Rating
        </LoadingButton>
      </DialogActions>
    </Dialog>
  );
};