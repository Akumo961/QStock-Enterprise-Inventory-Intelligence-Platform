/**
 * TransactionsManagement.tsx — Admin-only live borrow tracker
 *
 * Shows every borrow transaction across all users in one filterable table.
 * The core screen admins actually need daily: who has what, since when,
 * due when, and whether it's overdue — with a quick "Mark Returned" action
 * right inline so they don't have to navigate away.
 *
 * Backend: GET /api/transactions/ (admin sees all, regular users see own only)
 * Route:   /admin/transactions  (AdminRoute-protected in App.tsx)
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Card, CardContent, Typography, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Paper, Chip,
  Alert, CircularProgress, Button, IconButton, Tooltip,
  FormControl, InputLabel, Select, MenuItem, Grid,
  TablePagination, InputAdornment, TextField, Avatar,
  Dialog, DialogTitle, DialogContent, DialogActions, Divider,
  Badge,
} from '@mui/material';
import {
  Search, FilterList, CheckCircle, HourglassEmpty,
  Assignment, Warning, Refresh, Person, Inventory2,
  EventAvailable, EventBusy, MoreVert, ChatBubbleOutline,
} from '@mui/icons-material';
import { useLanguage } from '../../context/LanguageContext';

const API = '/api';
const authHeaders = () => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${localStorage.getItem('token')}`,
});

// ─── Types ──────────────────────────────────────────────────────────────────

interface Transaction {
  id: number;
  user_id: number;
  user_name: string;
  user_email: string;
  item_id: number;
  item_name: string;
  item_code: string;
  status: 'borrowed' | 'returned' | 'overdue' | 'cancelled';
  quantity: number;
  borrowed_at: string;
  due_date?: string;
  returned_at?: string;
  purpose?: string;
  notes?: string;
}

// ─── Status config ───────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<string, { color: any; icon: React.ReactNode; en: string; fr: string }> = {
  borrowed:  { color: 'primary', icon: <HourglassEmpty fontSize="small" />, en: 'Borrowed',  fr: 'Emprunté'   },
  returned:  { color: 'success', icon: <CheckCircle   fontSize="small" />, en: 'Returned',  fr: 'Retourné'   },
  overdue:   { color: 'error',   icon: <Warning        fontSize="small" />, en: 'Overdue',   fr: 'En retard'  },
  cancelled: { color: 'default', icon: <Assignment     fontSize="small" />, en: 'Cancelled', fr: 'Annulé'     },
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

const fmt = (iso?: string) =>
  iso ? new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }) : '—';

const isOverdue = (t: Transaction) =>
  t.status === 'borrowed' && t.due_date && new Date(t.due_date) < new Date();

const daysOverdue = (due?: string) => {
  if (!due) return 0;
  return Math.floor((Date.now() - new Date(due).getTime()) / 86_400_000);
};

// ─── Component ───────────────────────────────────────────────────────────────

const TransactionsManagement: React.FC = () => {
  const { language } = useLanguage();
  const fr = language === 'fr';

  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading]           = useState(true);
  const [error, setError]               = useState('');
  const [success, setSuccess]           = useState('');

  const [search, setSearch]             = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [overdueOnly, setOverdueOnly]   = useState(false);
  const [page, setPage]                 = useState(0);
  const [total, setTotal]               = useState(0);
  const rowsPerPage                     = 15;

  // Summary counts for the stat cards at the top
  const [stats, setStats] = useState({ active: 0, overdue: 0, returned: 0 });

  // Detail dialog
  const [detail, setDetail] = useState<Transaction | null>(null);
  const [marking, setMarking] = useState(false);

  // ── Fetch ────────────────────────────────────────────────────────────────

  const fetchTransactions = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const params = new URLSearchParams({
        page: (page + 1).toString(),
        page_size: rowsPerPage.toString(),
        ...(filterStatus  && { status: filterStatus }),
        ...(overdueOnly   && { overdue_only: 'true' }),
      });

      const res = await fetch(`${API}/transactions/?${params}`, { headers: authHeaders() });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setTransactions(data.transactions ?? []);
      setTotal(data.total ?? 0);
    } catch (e: any) {
      setError(e.message || (fr ? 'Impossible de charger les transactions.' : 'Failed to load transactions.'));
    } finally {
      setLoading(false);
    }
  }, [page, filterStatus, overdueOnly, fr]);

  // Light summary fetch (no pagination, just counts) — runs once on mount
  const fetchStats = useCallback(async () => {
    try {
      const [activeRes, overdueRes, returnedRes] = await Promise.all([
        fetch(`${API}/transactions/?page=1&page_size=1&status=borrowed`,  { headers: authHeaders() }),
        fetch(`${API}/transactions/?page=1&page_size=1&overdue_only=true`, { headers: authHeaders() }),
        fetch(`${API}/transactions/?page=1&page_size=1&status=returned`,  { headers: authHeaders() }),
      ]);
      const [a, o, r] = await Promise.all([activeRes.json(), overdueRes.json(), returnedRes.json()]);
      setStats({ active: a.total ?? 0, overdue: o.total ?? 0, returned: r.total ?? 0 });
    } catch { /* non-critical */ }
  }, []);

  useEffect(() => { fetchTransactions(); }, [fetchTransactions]);
  useEffect(() => { fetchStats(); }, [fetchStats]);

  // Auto-dismiss success banner
  useEffect(() => {
    if (!success) return;
    const t = setTimeout(() => setSuccess(''), 4000);
    return () => clearTimeout(t);
  }, [success]);

  // ── Mark returned ────────────────────────────────────────────────────────

  const handleMarkReturned = async (txId: number) => {
    setMarking(true);
    try {
      const res = await fetch(`${API}/transactions/${txId}/return`, {
        method: 'POST',
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error(await res.text());
      setSuccess(fr ? 'Article marqué comme retourné.' : 'Item marked as returned.');
      setDetail(null);
      fetchTransactions();
      fetchStats();
    } catch (e: any) {
      setError(e.message || (fr ? 'Échec du retour.' : 'Failed to mark returned.'));
    } finally {
      setMarking(false);
    }
  };

  // ── Client-side search (user name / item name / item code) ───────────────

  const visible = search.trim()
    ? transactions.filter(t =>
        t.user_name.toLowerCase().includes(search.toLowerCase()) ||
        t.user_email.toLowerCase().includes(search.toLowerCase()) ||
        t.item_name.toLowerCase().includes(search.toLowerCase()) ||
        t.item_code.toLowerCase().includes(search.toLowerCase())
      )
    : transactions;

  // ── Stat cards ────────────────────────────────────────────────────────────

  const statCards = [
    { label: fr ? 'En cours' : 'Active Borrows', value: stats.active,   color: '#1565c0', bg: '#e3f2fd', icon: <HourglassEmpty /> },
    { label: fr ? 'En retard' : 'Overdue',        value: stats.overdue,  color: '#c62828', bg: '#ffebee', icon: <Warning /> },
    { label: fr ? 'Retournés' : 'Returned',        value: stats.returned, color: '#2e7d32', bg: '#e8f5e9', icon: <CheckCircle /> },
  ];

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <Box sx={{ p: { xs: 2, md: 3 } }}>

      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3, flexWrap: 'wrap', gap: 1 }}>
        <Box>
          <Typography variant="h5" fontWeight={700}>
            {fr ? 'Transactions' : 'Transactions'}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {fr ? 'Vue en direct de tous les emprunts' : 'Live view of all borrows across all users'}
          </Typography>
        </Box>
        <Button startIcon={<Refresh />} onClick={() => { fetchTransactions(); fetchStats(); }} variant="outlined" size="small">
          {fr ? 'Actualiser' : 'Refresh'}
        </Button>
      </Box>

      {/* Stat cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {statCards.map(card => (
          <Grid item xs={12} sm={4} key={card.label}>
            <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
              <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2, py: '12px !important' }}>
                <Avatar sx={{ bgcolor: card.bg, color: card.color, width: 44, height: 44 }}>
                  {card.icon}
                </Avatar>
                <Box>
                  <Typography variant="h5" fontWeight={700} color={card.color}>{card.value}</Typography>
                  <Typography variant="caption" color="text.secondary">{card.label}</Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Alerts */}
      {error   && <Alert severity="error"   sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}

      {/* Filters */}
      <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={5}>
              <TextField
                fullWidth size="small"
                placeholder={fr ? 'Rechercher par utilisateur ou article…' : 'Search by user or item…'}
                value={search}
                onChange={e => setSearch(e.target.value)}
                InputProps={{ startAdornment: <InputAdornment position="start"><Search fontSize="small" /></InputAdornment> }}
              />
            </Grid>
            <Grid item xs={6} sm={3}>
              <FormControl fullWidth size="small">
                <InputLabel>{fr ? 'Statut' : 'Status'}</InputLabel>
                <Select value={filterStatus} label={fr ? 'Statut' : 'Status'} onChange={e => { setFilterStatus(e.target.value); setPage(0); }}>
                  <MenuItem value="">{fr ? 'Tous' : 'All'}</MenuItem>
                  {Object.entries(STATUS_CONFIG).map(([k, v]) => (
                    <MenuItem key={k} value={k}>{fr ? v.fr : v.en}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={6} sm={4}>
              <Button
                fullWidth
                variant={overdueOnly ? 'contained' : 'outlined'}
                color="error"
                startIcon={<EventBusy />}
                onClick={() => { setOverdueOnly(o => !o); setFilterStatus(''); setPage(0); }}
                size="medium"
              >
                {fr ? 'En retard seulement' : 'Overdue only'}
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Table */}
      <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
            <CircularProgress />
          </Box>
        ) : visible.length === 0 ? (
          <Box sx={{ py: 6, textAlign: 'center' }}>
            <Assignment sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
            <Typography color="text.secondary">
              {fr ? 'Aucune transaction trouvée.' : 'No transactions found.'}
            </Typography>
          </Box>
        ) : (
          <>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ bgcolor: 'grey.50' }}>
                    <TableCell sx={{ fontWeight: 700 }}>{fr ? 'Utilisateur' : 'User'}</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>{fr ? 'Article' : 'Item'}</TableCell>
                    <TableCell sx={{ fontWeight: 700 }} align="center">{fr ? 'Qté' : 'Qty'}</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>{fr ? 'Emprunté le' : 'Borrowed'}</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>{fr ? 'Échéance' : 'Due'}</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>{fr ? 'Retourné le' : 'Returned'}</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>{fr ? 'Statut' : 'Status'}</TableCell>
                    <TableCell sx={{ fontWeight: 700 }} align="center">{fr ? 'Action' : 'Action'}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {visible.map(tx => {
                    const overdue = isOverdue(tx);
                    const cfg = STATUS_CONFIG[tx.status] ?? STATUS_CONFIG.borrowed;
                    const days = overdue ? daysOverdue(tx.due_date) : 0;

                    return (
                      <TableRow
                        key={tx.id}
                        hover
                        sx={{
                          bgcolor: overdue ? 'rgba(211,47,47,0.04)' : 'inherit',
                          borderLeft: overdue ? '3px solid #d32f2f' : '3px solid transparent',
                        }}
                      >
                        {/* User */}
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Avatar sx={{ width: 30, height: 30, fontSize: 13, bgcolor: 'primary.main' }}>
                              {tx.user_name.charAt(0).toUpperCase()}
                            </Avatar>
                            <Box>
                              <Typography variant="body2" fontWeight={600} noWrap>{tx.user_name}</Typography>
                              <Typography variant="caption" color="text.secondary" noWrap>{tx.user_email}</Typography>
                            </Box>
                          </Box>
                        </TableCell>

                        {/* Item */}
                        <TableCell>
                          <Typography variant="body2" fontWeight={500} noWrap>{tx.item_name}</Typography>
                          <Typography variant="caption" color="text.secondary">{tx.item_code}</Typography>
                          {tx.purpose && (
                            <Tooltip title={tx.purpose} arrow>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5, cursor: 'help' }}>
                                <ChatBubbleOutline sx={{ fontSize: 13, color: 'primary.main' }} />
                                <Typography variant="caption" color="primary.main" noWrap sx={{ maxWidth: 140 }}>
                                  {tx.purpose}
                                </Typography>
                              </Box>
                            </Tooltip>
                          )}
                        </TableCell>

                        {/* Qty */}
                        <TableCell align="center">
                          <Typography variant="body2">{tx.quantity}</Typography>
                        </TableCell>

                        {/* Borrowed */}
                        <TableCell>
                          <Typography variant="body2">{fmt(tx.borrowed_at)}</Typography>
                        </TableCell>

                        {/* Due */}
                        <TableCell>
                          {tx.due_date ? (
                            <Box>
                              <Typography variant="body2" color={overdue ? 'error.main' : 'inherit'} fontWeight={overdue ? 700 : 400}>
                                {fmt(tx.due_date)}
                              </Typography>
                              {overdue && (
                                <Typography variant="caption" color="error.main">
                                  {days}d {fr ? 'de retard' : 'overdue'}
                                </Typography>
                              )}
                            </Box>
                          ) : (
                            <Typography variant="body2" color="text.disabled">—</Typography>
                          )}
                        </TableCell>

                        {/* Returned */}
                        <TableCell>
                          <Typography variant="body2" color={tx.returned_at ? 'success.main' : 'text.disabled'}>
                            {tx.returned_at ? fmt(tx.returned_at) : '—'}
                          </Typography>
                        </TableCell>

                        {/* Status chip */}
                        <TableCell>
                          <Chip
                            icon={cfg.icon as any}
                            label={fr ? cfg.fr : cfg.en}
                            color={overdue ? 'error' : cfg.color}
                            size="small"
                            variant={overdue ? 'filled' : 'outlined'}
                          />
                        </TableCell>

                        {/* Action */}
                        <TableCell align="center">
                          <Tooltip title={fr ? 'Voir le détail' : 'View detail'}>
                            <IconButton size="small" onClick={() => setDetail(tx)}>
                              <MoreVert fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>

            <TablePagination
              component="div"
              count={total}
              page={page}
              rowsPerPage={rowsPerPage}
              onPageChange={(_, p) => setPage(p)}
              rowsPerPageOptions={[rowsPerPage]}
              labelDisplayedRows={({ from, to, count }) =>
                fr ? `${from}–${to} sur ${count}` : `${from}–${to} of ${count}`
              }
            />
          </>
        )}
      </Card>

      {/* Detail dialog */}
      <Dialog open={!!detail} onClose={() => setDetail(null)} maxWidth="sm" fullWidth>
        {detail && (() => {
          const cfg = STATUS_CONFIG[detail.status] ?? STATUS_CONFIG.borrowed;
          const overdue = isOverdue(detail);
          return (
            <>
              <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Assignment color="primary" />
                {fr ? 'Détail de la transaction' : 'Transaction Detail'}
                <Box sx={{ ml: 'auto' }}>
                  <Chip
                    label={fr ? cfg.fr : cfg.en}
                    color={overdue ? 'error' : cfg.color}
                    size="small"
                  />
                </Box>
              </DialogTitle>

              <DialogContent dividers>
                <Grid container spacing={2}>
                  {/* User */}
                  <Grid item xs={12}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1 }}>
                      <Person color="action" />
                      <Typography variant="subtitle2" color="text.secondary">{fr ? 'Utilisateur' : 'User'}</Typography>
                    </Box>
                    <Typography fontWeight={600}>{detail.user_name}</Typography>
                    <Typography variant="body2" color="text.secondary">{detail.user_email}</Typography>
                  </Grid>

                  <Divider sx={{ width: '100%', mx: 2 }} />

                  {/* Item */}
                  <Grid item xs={12}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1 }}>
                      <Inventory2 color="action" />
                      <Typography variant="subtitle2" color="text.secondary">{fr ? 'Article' : 'Item'}</Typography>
                    </Box>
                    <Typography fontWeight={600}>{detail.item_name}</Typography>
                    <Typography variant="body2" color="text.secondary">{detail.item_code} · {fr ? 'Qté' : 'Qty'}: {detail.quantity}</Typography>
                  </Grid>

                  <Divider sx={{ width: '100%', mx: 2 }} />

                  {/* Dates */}
                  <Grid item xs={6}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                      <EventAvailable fontSize="small" color="action" />
                      <Typography variant="caption" color="text.secondary">{fr ? 'Emprunté le' : 'Borrowed'}</Typography>
                    </Box>
                    <Typography variant="body2" fontWeight={500}>{fmt(detail.borrowed_at)}</Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                      <EventBusy fontSize="small" color={overdue ? 'error' : 'action'} />
                      <Typography variant="caption" color={overdue ? 'error.main' : 'text.secondary'}>{fr ? 'Échéance' : 'Due Date'}</Typography>
                    </Box>
                    <Typography variant="body2" fontWeight={500} color={overdue ? 'error.main' : 'inherit'}>
                      {fmt(detail.due_date)}
                      {overdue && ` (${daysOverdue(detail.due_date)}d ${fr ? 'de retard' : 'overdue'})`}
                    </Typography>
                  </Grid>
                  {detail.returned_at && (
                    <Grid item xs={6}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                        <CheckCircle fontSize="small" color="success" />
                        <Typography variant="caption" color="text.secondary">{fr ? 'Retourné le' : 'Returned'}</Typography>
                      </Box>
                      <Typography variant="body2" fontWeight={500} color="success.main">{fmt(detail.returned_at)}</Typography>
                    </Grid>
                  )}

                  {/* Purpose / Notes */}
                  {detail.purpose && (
                    <Grid item xs={12}>
                      <Typography variant="caption" color="text.secondary">{fr ? 'Motif' : 'Purpose'}</Typography>
                      <Typography variant="body2">{detail.purpose}</Typography>
                    </Grid>
                  )}
                  {detail.notes && (
                    <Grid item xs={12}>
                      <Typography variant="caption" color="text.secondary">{fr ? 'Notes' : 'Notes'}</Typography>
                      <Typography variant="body2">{detail.notes}</Typography>
                    </Grid>
                  )}
                </Grid>
              </DialogContent>

              <DialogActions>
                <Button onClick={() => setDetail(null)} disabled={marking}>{fr ? 'Fermer' : 'Close'}</Button>
                {(detail.status === 'borrowed' || detail.status === 'overdue') && (
                  <Button
                    onClick={() => handleMarkReturned(detail.id)}
                    variant="contained"
                    color="success"
                    startIcon={marking ? <CircularProgress size={16} color="inherit" /> : <CheckCircle />}
                    disabled={marking}
                  >
                    {marking ? (fr ? 'En cours…' : 'Processing…') : (fr ? 'Marquer retourné' : 'Mark as Returned')}
                  </Button>
                )}
              </DialogActions>
            </>
          );
        })()}
      </Dialog>

    </Box>
  );
};

export default TransactionsManagement;