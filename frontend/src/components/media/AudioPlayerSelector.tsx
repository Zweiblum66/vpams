import React, { useState } from 'react';
import {
  Box,
  Paper,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
  Divider,
} from '@mui/material';
import {
  Waves as WaveformIcon,
  PlayCircle as StandardIcon,
} from '@mui/icons-material';
import AudioPlayer from './AudioPlayer';
import WaveformPlayer from './WaveformPlayer';
import { Asset } from '../../types/asset';

interface AudioPlayerSelectorProps {
  asset: Asset;
  height?: number;
  onTimeUpdate?: (currentTime: number) => void;
  onMarkerAdd?: (time: number, text: string) => void;
  onTrimExport?: (startTime: number, endTime: number) => void;
  onRegionCreate?: (region: any) => void;
}

type PlayerType = 'standard' | 'waveform';

const AudioPlayerSelector: React.FC<AudioPlayerSelectorProps> = ({
  asset,
  height = 200,
  onTimeUpdate,
  onMarkerAdd,
  onTrimExport,
  onRegionCreate,
}) => {
  const [playerType, setPlayerType] = useState<PlayerType>('waveform');

  const handlePlayerTypeChange = (event: React.MouseEvent<HTMLElement>, newType: PlayerType | null) => {
    if (newType !== null) {
      setPlayerType(newType);
    }
  };

  return (
    <Box>
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Audio Player</Typography>
          <ToggleButtonGroup
            value={playerType}
            exclusive
            onChange={handlePlayerTypeChange}
            size="small"
          >
            <ToggleButton value="standard">
              <StandardIcon sx={{ mr: 1 }} />
              Standard
            </ToggleButton>
            <ToggleButton value="waveform">
              <WaveformIcon sx={{ mr: 1 }} />
              Waveform
            </ToggleButton>
          </ToggleButtonGroup>
        </Box>
        
        <Divider sx={{ mb: 2 }} />
        
        {playerType === 'standard' ? (
          <AudioPlayer
            src={asset.previewUrl || asset.originalUrl}
            title={asset.name}
            albumArt={asset.thumbnailUrl}
          />
        ) : (
          <WaveformPlayer
            asset={asset}
            height={height}
            onTimeUpdate={onTimeUpdate}
            onMarkerAdd={onMarkerAdd}
            onTrimExport={onTrimExport}
            onRegionCreate={onRegionCreate}
          />
        )}
      </Paper>
    </Box>
  );
};

export default AudioPlayerSelector;