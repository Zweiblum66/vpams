import { createTheme } from '@mui/material/styles';
import { blue, red, green, orange, grey, purple } from '@mui/material/colors';

declare module '@mui/material/styles' {
  interface Palette {
    neutral: Palette['primary'];
    media: Palette['primary'];
  }

  interface PaletteOptions {
    neutral?: PaletteOptions['primary'];
    media?: PaletteOptions['primary'];
  }
}

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
      light: '#42a5f5',
      dark: '#1565c0',
    },
    secondary: {
      main: '#424242',
      light: '#757575',
      dark: '#212121',
    },
    neutral: {
      main: '#64748b',
      light: '#94a3b8',
      dark: '#475569',
    },
    media: {
      main: purple[600],
      light: purple[300],
      dark: purple[800],
    },
    error: {
      main: red[600],
    },
    warning: {
      main: orange[600],
    },
    success: {
      main: green[600],
    },
    background: {
      default: '#f8fafc',
      paper: '#ffffff',
    },
  },
  typography: {
    fontFamily: [
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Roboto',
      '"Helvetica Neue"',
      'Arial',
      'sans-serif',
    ].join(','),
    h1: {
      fontWeight: 600,
    },
    h2: {
      fontWeight: 600,
    },
    h3: {
      fontWeight: 600,
    },
    h4: {
      fontWeight: 600,
    },
    h5: {
      fontWeight: 600,
    },
    h6: {
      fontWeight: 600,
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
          borderRadius: 8,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
          borderRadius: 12,
        },
      },
    },
    MuiDataGrid: {
      styleOverrides: {
        root: {
          border: 'none',
          borderRadius: 8,
          '& .MuiDataGrid-cell': {
            borderBottom: '1px solid #e0e0e0',
          },
          '& .MuiDataGrid-columnHeader': {
            backgroundColor: '#f8fafc',
            fontWeight: 600,
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 6,
          fontWeight: 500,
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 8,
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06)',
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        },
      },
    },
  },
});

export default theme;