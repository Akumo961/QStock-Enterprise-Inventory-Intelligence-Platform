/**
 * App.tsx
 * Wraps the entire app in <LanguageProvider> so every component
 * can call useLanguage() / t() for French ↔ English switching.
 */

import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { AuthProvider } from './hooks/useAuth';
import { SnackbarProvider } from 'notistack';
import { LanguageProvider } from './context/LanguageContext';

import MainLayout from './components/layout/MainLayout';
import AdminLayout from './components/layout/AdminLayout';
import Login from './components/auth/Login';
import Register from './pages/Register';
import Home from './pages/Home';
import Scanner from './pages/Scanner';
import Inventory from './pages/Inventory';
import ProfilePage from './pages/ProfilePage';
import UserOrders from './pages/UserOrders';
import AdminDashboard from './components/dashboard/Dashboard';
import UserManagement from './components/admin/UserManagement';
import ItemManagement from './components/admin/ItemManagement';
import Reports from './components/admin/Reports';
import OrdersManagement from './components/admin/OrdersManagement';
import TransactionsManagement from './components/admin/TransactionsManagement';
import AIAssistant from './pages/AIAssistant';
import ProtectedRoute from './components/common/ProtectedRoute';
import AdminRoute from './components/common/AdminRoute';

const NotFound = () => {
  const navigate = useNavigate();
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', height: '100vh', textAlign: 'center', padding: 20,
    }}>
      <h1 style={{ fontSize: '6rem', fontWeight: 700, color: '#2d6a4f', margin: 0 }}>404</h1>
      <h2 style={{ color: '#333', marginBottom: 16 }}>Page Not Found</h2>
      <button onClick={() => navigate('/')} style={{
        padding: '10px 24px', backgroundColor: '#2d6a4f', color: 'white',
        border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 16,
      }}>Go Home</button>
    </div>
  );
};

// Scout-themed green palette
const theme = createTheme({
  palette: {
    primary: { main: '#2d6a4f', light: '#52b788', dark: '#1b4332' },
    secondary: { main: '#dc2f02', light: '#f48c06', dark: '#9d0208' },
    success: { main: '#52b788' },
    error: { main: '#dc2f02' },
    warning: { main: '#f48c06' },
    info: { main: '#1565c0' },
    background: { default: '#f4f7f6', paper: '#ffffff' },
  },
  typography: {
    fontFamily: ['-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'Arial', 'sans-serif'].join(','),
  },
  shape: { borderRadius: 10 },
  components: {
    MuiButton: { styleOverrides: { root: { textTransform: 'none', fontWeight: 600 } } },
    MuiCard: { styleOverrides: { root: { boxShadow: '0 2px 12px rgba(0,0,0,0.08)' } } },
    MuiAppBar: { styleOverrides: { root: { backgroundColor: '#1b4332' } } },
  },
});

function App() {
  return (
    <LanguageProvider>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <SnackbarProvider maxSnack={3} anchorOrigin={{ vertical: 'top', horizontal: 'right' }} autoHideDuration={5000}>
          <Router>
            <AuthProvider>
              <Routes>
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />

                {/* Protected user routes */}
                <Route path="/" element={<ProtectedRoute><MainLayout /></ProtectedRoute>}>
                  <Route index element={<Home />} />
                  <Route path="scanner" element={<Scanner />} />
                  <Route path="inventory" element={<Inventory />} />
                  <Route path="profile" element={<ProfilePage />} />
                  <Route path="orders" element={<UserOrders />} />
                  <Route path="ai-assistant" element={<AIAssistant />} />
                </Route>

                {/* Admin routes */}
                <Route path="/admin" element={<AdminRoute><AdminLayout /></AdminRoute>}>
                  <Route index element={<Navigate to="/admin/dashboard" replace />} />
                  <Route path="dashboard" element={<AdminDashboard />} />
                  <Route path="users" element={<UserManagement />} />
                  <Route path="items" element={<ItemManagement />} />
                  <Route path="orders" element={<OrdersManagement />} />
                  <Route path="transactions" element={<TransactionsManagement />} />
                  <Route path="reports" element={<Reports />} />
                  <Route path="ai-assistant" element={<AIAssistant />} />
                </Route>

                <Route path="*" element={<NotFound />} />
              </Routes>
            </AuthProvider>
          </Router>
        </SnackbarProvider>
      </ThemeProvider>
    </LanguageProvider>
  );
}

export default App;