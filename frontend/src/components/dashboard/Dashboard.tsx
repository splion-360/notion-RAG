import { useState, useEffect } from 'react';
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
} from '@mui/material';
import {
  LogoutOutlined as LogoutIcon,
  IntegrationInstructions as IntegrationsIcon,
  Person as PersonIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuth } from '../../contexts/AuthContext';
import { createClient } from '../../lib/supabase';

const DRAWER_WIDTH = 240;

interface UserProfile {
  id: string;
  email: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export default function Dashboard() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const [selectedTab, setSelectedTab] = useState('integrations');
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const supabase = createClient();

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
    toast.success('Connect Notion - Coming soon!');
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            Notion RAG
          </Typography>
          <Typography variant="body2" sx={{ mr: 2 }}>
            {user?.user_metadata?.name || user?.email}
          </Typography>
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
                >
                  Connect Notion
                </Button>
              </CardActions>
            </Card>
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
  );
}
