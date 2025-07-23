import React, { useState } from 'react';
import {
  Box,
  Container,
  Typography,
  Tabs,
  Tab,
  Paper,
  Alert,
  CircularProgress
} from '@mui/material';
import {
  Palette as ThemeIcon,
  Business as BrandingIcon,
  Language as DomainIcon,
  Email as EmailIcon,
  PhoneAndroid as MobileIcon,
  Analytics as AnalyticsIcon
} from '@mui/icons-material';
import { useWhiteLabel } from '../../hooks/useWhiteLabel';
import ThemeManager from './ThemeManager';
import BrandingManager from './BrandingManager';
import DomainManager from './DomainManager';
import EmailTemplateManager from './EmailTemplateManager';
import MobileAppManager from './MobileAppManager';
import WhiteLabelAnalytics from './WhiteLabelAnalytics';

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
      id={`whitelabel-tabpanel-${index}`}
      aria-labelledby={`whitelabel-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

const WhiteLabelPortal: React.FC = () => {
  const [currentTab, setCurrentTab] = useState(0);
  const {
    branding,
    themes,
    isLoading,
    error,
    refetchBranding,
    refetchThemes
  } = useWhiteLabel();

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          Failed to load white-label configuration: {error.message}
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          White-Label Configuration
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Customize the appearance and branding of your MAMS platform
        </Typography>
      </Box>

      {isLoading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      )}

      <Paper sx={{ width: '100%' }}>
        <Tabs
          value={currentTab}
          onChange={handleTabChange}
          variant="scrollable"
          scrollButtons="auto"
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab
            icon={<ThemeIcon />}
            label="Themes"
            id="whitelabel-tab-0"
            aria-controls="whitelabel-tabpanel-0"
          />
          <Tab
            icon={<BrandingIcon />}
            label="Branding"
            id="whitelabel-tab-1"
            aria-controls="whitelabel-tabpanel-1"
          />
          <Tab
            icon={<DomainIcon />}
            label="Custom Domains"
            id="whitelabel-tab-2"
            aria-controls="whitelabel-tabpanel-2"
          />
          <Tab
            icon={<EmailIcon />}
            label="Email Templates"
            id="whitelabel-tab-3"
            aria-controls="whitelabel-tabpanel-3"
          />
          <Tab
            icon={<MobileIcon />}
            label="Mobile Apps"
            id="whitelabel-tab-4"
            aria-controls="whitelabel-tabpanel-4"
          />
          <Tab
            icon={<AnalyticsIcon />}
            label="Analytics"
            id="whitelabel-tab-5"
            aria-controls="whitelabel-tabpanel-5"
          />
        </Tabs>

        <TabPanel value={currentTab} index={0}>
          <ThemeManager 
            themes={themes}
            onThemeChange={refetchThemes}
          />
        </TabPanel>

        <TabPanel value={currentTab} index={1}>
          <BrandingManager 
            branding={branding}
            themes={themes}
            onBrandingChange={refetchBranding}
          />
        </TabPanel>

        <TabPanel value={currentTab} index={2}>
          <DomainManager />
        </TabPanel>

        <TabPanel value={currentTab} index={3}>
          <EmailTemplateManager />
        </TabPanel>

        <TabPanel value={currentTab} index={4}>
          <MobileAppManager />
        </TabPanel>

        <TabPanel value={currentTab} index={5}>
          <WhiteLabelAnalytics />
        </TabPanel>
      </Paper>
    </Container>
  );
};

export default WhiteLabelPortal;