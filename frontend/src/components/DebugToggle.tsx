import React, { useState, useEffect } from 'react';
import { Fab, Tooltip } from '@mui/material';
import { BugReport } from '@mui/icons-material';
import DebugPanel from './DebugPanel';

const DebugToggle: React.FC = () => {
  const [debugPanelOpen, setDebugPanelOpen] = useState(false);
  const [showDebugButton, setShowDebugButton] = useState(false);

  useEffect(() => {
    // Only show debug button in development or when explicitly enabled
    const shouldShowDebug = 
      process.env.NODE_ENV === 'development' || 
      localStorage.getItem('mams_debug_enabled') === 'true';
    
    setShowDebugButton(shouldShowDebug);

    // Keyboard shortcut to toggle debug panel (Ctrl+Shift+D)
    const handleKeyPress = (event: KeyboardEvent) => {
      if (event.ctrlKey && event.shiftKey && event.key === 'D') {
        event.preventDefault();
        setDebugPanelOpen(prev => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, []);

  if (!showDebugButton) {
    return null;
  }

  return (
    <>
      <Tooltip title="Debug Panel (Ctrl+Shift+D)" placement="left">
        <Fab
          color="secondary"
          size="small"
          onClick={() => setDebugPanelOpen(true)}
          sx={{
            position: 'fixed',
            bottom: 16,
            right: 16,
            zIndex: 1000,
          }}
        >
          <BugReport />
        </Fab>
      </Tooltip>

      <DebugPanel
        open={debugPanelOpen}
        onClose={() => setDebugPanelOpen(false)}
      />
    </>
  );
};

export default DebugToggle;