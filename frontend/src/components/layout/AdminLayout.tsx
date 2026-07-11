/**
 * AdminLayout.tsx
 * Uses <Outlet /> for React Router v6.
 * Scout-branded dark green sidebar with logo.
 * Admin nav labels translated via useLanguage().
 */

import { Outlet, Link, useLocation } from 'react-router-dom';
import { Box, Typography, List, ListItem, ListItemIcon, ListItemText } from '@mui/material';
import { Dashboard, People, Inventory, BarChart, ShoppingCart, SmartToy, SwapHoriz } from '@mui/icons-material';
import Header from './Header';
import { useAuth } from '../../hooks/useAuth';
import { useLanguage } from '../../context/LanguageContext';

const AdminLayout = () => {
  const { user, logout } = useAuth();
  const { t, language } = useLanguage();
  const location = useLocation();

  const navItems = [
    { label: t('dashboard'),                                         path: '/admin/dashboard',     icon: <Dashboard /> },
    { label: t('userManagement'),                                    path: '/admin/users',         icon: <People /> },
    { label: t('itemManagement'),                                    path: '/admin/items',         icon: <Inventory /> },
    { label: language === 'fr' ? 'Commandes'    : 'Orders',         path: '/admin/orders',        icon: <ShoppingCart /> },
    { label: language === 'fr' ? 'Transactions' : 'Transactions',   path: '/admin/transactions',  icon: <SwapHoriz /> },
    { label: t('reports'),                                           path: '/admin/reports',       icon: <BarChart /> },
    { label: language === 'fr' ? 'Assistant IA' : 'AI Assistant',   path: '/admin/ai-assistant',  icon: <SmartToy /> },
  ];

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Header user={user} onLogout={logout} />

      <Box sx={{ display: 'flex', flexGrow: 1 }}>
        {/* Sidebar */}
        <Box sx={{
          width: 240,
          flexShrink: 0,
          bgcolor: '#1b4332',
          color: 'white',
          minHeight: 'calc(100vh - 72px)',
          display: 'flex',
          flexDirection: 'column',
        }}>
          {/* Sidebar logo */}
          <Box sx={{ p: 2.5, borderBottom: '1px solid rgba(255,255,255,0.12)', display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Box
              component="img"
              src="/logo.jpg"
              alt="Logo"
              sx={{ height: 42, width: 42, objectFit: 'contain', bgcolor: 'white', borderRadius: '50%', p: 0.4 }}
            />
            <Box>
              <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', display: 'block', fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: 1 }}>
                {t('adminMenu')}
              </Typography>
              <Typography variant="body2" sx={{ fontWeight: 700, color: 'white', fontSize: '0.8rem' }}>
                {t('orgName').split(' ').slice(0, 2).join(' ')}
              </Typography>
            </Box>
          </Box>

          <List sx={{ py: 1, flexGrow: 1 }}>
            {navItems.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <ListItem
                  key={item.path}
                  component={Link}
                  to={item.path}
                  sx={{
                    py: 1.5,
                    px: 2.5,
                    color: 'white',
                    textDecoration: 'none',
                    bgcolor: isActive ? 'rgba(82,183,136,0.25)' : 'transparent',
                    borderLeft: isActive ? '4px solid #52b788' : '4px solid transparent',
                    '&:hover': { bgcolor: 'rgba(255,255,255,0.08)' },
                    transition: 'all 0.15s',
                  }}
                >
                  <ListItemIcon sx={{ color: isActive ? '#52b788' : 'rgba(255,255,255,0.6)', minWidth: 36 }}>
                    {item.icon}
                  </ListItemIcon>
                  <ListItemText
                    primary={item.label}
                    primaryTypographyProps={{ fontSize: '0.88rem', fontWeight: isActive ? 700 : 400 }}
                  />
                </ListItem>
              );
            })}
          </List>

          {/* Sidebar footer logo */}
          <Box sx={{ p: 2, borderTop: '1px solid rgba(255,255,255,0.12)', textAlign: 'center' }}>
            <Box component="img" src="/logo.jpg" alt="" sx={{ height: 36, width: 36, objectFit: 'contain', bgcolor: 'white', borderRadius: '50%', p: 0.3, opacity: 0.8 }} />
          </Box>
        </Box>

        {/* Main content */}
        <Box component="main" sx={{ flexGrow: 1, bgcolor: '#f4f7f6', overflow: 'auto' }}>
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
};

export default AdminLayout;