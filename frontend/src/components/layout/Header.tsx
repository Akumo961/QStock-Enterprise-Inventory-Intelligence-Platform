import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import {
  AppBar, Toolbar, Typography, IconButton, Button, Menu, MenuItem,
  Avatar, Box, Badge, Drawer, List, ListItem, ListItemIcon, ListItemText,
  Divider, useTheme, useMediaQuery, Tooltip, Chip,
} from '@mui/material';
import {
  Menu as MenuIcon, AccountCircle, Notifications, Inventory,
  Dashboard, Logout, Home, QrCodeScanner, Assignment, Translate, SmartToy,
} from '@mui/icons-material';
import { useAuth } from '../../hooks/useAuth';
import { useLanguage } from '../../context/LanguageContext';
import { dashboardAPI } from '../../services/api';

interface HeaderProps {
  user?: {
    id: number;
    email: string;
    full_name: string;
    is_admin: boolean;
    qr_code_image?: string;
  } | null;
  onLogout?: () => void;
}

interface Notification {
  id: number;
  message: string;
  read: boolean;
}

const Header: React.FC<HeaderProps> = ({ user, onLogout }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const { t, language, setLanguage } = useLanguage();

  const [anchorElUser, setAnchorElUser] = useState<null | HTMLElement>(null);
  const [anchorElNotif, setAnchorElNotif] = useState<null | HTMLElement>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);

  useEffect(() => {
    if (!user) {
      setNotifications([]);
      return;
    }
    const fetchNotifications = async () => {
      try {
        const stats = await dashboardAPI.getStats();
        const notifs: Notification[] = [];
        if (stats.overdue_borrows > 0) {
          notifs.push({
            id: 1,
            message: language === 'fr'
              ? `${stats.overdue_borrows} article(s) en retard`
              : `${stats.overdue_borrows} overdue item(s)`,
            read: false,
          });
        }
        if (stats.pending_requests > 0 && user.is_admin) {
          notifs.push({
            id: 2,
            message: language === 'fr'
              ? `${stats.pending_requests} commande(s) en attente`
              : `${stats.pending_requests} pending order(s)`,
            read: false,
          });
        }
        setNotifications(notifs);
      } catch {
        setNotifications([]);
      }
    };
    fetchNotifications();
  }, [user, language]);

  const unreadCount = notifications.filter(n => !n.read).length;

  const handleMarkAllRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
  };

  const handleLogout = () => {
    setAnchorElUser(null);
    if (onLogout) onLogout();
  };

  const isActive = (path: string) => location.pathname === path;

  const navItems = [
    { label: t('home'),        path: '/',               icon: <Home /> },
    { label: t('scanner'),     path: '/scanner',        icon: <QrCodeScanner /> },
    { label: t('inventory'),   path: '/inventory',      icon: <Inventory /> },
    { label: t('myRequests'),  path: '/orders',         icon: <Assignment /> },
    { label: language === 'fr' ? 'Assistant IA' : 'AI Assistant', path: '/ai-assistant', icon: <SmartToy /> },
  ];

  const adminItems = [
    { label: t('dashboard'),       path: '/admin/dashboard',      icon: <Dashboard /> },
    { label: t('itemManagement'),  path: '/admin/items',          icon: <Inventory /> },
    { label: t('userManagement'),  path: '/admin/users',          icon: <AccountCircle /> },
    { label: language === 'fr' ? 'Commandes' : 'Orders',          path: '/admin/orders',        icon: <Assignment /> },
    { label: language === 'fr' ? 'Transactions' : 'Transactions', path: '/admin/transactions',  icon: <Assignment /> },
    { label: language === 'fr' ? 'Assistant IA' : 'AI Assistant', path: '/admin/ai-assistant',  icon: <SmartToy /> },
  ];

  return (
    <>
      <AppBar position="sticky" elevation={3} sx={{ backgroundColor: '#1b4332' }}>
        <Toolbar sx={{ minHeight: { xs: 64, md: 72 } }}>
          {isMobile && user && (
            <IconButton color="inherit" onClick={() => setMobileMenuOpen(true)} sx={{ mr: 1 }}>
              <MenuIcon />
            </IconButton>
          )}

          {/* Logo + Brand */}
          <Box onClick={() => navigate('/')} sx={{ display: 'flex', alignItems: 'center', cursor: 'pointer', flexGrow: { xs: 1, md: 0 }, gap: 1.5 }}>
            <Box component="img" src="/logo.jpg" alt="Scouts Logo"
              sx={{ height: { xs: 44, md: 54 }, width: { xs: 44, md: 54 }, objectFit: 'contain', borderRadius: '50%', bgcolor: 'white', p: 0.5 }} />
            <Box sx={{ display: { xs: 'none', sm: 'block' } }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 800, lineHeight: 1.1, color: 'white', fontSize: { sm: '0.9rem', md: '1rem' } }}>
                {t('orgName')}
              </Typography>
              <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.7rem' }}>
                {t('tagline')}
              </Typography>
            </Box>
          </Box>

          {/* Desktop nav */}
          {!isMobile && user && (
            <Box sx={{ flexGrow: 1, display: 'flex', ml: 3 }}>
              {navItems.map((item) => (
                <Button key={item.path} color="inherit" startIcon={item.icon} onClick={() => navigate(item.path)}
                  sx={{
                    mx: 0.5, fontWeight: isActive(item.path) ? 700 : 400, fontSize: '0.82rem',
                    borderBottom: isActive(item.path) ? '2px solid #52b788' : '2px solid transparent',
                    borderRadius: 0, '&:hover': { backgroundColor: 'rgba(255,255,255,0.1)' },
                  }}>
                  {item.label}
                </Button>
              ))}
              {user?.is_admin && (
                <Button color="inherit" startIcon={<Dashboard />} onClick={() => navigate('/admin/dashboard')}
                  sx={{
                    mx: 0.5, fontWeight: 700, fontSize: '0.82rem', color: '#f48c06',
                    borderBottom: location.pathname.startsWith('/admin') ? '2px solid #f48c06' : '2px solid transparent',
                    borderRadius: 0, '&:hover': { backgroundColor: 'rgba(255,255,255,0.1)' },
                  }}>
                  Admin
                </Button>
              )}
            </Box>
          )}

          {!user && <Box sx={{ flexGrow: 1 }} />}

          {/* Right side */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Tooltip title={t('language')}>
              <Button color="inherit" startIcon={<Translate />}
                onClick={() => setLanguage(language === 'fr' ? 'en' : 'fr')}
                sx={{ fontSize: '0.75rem', minWidth: 'auto', px: 1.5, border: '1px solid rgba(255,255,255,0.3)', borderRadius: 2 }}>
                {language === 'fr' ? 'EN' : 'FR'}
              </Button>
            </Tooltip>

            {user ? (
              <>
                <Tooltip title={t('notifications')}>
                  <IconButton color="inherit" onClick={(e) => setAnchorElNotif(e.currentTarget)}>
                    <Badge badgeContent={unreadCount > 0 ? unreadCount : null} color="error">
                      <Notifications />
                    </Badge>
                  </IconButton>
                </Tooltip>

                <Tooltip title={user.full_name}>
                  <IconButton onClick={(e) => setAnchorElUser(e.currentTarget)} sx={{ p: 0.5 }}>
                    <Avatar sx={{ width: 38, height: 38, bgcolor: '#52b788', fontWeight: 700, fontSize: '1rem' }}>
                      {user.full_name.charAt(0).toUpperCase()}
                    </Avatar>
                  </IconButton>
                </Tooltip>
              </>
            ) : (
              <Button color="inherit" variant="outlined" onClick={() => navigate('/login')}
                sx={{ borderColor: 'rgba(255,255,255,0.5)', fontSize: '0.82rem' }}>
                {t('login')}
              </Button>
            )}
          </Box>
        </Toolbar>
      </AppBar>

      {/* User dropdown */}
      <Menu anchorEl={anchorElUser} open={Boolean(anchorElUser)} onClose={() => setAnchorElUser(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
        PaperProps={{ elevation: 4, sx: { minWidth: 220, mt: 0.5 } }}>
        {user && (
          <>
            <Box sx={{ px: 2, py: 1.5, borderBottom: 1, borderColor: 'divider' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                <Box component="img" src="/logo.jpg" alt="" sx={{ height: 32, width: 32, objectFit: 'contain', borderRadius: '50%' }} />
                <Box>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>{user.full_name}</Typography>
                  <Typography variant="caption" color="text.secondary">{user.email}</Typography>
                </Box>
              </Box>
              {user.is_admin && <Chip label={t('administrator')} size="small" color="warning" sx={{ mt: 1, fontSize: '0.68rem' }} />}
            </Box>

            <MenuItem onClick={() => { setAnchorElUser(null); navigate('/profile'); }}>
              <ListItemIcon><AccountCircle fontSize="small" /></ListItemIcon>
              <ListItemText>{t('profile')}</ListItemText>
            </MenuItem>
            <MenuItem onClick={() => { setAnchorElUser(null); navigate('/orders'); }}>
              <ListItemIcon><Assignment fontSize="small" /></ListItemIcon>
              <ListItemText>{t('myRequests')}</ListItemText>
            </MenuItem>
            {user.is_admin && adminItems.map(item => (
              <MenuItem key={item.path} onClick={() => { setAnchorElUser(null); navigate(item.path); }}>
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText>{item.label}</ListItemText>
              </MenuItem>
            ))}
            <Divider />
            <MenuItem onClick={handleLogout} sx={{ color: 'error.main' }}>
              <ListItemIcon><Logout fontSize="small" color="error" /></ListItemIcon>
              <ListItemText>{t('logout')}</ListItemText>
            </MenuItem>
          </>
        )}
      </Menu>

      {/* Notifications dropdown */}
      <Menu anchorEl={anchorElNotif} open={Boolean(anchorElNotif)} onClose={() => setAnchorElNotif(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
        PaperProps={{ elevation: 4, sx: { minWidth: 300 } }}>
        <Box sx={{ px: 2, py: 1.5, borderBottom: 1, borderColor: 'divider', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="subtitle2" fontWeight={700}>{t('notifications')}</Typography>
          {unreadCount > 0 && (
            <Button size="small" onClick={handleMarkAllRead} sx={{ fontSize: '0.72rem' }}>
              {language === 'fr' ? 'Tout marquer lu' : 'Mark all read'}
            </Button>
          )}
        </Box>
        {notifications.length > 0 ? notifications.map(n => (
          <MenuItem key={n.id} sx={{ whiteSpace: 'normal', py: 1.5, bgcolor: n.read ? 'transparent' : 'action.hover' }}>
            <ListItemText primary={n.message} primaryTypographyProps={{ variant: 'body2', fontWeight: n.read ? 400 : 600 }} />
          </MenuItem>
        )) : (
          <MenuItem disabled>
            <ListItemText primary={t('noNotifications')} primaryTypographyProps={{ variant: 'body2', sx: { color: 'text.secondary', textAlign: 'center' } }} />
          </MenuItem>
        )}
        <Divider />
        <MenuItem sx={{ justifyContent: 'center' }} onClick={() => setAnchorElNotif(null)}>
          <Typography variant="caption" color="primary">{t('close')}</Typography>
        </MenuItem>
      </Menu>

      {/* Mobile drawer */}
      <Drawer anchor="left" open={mobileMenuOpen} onClose={() => setMobileMenuOpen(false)} PaperProps={{ sx: { width: 280 } }}>
        <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider', bgcolor: '#1b4332', color: 'white', display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box component="img" src="/logo.jpg" alt="Logo" sx={{ height: 48, width: 48, objectFit: 'contain', bgcolor: 'white', borderRadius: '50%', p: 0.5 }} />
          <Box>
            <Typography variant="body2" sx={{ fontWeight: 700 }}>{t('orgName')}</Typography>
            {user && <Typography variant="caption" sx={{ opacity: 0.8 }}>{user.full_name}</Typography>}
          </Box>
        </Box>
        <List>
          {navItems.map(item => (
            <ListItem button key={item.path} selected={isActive(item.path)}
              onClick={() => { navigate(item.path); setMobileMenuOpen(false); }}>
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItem>
          ))}
          {user?.is_admin && (
            <ListItem button onClick={() => { navigate('/admin/dashboard'); setMobileMenuOpen(false); }}>
              <ListItemIcon><Dashboard /></ListItemIcon>
              <ListItemText primary="Admin" />
            </ListItem>
          )}
          <Divider sx={{ my: 1 }} />
          <ListItem button onClick={() => setLanguage(language === 'fr' ? 'en' : 'fr')}>
            <ListItemIcon><Translate /></ListItemIcon>
            <ListItemText primary={language === 'fr' ? 'English' : 'Français'} />
          </ListItem>
          <Divider sx={{ my: 1 }} />
          <ListItem button onClick={() => { handleLogout(); setMobileMenuOpen(false); }} sx={{ color: 'error.main' }}>
            <ListItemIcon><Logout color="error" /></ListItemIcon>
            <ListItemText primary={t('logout')} />
          </ListItem>
        </List>
      </Drawer>
    </>
  );
};

export default Header;