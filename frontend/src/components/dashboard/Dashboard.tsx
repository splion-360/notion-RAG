import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Box,
  AppBar,
  Toolbar,
  Typography,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Card,
  CardContent,
  CardActions,
  Button,
  IconButton,
  Divider,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Avatar,
} from '@mui/material';
import {
  LogoutOutlined as LogoutIcon,
  IntegrationInstructions as IntegrationsIcon,
  Person as PersonIcon,
  LightMode as LightModeIcon,
  DarkMode as DarkModeIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { FrontendClientProvider, useFrontendClient } from '@pipedream/connect-react';
import { createFrontendClient } from '@pipedream/sdk/browser';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import { createClient } from '../../lib/supabase';

const DRAWER_WIDTH = 240;
const backendUrl = import.meta.env.VITE_BACKEND_URL;

interface ConnectPortalCloseStatus {
  successful: boolean;
  completed: boolean;
}

interface PipedreamConnectPortalProps {
  app: string;
  open: boolean;
  onClose: (status: ConnectPortalCloseStatus) => void;
  onSuccess?: (payload: { id?: string }) => void;
  onError?: (error: unknown) => void;
}

interface UserProfile {
  id: string;
  email: string;
  name: string;
  created_at: string;
  updated_at: string;
  account_id?: string | null;
  app_id?: string | null;
}

interface UserIntegration {
  appName: string;
  logo: string;
  createdAt: string;
  accountId: string;
}

export default function Dashboard() {
  const { user, signOut } = useAuth();
  const { mode, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [selectedTab, setSelectedTab] = useState('integrations');
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [isConnectPortalOpen, setIsConnectPortalOpen] = useState(false);
  const [userIntegrations, setUserIntegrations] = useState<UserIntegration[]>([]);
  const [isSavingIntegration, setIsSavingIntegration] = useState(false);
  const [syncingAccounts, setSyncingAccounts] = useState<Set<string>>(new Set());
  const supabase = createClient();
  const userId = user?.id;

  const pipedreamClient = useMemo(() => {
    if (!userId) {
      return null;
    }

    return createFrontendClient({
      environment: import.meta.env.VITE_PIPEDREAM_ENVIRONMENT || 'development',
      projectId: import.meta.env.VITE_PIPEDREAM_PROJECT_ID || '',
      externalUserId: userId,
      tokenCallback: async () => {
        const response = await fetch(`${backendUrl}/api/v1/auth/connect-token`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ external_user_id: userId }),
        });

        if (!response.ok) {
          throw new Error('Failed to fetch connect token');
        }

        const data = await response.json();
        if (!data?.token) {
          throw new Error('Connect token missing from backend response');
        }

        const expiresAtValue = data.expires_at;
        const connectLinkUrl = data.connect_link_url;

        return { token: data.token, expiresAt: expiresAtValue, connectLinkUrl };
      },
    });
  }, [userId]);

  const handlePortalClose = useCallback((_: ConnectPortalCloseStatus) => {
    setIsConnectPortalOpen(false);
  }, []);

  const getAppLogo = (appName: string): string => {
    const logos: Record<string, string> = {
      notion: 'https://upload.wikimedia.org/wikipedia/commons/e/e9/Notion-logo.svg',
    };
    return logos[appName.toLowerCase()] || '';
  };

  const fetchIntegrations = useCallback(async () => {
    if (!userId) return;

    try {
      const response = await fetch(
        `${backendUrl}/api/v1/auth/integrations?user_id=${userId}`
      );

      if (response.ok) {
        const integrations = await response.json();
        setUserIntegrations(
          integrations.map((int: any) => ({
            appName: int.app_name,
            logo: getAppLogo(int.app_name),
            createdAt: int.created_at,
            accountId: int.account_id,
          }))
        );
      }
    } catch (error) {
      console.error('Failed to fetch integrations:', error);
    }
  }, [userId]);

  const handleConnectSuccess = useCallback(async (payload: { id?: string }) => {
    if (!userId || !payload.id) {
      toast.error('Connection finished but account info is missing');
      setIsConnectPortalOpen(false);
      return;
    }

    setIsSavingIntegration(true);
    try {
      const response = await fetch(`${backendUrl}/api/v1/auth/integrations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          app_name: 'notion',
          account_id: payload.id,
        }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || 'Failed to store integration');
      }

      toast.success('Notion connected successfully!');
      await fetchIntegrations();
      setIsConnectPortalOpen(false);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to store integration');
      console.error(error);
      setIsConnectPortalOpen(false);
    } finally {
      setIsSavingIntegration(false);
    }
  }, [userId, fetchIntegrations]);

  const handleConnectError = useCallback((error: unknown) => {
    toast.error('Failed to connect Notion');
    console.error(error);
    setIsConnectPortalOpen(false);
  }, []);

  useEffect(() => {
    const fetchUserProfile = async () => {
      if (!user) return;

      const { data, error } = await supabase
        .from('users')
        .select('*')
        .eq('id', user.id)
        .single();

      if (error) {
        console.error('Error fetching user profile:', error);
      } else {
        setUserProfile(data);
      }
    };

    fetchUserProfile();
  }, [user]);

  useEffect(() => {
    fetchIntegrations();
  }, [fetchIntegrations]);

  const handleSignOut = async () => {
    try {
      await signOut();
      toast.success('Signed out successfully');
      navigate('/signin');
    } catch (error) {
      toast.error('Error signing out');
      console.error(error);
    }
  };

  const handleConnectNotion = () => {
    if (!userId || !pipedreamClient) {
      toast.error('User not authenticated');
      return;
    }

    setIsConnectPortalOpen(true);
  };

  const handleSync = useCallback(async (accountId: string) => {
    if (!userId) {
      toast.error('User not authenticated');
      return;
    }

    setSyncingAccounts(prev => new Set(prev).add(accountId));
    try {
      const response = await fetch(`${backendUrl}/api/v1/notion/sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          account_id: accountId,
          recency_months: 6,
        }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || 'Failed to sync Notion pages');
      }

      const result = await response.json();
      toast.success(result.message || 'Sync completed successfully');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to sync Notion pages');
      console.error(error);
    } finally {
      setSyncingAccounts(prev => {
        const next = new Set(prev);
        next.delete(accountId);
        return next;
      });
    }
  }, [userId]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const dashboardContent = (
    <>
      <Box sx={{ display: 'flex', minHeight: '100vh' }}>
        <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
          <Toolbar>
            <Typography variant="h6" sx={{ flexGrow: 1 }}>
              Notion RAG
            </Typography>
            <Typography variant="body2" sx={{ mr: 2 }}>
              {user?.user_metadata?.name || user?.email}
            </Typography>
            <IconButton onClick={toggleTheme} color="inherit" title="Toggle theme">
              {mode === 'light' ? <DarkModeIcon /> : <LightModeIcon />}
            </IconButton>
            <IconButton onClick={handleSignOut} color="inherit" title="Sign out">
              <LogoutIcon />
            </IconButton>
          </Toolbar>
        </AppBar>

        <Drawer
          variant="permanent"
          sx={{
            width: DRAWER_WIDTH,
            flexShrink: 0,
            '& .MuiDrawer-paper': {
              width: DRAWER_WIDTH,
              boxSizing: 'border-box',
            },
          }}
        >
          <Toolbar />
          <Box sx={{ overflow: 'auto' }}>
            <List>
              <ListItem disablePadding>
                <ListItemButton
                  selected={selectedTab === 'integrations'}
                  onClick={() => setSelectedTab('integrations')}
                >
                  <ListItemIcon>
                    <IntegrationsIcon />
                  </ListItemIcon>
                  <ListItemText primary="Integrations" />
                </ListItemButton>
              </ListItem>
              <ListItem disablePadding>
                <ListItemButton
                  selected={selectedTab === 'profile'}
                  onClick={() => setSelectedTab('profile')}
                >
                  <ListItemIcon>
                    <PersonIcon />
                  </ListItemIcon>
                  <ListItemText primary="Profile" />
                </ListItemButton>
              </ListItem>
            </List>
          </Box>
        </Drawer>

        <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
          <Toolbar />

          {selectedTab === 'integrations' && (
            <Box>
              <Typography variant="h5" sx={{ mb: 3 }}>
                Integrations
              </Typography>
              <Card sx={{ maxWidth: 350 }} variant="outlined">
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Notion
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Connect your Notion workspace to index and search your pages.
                  </Typography>
                </CardContent>
                <CardActions>
                  <Button
                    variant="contained"
                    color="primary"
                    fullWidth
                    onClick={handleConnectNotion}
                    disabled={isSavingIntegration}
                  >
                    Connect Notion
                  </Button>
                </CardActions>
              </Card>
              <Box mt={4}>
                <Typography variant="subtitle1" gutterBottom>
                  Connected Apps
                </Typography>
                {userIntegrations.length > 0 ? (
                  <TableContainer component={Paper} variant="outlined">
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Logo</TableCell>
                          <TableCell>App</TableCell>
                          <TableCell>Account ID</TableCell>
                          <TableCell>Connected</TableCell>
                          <TableCell>Actions</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {userIntegrations.map((integration) => (
                          <TableRow key={`${integration.appName}-${integration.createdAt}`}>
                            <TableCell>
                              <Avatar
                                src={integration.logo}
                                alt={`${integration.appName} logo`}
                                sx={{ width: 32, height: 32 }}
                              >
                                {integration.appName.charAt(0)}
                              </Avatar>
                            </TableCell>
                            <TableCell>{integration.appName}</TableCell>
                            <TableCell>{integration.accountId}</TableCell>
                            <TableCell>{formatDate(integration.createdAt)}</TableCell>
                            <TableCell>
                              <Button
                                variant="outlined"
                                size="small"
                                onClick={() => handleSync(integration.accountId)}
                                disabled={syncingAccounts.has(integration.accountId)}
                              >
                                {syncingAccounts.has(integration.accountId) ? 'Syncing...' : 'Sync'}
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No integrations connected yet.
                  </Typography>
                )}
              </Box>
            </Box>
          )}

          {selectedTab === 'profile' && (
            <Box>
              <Typography variant="h5" sx={{ mb: 3 }}>
                Profile
              </Typography>
              <Card sx={{ maxWidth: 500 }}>
                <CardContent>
                  <Stack spacing={2}>
                    <Box>
                      <Typography variant="subtitle2" color="text.secondary">
                        Name
                      </Typography>
                      <Typography variant="body1">
                        {userProfile?.name || user?.user_metadata?.name || 'N/A'}
                      </Typography>
                    </Box>
                    <Divider />
                    <Box>
                      <Typography variant="subtitle2" color="text.secondary">
                        Email
                      </Typography>
                      <Typography variant="body1">
                        {userProfile?.email || user?.email}
                      </Typography>
                    </Box>
                    <Divider />
                    <Box>
                      <Typography variant="subtitle2" color="text.secondary">
                        Joined
                      </Typography>
                      <Typography variant="body1">
                        {userProfile?.created_at ? formatDate(userProfile.created_at) : 'N/A'}
                      </Typography>
                    </Box>
                    <Divider />
                    <Box>
                      <Typography variant="subtitle2" color="text.secondary">
                        Last Updated
                      </Typography>
                      <Typography variant="body1">
                        {userProfile?.updated_at ? formatDate(userProfile.updated_at) : 'N/A'}
                      </Typography>
                    </Box>
                  </Stack>
                </CardContent>
              </Card>
            </Box>
          )}
        </Box>
      </Box>
      {pipedreamClient && (
        <PipedreamConnectPortal
          app="notion"
          open={isConnectPortalOpen}
          onClose={handlePortalClose}
          onSuccess={handleConnectSuccess}
          onError={handleConnectError}
        />
      )}
    </>
  );

  if (pipedreamClient) {
    return (
      <FrontendClientProvider client={pipedreamClient}>
        {dashboardContent}
      </FrontendClientProvider>
    );
  }

  return dashboardContent;
}

function PipedreamConnectPortal({ app, open, onClose, onSuccess, onError }: PipedreamConnectPortalProps) {
  const client = useFrontendClient();

  useEffect(() => {
    if (!open || !client) {
      return;
    }

    let cancelled = false;

    const launchPortal = async () => {
      try {
        await client.connectAccount({
          app,
          onSuccess: (result) => {
            if (cancelled) return;
            onSuccess?.(result);
          },
          onError: (error) => {
            if (cancelled) return;
            onError?.(error);
          },
          onClose: (status) => {
            if (cancelled) return;
            onClose(status);
          },
        });
      } catch (error) {
        if (cancelled) return;
        onError?.(error);
        onClose({ successful: false, completed: false });
      }
    };

    launchPortal();

    return () => {
      cancelled = true;
    };
  }, [app, client, onClose, onSuccess, onError, open]);

  return null;
}
