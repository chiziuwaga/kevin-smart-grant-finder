import {
    AssignmentOutlined as AssignmentIcon,
    BarChart as BarChartIcon,
    Bookmarks as BookmarksIcon,
    ChevronLeft as ChevronLeftIcon,
    Dashboard as DashboardIcon,
    Menu as MenuIcon,
    Search as SearchIcon,
    Settings as SettingsIcon
} from '@mui/icons-material';
import {
    AppBar,
    Box,
    Button,
    Divider,
    Drawer,
    IconButton,
    List,
    ListItem,
    ListItemButton,
    ListItemIcon,
    ListItemText,
    Toolbar,
    Typography,
    useMediaQuery,
    useTheme
} from '@mui/material';
import React, { useEffect, useState } from 'react';
import { Outlet, Link as RouterLink, useLocation } from 'react-router-dom';
import RunHistoryModal from './RunHistoryModal';

const drawerWidth = 240;

const AppLayout = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [open, setOpen] = useState(!isMobile);
  const location = useLocation();
  const [historyOpen, setHistoryOpen] = useState(false);

  const handleDrawerToggle = () => {
    setOpen(!open);
  };

  useEffect(() => {
    const fetchLastRun = async () => {
      try {
        const { getLastRun } = await import('api/apiClient');
        const data = await getLastRun();
        if(data.status!=='none'){
          document.getElementById('last-run-time').innerText = new Date(data.end || data.start).toLocaleString();
        }
      } catch(e) {
        console.error(e);
      }
    };
    fetchLastRun();
    const interval = setInterval(fetchLastRun, 60000);
    return () => clearInterval(interval);
  },[]);

  const menuItems = [
    { text: 'Dashboard', icon: <DashboardIcon />, path: '/' },
    { text: 'All Grants', icon: <AssignmentIcon />, path: '/grants' },
    { text: 'Search', icon: <SearchIcon />, path: '/search' },
    { text: 'Saved Grants', icon: <BookmarksIcon />, path: '/saved' },
    { text: 'Analytics', icon: <BarChartIcon />, path: '/analytics' },
    { text: 'Settings', icon: <SettingsIcon />, path: '/settings' }
  ];

  return (
    <Box sx={{ display: 'flex', height: '100vh' }}>
      <AppBar
        position="fixed"
        sx={{
          width: { sm: open ? `calc(100% - ${drawerWidth}px)` : '100%' },
          ml: { sm: open ? `${drawerWidth}px` : 0 },
          zIndex: (theme) => theme.zIndex.drawer + 1,
          transition: theme.transitions.create(['width', 'margin'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen,
          }),
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2 }}
          >
            {open ? <ChevronLeftIcon /> : <MenuIcon />}
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            Smart Grant Finder
          </Typography>
        </Toolbar>
      </AppBar>
      <Drawer
        variant={isMobile ? "temporary" : "persistent"}
        open={isMobile ? false : open}
        onClose={isMobile ? handleDrawerToggle : undefined}
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          [`& .MuiDrawer-paper`]: {
            width: drawerWidth,
            boxSizing: 'border-box',
            backgroundColor: theme.palette.background.default,
            borderRight: `1px solid ${theme.palette.divider}`,
          },
        }}
      >
        <Toolbar />
        <Box sx={{ overflow: 'auto', mt: 2 }}>
          <List>
            {menuItems.map((item) => (
              <ListItem key={item.text} disablePadding>
                <ListItemButton
                  component={RouterLink}
                  to={item.path}
                  selected={location.pathname === item.path}
                  sx={{
                    borderRadius: '0 24px 24px 0',
                    mr: 1,
                    '&.Mui-selected': {
                      backgroundColor: theme.palette.primary.light,
                      color: theme.palette.primary.contrastText,
                      '& .MuiListItemIcon-root': {
                        color: theme.palette.primary.contrastText,
                      },
                    },
                    '&:hover': {
                      backgroundColor: theme.palette.primary.light + '40', // 25% opacity
                      color: theme.palette.primary.main,
                      '& .MuiListItemIcon-root': {
                        color: theme.palette.primary.main,
                      },
                    },
                  }}
                >
                  <ListItemIcon
                    sx={{
                      color: location.pathname === item.path
                        ? theme.palette.primary.contrastText
                        : theme.palette.text.secondary,
                    }}
                  >
                    {item.icon}
                  </ListItemIcon>
                  <ListItemText primary={item.text} />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
          <Divider sx={{ my: 2 }} />
          <Box sx={{ p: 2 }}>
            <Typography variant="body2" color="textSecondary">
              System Status: All Good
            </Typography>
            <Box sx={{display:'flex',alignItems:'center',columnGap:1}}>
              <Typography variant="caption" color="textSecondary">
                Last run: <span id="last-run-time">—</span>
              </Typography>
              <Button size="small" variant="text" onClick={()=>setHistoryOpen(true)}>History</Button>
            </Box>
            <Typography variant="caption" color="textSecondary">
              Version 1.0.0
            </Typography>
          </Box>
        </Box>
      </Drawer>
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 0,
          width: { sm: open ? `calc(100% - ${drawerWidth}px)` : '100%' },
          transition: theme.transitions.create('margin', {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen,
          }),
          ml: open ? 0 : `-${drawerWidth}px`,
          height: '100vh',
          overflow: 'auto',
        }}
      >
        <Toolbar /> {/* Spacer for fixed app bar */}
        <Box sx={{ p: 0 }}>
          <Outlet />
        </Box>
      </Box>
      <RunHistoryModal open={historyOpen} onClose={()=>setHistoryOpen(false)} />
    </Box>
  );
};

export default AppLayout;