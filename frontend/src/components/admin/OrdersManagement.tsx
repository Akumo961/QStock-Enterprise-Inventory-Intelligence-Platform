/**
 * OrdersManagement.tsx — Admin Orders Dashboard
 * Status: pending | approved | rejected | ready  (4 only)
 * Admin can: view all, filter, mark ready, update status, add notes, delete
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Card, CardContent, Typography, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Paper, Chip,
  Dialog, DialogTitle, DialogContent, DialogActions, TextField,
  Alert, Tooltip, IconButton, FormControl, InputLabel, Select,
  MenuItem, Grid, Avatar, TablePagination, InputAdornment,
  Switch, FormControlLabel, CircularProgress, Button, Divider,
} from '@mui/material';
import {
  CheckCircle, Cancel, LocalShipping, HourglassEmpty,
  ThumbDown, Edit, Delete, Search, FilterList, ChatBubbleOutline,
} from '@mui/icons-material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { useLanguage } from '../../context/LanguageContext';

const API = '/api';
const authHeaders = () => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${localStorage.getItem('token')}`,
});

interface Order {
  id: number; user_id: number; user_name: string; user_email: string;
  user_employee_id?: string; order_type: string; title: string;
  description: string; item_id?: number; item_name?: string;
  needed_date?: string; ready_date?: string; status: string;
  admin_response?: string; admin_name?: string; created_at: string;
}

const STATUSES: Record<string, { color: any; icon: React.ReactNode; en: string; fr: string }> = {
  pending:  { color: 'warning', icon: <HourglassEmpty />, en: 'Pending',  fr: 'En attente' },
  approved: { color: 'info',    icon: <CheckCircle />,    en: 'Approved', fr: 'Approuvée'  },
  rejected: { color: 'error',   icon: <ThumbDown />,      en: 'Rejected', fr: 'Rejetée'    },
  ready:    { color: 'success', icon: <LocalShipping />,  en: 'Ready',    fr: 'Prête'      },
};

const ORDER_TYPES = [
  { value: 'new_item',       en: 'New Item Request',  fr: 'Demande de nouvel article' },
  { value: 'special_borrow', en: 'Special Borrowing', fr: 'Emprunt Spécial'           },
  { value: 'other',          en: 'Other Request',      fr: 'Autre demande'             },
];

const OrdersManagement: React.FC = () => {
  const { language } = useLanguage();
  const fr = language === 'fr';

  const [orders, setOrders]         = useState<Order[]>([]);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState('');
  const [success, setSuccess]       = useState('');
  const [search, setSearch]         = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterType, setFilterType]     = useState('');
  const [page, setPage]             = useState(0);
  const [total, setTotal]           = useState(0);
  const rowsPerPage                 = 15;

  // Edit dialog
  const [editOrder, setEditOrder]   = useState<Order | null>(null);
  const [editStatus, setEditStatus] = useState('');
  const [editResponse, setEditResponse] = useState('');
  const [editReadyDate, setEditReadyDate] = useState<Date | null>(null);
  const [saving, setSaving]         = useState(false);

  const fetchOrders = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const params = new URLSearchParams({
        page: (page + 1).toString(),
        page_size: rowsPerPage.toString(),
        ...(filterStatus && { status: filterStatus }),
        ...(filterType   && { order_type: filterType }),
        ...(search       && { search }),
      });
      const res = await fetch(`${API}/orders?${params}`, { headers: authHeaders() });
      if (!res.ok) throw new Error(fr ? 'Échec du chargement' : 'Failed to load');
      const data = await res.json();
      setOrders(data.orders || []);
      setTotal(data.total || 0);
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }, [page, filterStatus, filterType, search, fr]);

  useEffect(() => { fetchOrders(); }, [fetchOrders]);

  const openEdit = (order: Order) => {
    setEditOrder(order);
    setEditStatus(order.status);
    setEditResponse(order.admin_response || '');
    setEditReadyDate(order.ready_date ? new Date(order.ready_date) : null);
    setError('');
  };

  const handleSave = async () => {
    if (!editOrder) return;
    setSaving(true); setError('');
    try {
      const res = await fetch(`${API}/orders/${editOrder.id}`, {
        method: 'PUT', headers: authHeaders(),
        body: JSON.stringify({
          status: editStatus,
          admin_response: editResponse || null,
          ready_date: editReadyDate?.toISOString() || null,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(typeof err.detail === 'string' ? err.detail : (fr ? 'Échec' : 'Failed'));
      }
      setSuccess(fr ? 'Commande mise à jour !' : 'Order updated!');
      setEditOrder(null);
      fetchOrders();
    } catch (e: any) { setError(e.message); }
    finally { setSaving(false); }
  };

  const handleMarkReady = async (order: Order) => {
    setSaving(true);
    try {
      const res = await fetch(`${API}/orders/${order.id}`, {
        method: 'PUT', headers: authHeaders(),
        body: JSON.stringify({
          status: 'ready',
          admin_response: fr
            ? `Votre commande "${order.title}" est prête à être récupérée.`
            : `Your order "${order.title}" is ready for pickup.`,
        }),
      });
      if (!res.ok) throw new Error('Failed');
      setSuccess(fr ? `"${order.title}" marquée comme prête !` : `"${order.title}" marked ready!`);
      fetchOrders();
    } catch { setError(fr ? 'Échec' : 'Failed'); }
    finally { setSaving(false); }
  };

  const handleDelete = async (order: Order) => {
    if (!window.confirm(fr
      ? `Supprimer la commande #${order.id} de ${order.user_name} ?`
      : `Delete order #${order.id} from ${order.user_name}?`)) return;
    try {
      const res = await fetch(`${API}/orders/${order.id}`, { method: 'DELETE', headers: authHeaders() });
      if (!res.ok) throw new Error('Failed');
      setSuccess(fr ? 'Supprimée.' : 'Deleted.');
      fetchOrders();
    } catch { setError(fr ? 'Échec' : 'Failed'); }
  };

  const statusChip = (s: string) => {
    const cfg = STATUSES[s] || STATUSES.pending;
    return <Chip icon={cfg.icon as any} label={fr ? cfg.fr : cfg.en} color={cfg.color} size="small" />;
  };
  const typeLabel = (v: string) => { const t = ORDER_TYPES.find(x => x.value === v); return t ? (fr ? t.fr : t.en) : v; };
  const fmt = (d?: string) => d ? new Date(d).toLocaleDateString(fr ? 'fr-CA' : 'en-CA', { year: 'numeric', month: 'short', day: 'numeric' }) : '—';

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Box sx={{ p: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, color: '#1b4332', mb: 3 }}>
          {fr ? 'Gestion des commandes' : 'Orders Management'}
        </Typography>

        {error   && <Alert severity="error"   onClose={() => setError('')}   sx={{ mb: 2 }}>{error}</Alert>}
        {success && <Alert severity="success" onClose={() => setSuccess('')} sx={{ mb: 2 }}>{success}</Alert>}

        {/* Filters */}
        <Card sx={{ mb: 2, borderRadius: 2 }}>
          <CardContent>
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
              <FilterList sx={{ color: '#2d6a4f' }} />
              <TextField placeholder={fr ? 'Rechercher...' : 'Search...'} value={search}
                onChange={e => { setSearch(e.target.value); setPage(0); }} size="small"
                sx={{ flexGrow: 1, minWidth: 200 }}
                InputProps={{ startAdornment: <InputAdornment position="start"><Search /></InputAdornment> }} />
              <FormControl size="small" sx={{ minWidth: 150 }}>
                <InputLabel>{fr ? 'Statut' : 'Status'}</InputLabel>
                <Select value={filterStatus} label={fr ? 'Statut' : 'Status'}
                  onChange={e => { setFilterStatus(e.target.value); setPage(0); }}>
                  <MenuItem value="">{fr ? 'Tous' : 'All'}</MenuItem>
                  {Object.entries(STATUSES).map(([k, v]) => (
                    <MenuItem key={k} value={k}>{fr ? v.fr : v.en}</MenuItem>
                  ))}
                </Select>
              </FormControl>
              <FormControl size="small" sx={{ minWidth: 180 }}>
                <InputLabel>{fr ? 'Type' : 'Type'}</InputLabel>
                <Select value={filterType} label={fr ? 'Type' : 'Type'}
                  onChange={e => { setFilterType(e.target.value); setPage(0); }}>
                  <MenuItem value="">{fr ? 'Tous' : 'All'}</MenuItem>
                  {ORDER_TYPES.map(t => <MenuItem key={t.value} value={t.value}>{fr ? t.fr : t.en}</MenuItem>)}
                </Select>
              </FormControl>
              <Button variant="outlined" size="small"
                onClick={() => { setSearch(''); setFilterStatus(''); setFilterType(''); setPage(0); }}>
                {fr ? 'Réinitialiser' : 'Reset'}
              </Button>
            </Box>
          </CardContent>
        </Card>

        {/* Table */}
        <Card elevation={2} sx={{ borderRadius: 3 }}>
          <CardContent sx={{ p: 0 }}>
            <TableContainer component={Paper} variant="outlined">
              <Table>
                <TableHead sx={{ bgcolor: '#f0fdf4' }}>
                  <TableRow>
                    {['#',
                      fr ? 'Utilisateur' : 'User',
                      fr ? 'Type' : 'Type',
                      fr ? 'Titre' : 'Title',
                      fr ? 'Statut' : 'Status',
                      fr ? 'Souhaité le' : 'Needed By',
                      fr ? 'Prête le' : 'Ready Date',
                      fr ? 'Créée le' : 'Created',
                      fr ? 'Actions' : 'Actions',
                    ].map(h => <TableCell key={h} sx={{ fontWeight: 700 }}>{h}</TableCell>)}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {loading ? (
                    <TableRow><TableCell colSpan={9} align="center" sx={{ py: 6 }}>
                      <CircularProgress sx={{ color: '#2d6a4f' }} />
                    </TableCell></TableRow>
                  ) : orders.length === 0 ? (
                    <TableRow><TableCell colSpan={9} align="center" sx={{ py: 6, color: 'text.secondary' }}>
                      {fr ? 'Aucune commande trouvée' : 'No orders found'}
                    </TableCell></TableRow>
                  ) : orders.map(order => (
                    <TableRow key={order.id} hover
                      sx={order.status === 'ready' ? { bgcolor: '#f0fdf4' } : {}}>
                      <TableCell sx={{ fontFamily: 'monospace', color: '#888' }}>#{order.id}</TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Avatar sx={{ bgcolor: '#1b4332', width: 30, height: 30, fontSize: 13 }}>
                            {order.user_name?.[0]?.toUpperCase()}
                          </Avatar>
                          <Box>
                            <Typography variant="body2" sx={{ fontWeight: 600, lineHeight: 1.2 }}>
                              {order.user_name}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {order.user_employee_id ? `ID: ${order.user_employee_id}` : order.user_email}
                            </Typography>
                          </Box>
                        </Box>
                      </TableCell>
                      <TableCell><Chip label={typeLabel(order.order_type)} size="small" variant="outlined" /></TableCell>
                      <TableCell sx={{ maxWidth: 200 }}>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>{order.title}</Typography>
                        {order.item_name && <Typography variant="caption" color="text.secondary">📦 {order.item_name}</Typography>}
                        {order.description && (
                          <Tooltip title={order.description} arrow>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5, cursor: 'help' }}>
                              <ChatBubbleOutline sx={{ fontSize: 13, color: 'primary.main' }} />
                              <Typography variant="caption" color="primary.main" noWrap sx={{ maxWidth: 130 }}>
                                {order.description}
                              </Typography>
                            </Box>
                          </Tooltip>
                        )}
                      </TableCell>
                      <TableCell>{statusChip(order.status)}</TableCell>
                      <TableCell><Typography variant="caption">{fmt(order.needed_date)}</Typography></TableCell>
                      <TableCell>
                        {order.ready_date
                          ? <Chip size="small" color="success" label={fmt(order.ready_date)} />
                          : <Typography variant="caption" color="text.secondary">—</Typography>}
                      </TableCell>
                      <TableCell><Typography variant="caption">{fmt(order.created_at)}</Typography></TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', gap: 0.5 }}>
                          {order.status !== 'ready' && order.status !== 'rejected' && (
                            <Tooltip title={fr ? 'Marquer prête' : 'Mark Ready'}>
                              <IconButton size="small" color="success"
                                onClick={() => handleMarkReady(order)} disabled={saving}>
                                <LocalShipping fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          )}
                          <Tooltip title={fr ? 'Gérer' : 'Manage'}>
                            <IconButton size="small" color="primary" onClick={() => openEdit(order)}>
                              <Edit fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title={fr ? 'Supprimer' : 'Delete'}>
                            <IconButton size="small" color="error" onClick={() => handleDelete(order)}>
                              <Delete fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
            <TablePagination component="div" count={total} page={page}
              onPageChange={(_, p) => setPage(p)} rowsPerPage={rowsPerPage}
              rowsPerPageOptions={[15]} labelRowsPerPage={fr ? 'Par page' : 'Per page'} />
          </CardContent>
        </Card>

        {/* Edit Dialog */}
        <Dialog open={!!editOrder} onClose={() => setEditOrder(null)} maxWidth="sm" fullWidth>
          <DialogTitle sx={{ bgcolor: '#1b4332', color: 'white', fontWeight: 700 }}>
            {fr ? 'Gérer la commande' : 'Manage Order'} #{editOrder?.id}
          </DialogTitle>
          <DialogContent sx={{ mt: 2 }}>
            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
            {editOrder && (
              <Grid container spacing={2} sx={{ mt: 0.5 }}>
                {/* Summary */}
                <Grid item xs={12}>
                  <Card variant="outlined" sx={{ p: 2, bgcolor: '#f9fafb' }}>
                    <Typography variant="body2"><strong>{fr ? 'Utilisateur:' : 'User:'}</strong> {editOrder.user_name}</Typography>
                    <Typography variant="body2"><strong>{fr ? 'Type:' : 'Type:'}</strong> {typeLabel(editOrder.order_type)}</Typography>
                    <Typography variant="body2"><strong>{fr ? 'Titre:' : 'Title:'}</strong> {editOrder.title}</Typography>
                    {editOrder.description && (
                      <Box sx={{ mt: 1, p: 1.5, bgcolor: '#f0f4ff', borderRadius: 1, borderLeft: '3px solid #1976d2' }}>
                        <Typography variant="caption" color="primary.main" fontWeight={600}>
                          {fr ? "💬 Commentaire de l'utilisateur :" : '💬 User comment:'}
                        </Typography>
                        <Typography variant="body2" sx={{ mt: 0.5 }}>{editOrder.description}</Typography>
                      </Box>
                    )}
                    {editOrder.needed_date && (
                      <Typography variant="body2"><strong>{fr ? 'Souhaité le:' : 'Needed by:'}</strong> {fmt(editOrder.needed_date)}</Typography>
                    )}
                  </Card>
                </Grid>
                <Grid item xs={12}><Divider /></Grid>

                {/* Status — 4 options only */}
                <Grid item xs={12}>
                  <FormControl fullWidth>
                    <InputLabel>{fr ? 'Nouveau statut' : 'New Status'}</InputLabel>
                    <Select value={editStatus} label={fr ? 'Nouveau statut' : 'New Status'}
                      onChange={e => setEditStatus(e.target.value)}>
                      {Object.entries(STATUSES).map(([k, v]) => (
                        <MenuItem key={k} value={k}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            {v.icon} {fr ? v.fr : v.en}
                          </Box>
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>

                {/* Ready date */}
                <Grid item xs={12}>
                  <DatePicker label={fr ? 'Date de disponibilité' : 'Ready Date'}
                    value={editReadyDate} onChange={d => setEditReadyDate(d)}
                    slotProps={{ textField: { fullWidth: true, size: 'small' } }} />
                </Grid>

                {/* Admin message */}
                <Grid item xs={12}>
                  <TextField fullWidth multiline rows={3}
                    label={fr ? "Message à l'utilisateur" : 'Message to User'}
                    value={editResponse} onChange={e => setEditResponse(e.target.value)}
                    helperText={fr ? 'Visible par l\'utilisateur.' : 'Visible to the user.'} />
                </Grid>

                {/* Auto-fill when ready */}
                {editStatus === 'ready' && (
                  <Grid item xs={12}>
                    <Button size="small" variant="outlined" color="success"
                      onClick={() => setEditResponse(fr
                        ? `Votre commande "${editOrder.title}" est prête à récupérer.`
                        : `Your order "${editOrder.title}" is ready for pickup.`)}>
                      ✨ {fr ? 'Message automatique' : 'Auto-fill message'}
                    </Button>
                  </Grid>
                )}
              </Grid>
            )}
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 2 }}>
            <Button onClick={() => setEditOrder(null)} disabled={saving}>{fr ? 'Annuler' : 'Cancel'}</Button>
            <Button onClick={handleSave} variant="contained" disabled={saving}
              color={editStatus === 'ready' ? 'success' : editStatus === 'rejected' ? 'error' : 'primary'}>
              {saving ? (fr ? 'Sauvegarde...' : 'Saving...')
                : editStatus === 'ready'  ? (fr ? '✅ Marquer prête' : '✅ Mark Ready')
                : editStatus === 'rejected' ? (fr ? '❌ Rejeter' : '❌ Reject')
                : (fr ? 'Enregistrer' : 'Save')}
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </LocalizationProvider>
  );
};

export default OrdersManagement;