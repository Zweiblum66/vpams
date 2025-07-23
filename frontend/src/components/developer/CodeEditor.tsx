import React, { useState } from 'react';
import {
  Box,
  Tabs,
  Tab,
  Paper,
  Typography,
  IconButton,
  Toolbar,
  Stack,
  Button,
  Menu,
  MenuItem,
  Divider
} from '@mui/material';
import {
  Code as CodeIcon,
  Settings as SettingsIcon,
  Add as AddIcon,
  MoreVert as MoreVertIcon,
  Download as DownloadIcon,
  Upload as UploadIcon,
  Delete as DeleteIcon
} from '@mui/icons-material';
import Editor from '@monaco-editor/react';

interface CodeEditorProps {
  files: Record<string, string>;
  onFileChange: (filename: string, content: string) => void;
  pluginType?: string;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`code-editor-tabpanel-${index}`}
      aria-labelledby={`code-editor-tab-${index}`}
      {...other}
    >
      {value === index && <Box>{children}</Box>}
    </div>
  );
}

const FILE_LANGUAGES: Record<string, string> = {
  '.py': 'python',
  '.js': 'javascript',
  '.ts': 'typescript',
  '.json': 'json',
  '.yaml': 'yaml',
  '.yml': 'yaml',
  '.txt': 'plaintext',
  '.md': 'markdown',
  '.sh': 'shell'
};

const getLanguageFromFilename = (filename: string): string => {
  const extension = '.' + filename.split('.').pop();
  return FILE_LANGUAGES[extension] || 'plaintext';
};

export const CodeEditor: React.FC<CodeEditorProps> = ({
  files,
  onFileChange,
  pluginType
}) => {
  const [currentTab, setCurrentTab] = useState(0);
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const [newFileName, setNewFileName] = useState('');

  const fileNames = Object.keys(files);
  const currentFileName = fileNames[currentTab] || '';
  const currentFileContent = files[currentFileName] || '';

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  const handleEditorChange = (value: string | undefined) => {
    if (value !== undefined && currentFileName) {
      onFileChange(currentFileName, value);
    }
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setMenuAnchor(event.currentTarget);
  };

  const handleMenuClose = () => {
    setMenuAnchor(null);
  };

  const addNewFile = () => {
    const fileName = prompt('Enter file name (e.g., utils.py):');
    if (fileName && !files[fileName]) {
      onFileChange(fileName, '');
      const newIndex = Object.keys(files).length;
      setCurrentTab(newIndex);
    }
    handleMenuClose();
  };

  const deleteCurrentFile = () => {
    if (currentFileName && Object.keys(files).length > 1) {
      const newFiles = { ...files };
      delete newFiles[currentFileName];
      
      // Update files through parent component
      Object.keys(newFiles).forEach((filename, index) => {
        if (index === 0) {
          onFileChange(filename, newFiles[filename]);
          setCurrentTab(0);
        }
      });
    }
    handleMenuClose();
  };

  const downloadFile = () => {
    if (currentFileName && currentFileContent) {
      const blob = new Blob([currentFileContent], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = currentFileName;
      a.click();
      URL.revokeObjectURL(url);
    }
    handleMenuClose();
  };

  const uploadFile = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.py,.js,.ts,.json,.yaml,.yml,.txt,.md,.sh';
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
          const content = e.target?.result as string;
          onFileChange(file.name, content);
          // Switch to the uploaded file
          const newIndex = Object.keys(files).findIndex(name => name === file.name);
          if (newIndex >= 0) {
            setCurrentTab(newIndex);
          }
        };
        reader.readAsText(file);
      }
    };
    input.click();
    handleMenuClose();
  };

  return (
    <Paper elevation={1} sx={{ height: 600, display: 'flex', flexDirection: 'column' }}>
      {/* File Tabs and Toolbar */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', bgcolor: 'background.paper' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Tabs 
            value={currentTab} 
            onChange={handleTabChange}
            variant="scrollable"
            scrollButtons="auto"
            sx={{ flexGrow: 1 }}
          >
            {fileNames.map((filename, index) => (
              <Tab
                key={filename}
                label={filename}
                icon={<CodeIcon />}
                iconPosition="start"
                sx={{ minHeight: 48 }}
              />
            ))}
          </Tabs>
          
          <Stack direction="row" spacing={1} sx={{ px: 1 }}>
            <IconButton size="small" onClick={handleMenuOpen}>
              <MoreVertIcon />
            </IconButton>
          </Stack>
        </Box>
      </Box>

      {/* File Actions Menu */}
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={addNewFile}>
          <AddIcon sx={{ mr: 1 }} />
          Add New File
        </MenuItem>
        <MenuItem onClick={uploadFile}>
          <UploadIcon sx={{ mr: 1 }} />
          Upload File
        </MenuItem>
        <MenuItem onClick={downloadFile} disabled={!currentFileName}>
          <DownloadIcon sx={{ mr: 1 }} />
          Download File
        </MenuItem>
        <Divider />
        <MenuItem 
          onClick={deleteCurrentFile} 
          disabled={!currentFileName || Object.keys(files).length <= 1}
          sx={{ color: 'error.main' }}
        >
          <DeleteIcon sx={{ mr: 1 }} />
          Delete File
        </MenuItem>
      </Menu>

      {/* Editor Content */}
      <Box sx={{ flexGrow: 1, position: 'relative' }}>
        {fileNames.map((filename, index) => (
          <TabPanel key={filename} value={currentTab} index={index}>
            <Box sx={{ height: '100%', minHeight: 500 }}>
              <Editor
                height="500px"
                language={getLanguageFromFilename(filename)}
                theme="vs-dark"
                value={files[filename] || ''}
                onChange={handleEditorChange}
                options={{
                  fontSize: 14,
                  fontFamily: '"Fira Code", "Monaco", "Menlo", monospace',
                  ligatures: true,
                  minimap: { enabled: true },
                  automaticLayout: true,
                  wordWrap: 'on',
                  lineNumbers: 'on',
                  folding: true,
                  bracketMatching: 'always',
                  autoIndent: 'full',
                  formatOnPaste: true,
                  formatOnType: true,
                  tabSize: 4,
                  insertSpaces: true,
                  scrollBeyondLastLine: false,
                  smoothScrolling: true,
                  cursorBlinking: 'smooth',
                  renderWhitespace: 'selection',
                  multiCursorModifier: 'ctrlCmd'
                }}
              />
            </Box>
          </TabPanel>
        ))}
      </Box>

      {/* Status Bar */}
      <Box 
        sx={{ 
          px: 2, 
          py: 1, 
          bgcolor: 'grey.100', 
          borderTop: 1, 
          borderColor: 'divider',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}
      >
        <Typography variant="body2" color="text.secondary">
          {currentFileName} • {getLanguageFromFilename(currentFileName)} • {currentFileContent.split('\n').length} lines
        </Typography>
        
        <Stack direction="row" spacing={2} alignItems="center">
          {pluginType && (
            <Typography variant="body2" color="text.secondary">
              Plugin Type: {pluginType}
            </Typography>
          )}
          <Typography variant="body2" color="text.secondary">
            {currentFileContent.length} characters
          </Typography>
        </Stack>
      </Box>
    </Paper>
  );
};

export default CodeEditor;