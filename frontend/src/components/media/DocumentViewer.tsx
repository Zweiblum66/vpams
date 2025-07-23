import React from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Download as DownloadIcon,
  OpenInNew as OpenIcon,
  Description as DocumentIcon,
} from '@mui/icons-material';

interface DocumentViewerProps {
  src: string;
  title?: string;
  type?: string;
  width?: string | number;
  height?: string | number;
  onDownload?: () => void;
}

const DocumentViewer: React.FC<DocumentViewerProps> = ({
  src,
  title,
  type,
  width = '100%',
  height = '600px',
  onDownload,
}) => {
  const isOfficeDoc = type && ['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'].includes(type.toLowerCase());
  const isPdf = type && type.toLowerCase() === 'pdf';
  
  const handleOpenInNewTab = () => {
    window.open(src, '_blank');
  };

  // For Office documents, use Office Online viewer
  const getOfficeViewerUrl = () => {
    return `https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(src)}`;
  };

  return (
    <Paper
      sx={{
        width,
        height,
        position: 'relative',
        overflow: 'hidden',
        backgroundColor: 'grey.100',
        borderRadius: 2,
      }}
      elevation={3}
    >
      {/* Header */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          p: 2,
          borderBottom: 1,
          borderColor: 'divider',
          backgroundColor: 'background.paper',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <DocumentIcon color="action" />
          <Typography variant="subtitle1">
            {title || 'Document'}
          </Typography>
          {type && (
            <Typography variant="caption" color="text.secondary">
              ({type.toUpperCase()})
            </Typography>
          )}
        </Box>
        
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="Open in New Tab">
            <IconButton onClick={handleOpenInNewTab} size="small">
              <OpenIcon />
            </IconButton>
          </Tooltip>
          
          {onDownload && (
            <Tooltip title="Download">
              <IconButton onClick={onDownload} size="small">
                <DownloadIcon />
              </IconButton>
            </Tooltip>
          )}
        </Box>
      </Box>

      {/* Document Viewer */}
      <Box sx={{ width: '100%', height: 'calc(100% - 64px)' }}>
        {isPdf ? (
          // PDF viewer
          <iframe
            src={`${src}#toolbar=1&navpanes=0&scrollbar=1&view=FitH`}
            width="100%"
            height="100%"
            style={{ border: 'none' }}
            title={title || 'PDF Document'}
          />
        ) : isOfficeDoc ? (
          // Office document viewer
          <iframe
            src={getOfficeViewerUrl()}
            width="100%"
            height="100%"
            style={{ border: 'none' }}
            title={title || 'Office Document'}
          />
        ) : (
          // Fallback for other document types
          <Box
            sx={{
              width: '100%',
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 2,
              p: 4,
            }}
          >
            <DocumentIcon sx={{ fontSize: 80, color: 'text.secondary' }} />
            <Typography variant="h6" color="text.secondary">
              Document Preview Not Available
            </Typography>
            <Typography variant="body2" color="text.secondary" align="center">
              This document type cannot be previewed in the browser.
              Please download the file to view it.
            </Typography>
          </Box>
        )}
      </Box>
    </Paper>
  );
};

export default DocumentViewer;