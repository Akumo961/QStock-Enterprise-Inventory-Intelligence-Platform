import React, { useState, useEffect } from 'react';
import {
  Box, Stepper, Step, StepLabel, Button, Typography, Alert,
  TextField, Grid, Chip, Avatar, Paper, Dialog, DialogTitle,
  DialogContent, DialogActions, List, ListItem, ListItemText,
  ListItemAvatar, CircularProgress, Divider, Switch, FormControlLabel,
} from '@mui/material';
import {
  QrCodeScanner, Person, Inventory2, CheckCircle,
  ArrowForward, ArrowBack, CalendarMonth,
} from '@mui/icons-material';
import QRScanner from '../common/QRScanner';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../hooks/useAuth';

const API = '/api';
const authHeaders = () => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${localStorage.getItem('token')}`,
});

interface BorrowProcessProps {
  onComplete?: (transactionId: number) => void;
  onCancel?: () => void;
}

interface UserData  { id: number; email: string; full_name: string; department?: string; qr_code_data?: string; }
interface ItemData  { id: number; name: string; item_code: string; category: string; available_quantity: number; max_borrow_days?: number; description?: string; }

const BorrowProcess: React.FC<BorrowProcessProps> = ({ onComplete, onCancel }) => {
  const { language } = useLanguage();
  const { user: currentUser } = useAuth();
  const fr = language === 'fr';
  const isAdmin = currentUser?.is_admin;

  // Admin mode: borrow FOR a specific user
  const [adminMode, setAdminMode] = useState(false);
  const [activeStep, setActiveStep] = useState(0);

  const [userData, setUserData] = useState<UserData | null>(null);
  const [userQR, setUserQR]     = useState('');
  const [itemData, setItemData] = useState<ItemData | null>(null);
  const [itemQR, setItemQR]     = useState('');

  const [quantity, setQuantity]     = useState<number | ''>('');
  const [purpose, setPurpose]       = useState('');
  const [notes, setNotes]           = useState('');
  const [borrowDays, setBorrowDays] = useState<number | ''>('');

  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState('');
  const [transactionId, setTransactionId] = useState<number | null>(null);
  const [showScanner, setShowScanner]     = useState(false);
  const [scanTarget, setScanTarget]       = useState<'user' | 'item'>('item');

  // When not in admin mode, skip user-scan step
  const steps = adminMode
    ? [fr ? 'Scanner utilisateur' : 'Scan User', fr ? 'Scanner article' : 'Scan Item',
       fr ? 'Confirmer' : 'Confirm', fr ? 'Terminé' : 'Done']
    : [fr ? 'Scanner article' : 'Scan Item', fr ? 'Confirmer' : 'Confirm', fr ? 'Terminé' : 'Done'];

  // Reset when toggling admin mode
  useEffect(() => {
    setActiveStep(0);
    setUserData(null); setUserQR('');
    setItemData(null); setItemQR('');
    setError('');
  }, [adminMode]);

  const parseQR = (raw: string): { type: 'user' | 'item'; id: number } | null => {
    const parts = raw.split(':');
    if (parts.length < 2) return null;
    const type = parts[0].toLowerCase() as 'user' | 'item';
    const id = parseInt(parts[1]);
    if (!['user', 'item'].includes(type) || isNaN(id)) return null;
    return { type, id };
  };

  const fetchUser = async (id: number, qr: string) => {
    setLoading(true); setError('');
    try {
      const res = await fetch(`${API}/users/${id}`, { headers: authHeaders() });
      if (!res.ok) throw new Error(fr ? 'Utilisateur non trouvé' : 'User not found');
      const data = await res.json();
      setUserData(data); setUserQR(qr);
      setActiveStep(1);
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const fetchItem = async (id: number, qr: string) => {
    setLoading(true); setError('');
    try {
      const res = await fetch(`${API}/items/${id}`, { headers: authHeaders() });
      if (!res.ok) throw new Error(fr ? 'Article non trouvé' : 'Item not found');
      const data = await res.json();
      if (data.available_quantity < 1)
        throw new Error(fr ? 'Article non disponible' : 'Item not available');
      setItemData(data); setItemQR(qr);
      setBorrowDays('');
      setQuantity('');
      setActiveStep(adminMode ? 2 : 1);
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const handleScan = (raw: string) => {
    setShowScanner(false);
    const parsed = parseQR(raw);
    if (!parsed) { setError(fr ? 'Format QR invalide' : 'Invalid QR format'); return; }

    if (scanTarget === 'user') {
      if (parsed.type !== 'user') { setError(fr ? 'Scannez un QR utilisateur' : 'Please scan a user QR code'); return; }
      fetchUser(parsed.id, raw);
    } else {
      if (parsed.type !== 'item') { setError(fr ? 'Scannez un QR article' : 'Please scan an item QR code'); return; }
      fetchItem(parsed.id, raw);
    }
  };

  const handleBorrow = async () => {
    if (!quantity || !borrowDays) {
      setError(fr ? 'Veuillez entrer une quantité et une durée.' : 'Please enter a quantity and duration.');
      return;
    }
    setLoading(true); setError('');
    try {
      const body: any = {
        item_qr_code: itemQR,
        quantity: Number(quantity),
        purpose,
        notes: notes || undefined,
        due_days: Number(borrowDays),
      };
      // Admin borrows for user: pass user_qr_code; otherwise omit (borrow for self)
      if (adminMode && userQR) body.user_qr_code = userQR;

      const res = await fetch(`${API}/transactions/borrow`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(typeof err.detail === 'string' ? err.detail
          : (fr ? "Échec de l'emprunt" : 'Failed to borrow'));
      }
      const data = await res.json();
      setTransactionId(data.id);
      setActiveStep(adminMode ? 3 : 2);
      setTimeout(() => onComplete?.(data.id), 2500);
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const reset = () => {
    setActiveStep(0); setUserData(null); setUserQR('');
    setItemData(null); setItemQR(''); setQuantity(1);
    setPurpose(''); setBorrowDays(7); setError('');
    setTransactionId(null);
  };

  const confirmStep    = adminMode ? 2 : 1;
  const completeStep   = adminMode ? 3 : 2;
  const itemScanStep   = adminMode ? 1 : 0;

  return (
    <Box sx={{ maxWidth: 700, mx: 'auto' }}>
      {/* Admin mode toggle */}
      {isAdmin && (
        <FormControlLabel sx={{ mb: 2 }}
          control={<Switch checked={adminMode} onChange={e => setAdminMode(e.target.checked)} color="primary" />}
          label={<Typography variant="body2" sx={{ fontWeight: 600 }}>
            {fr ? 'Mode admin : emprunter pour un utilisateur' : 'Admin mode: borrow on behalf of user'}
          </Typography>}
        />
      )}

      <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
        {steps.map(label => <Step key={label}><StepLabel>{label}</StepLabel></Step>)}
      </Stepper>

      {error && <Alert severity="error" onClose={() => setError('')} sx={{ mb: 2 }}>{error}</Alert>}

      {/* ── Step: Scan User (admin only) ── */}
      {adminMode && activeStep === 0 && (
        <Box sx={{ textAlign: 'center', py: 2 }}>
          <Avatar sx={{ width: 72, height: 72, mx: 'auto', mb: 2, bgcolor: '#1b4332' }}>
            <Person sx={{ fontSize: 40 }} />
          </Avatar>
          <Typography variant="h6" gutterBottom>
            {fr ? "Scanner la carte de l'utilisateur" : "Scan User's QR Card"}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            {fr ? "Scannez le code QR de la carte fidélité de l'utilisateur"
                : "Scan the loyalty card QR code of the user to borrow for"}
          </Typography>
          {userData ? (
            <Paper variant="outlined" sx={{ p: 2, mb: 2, bgcolor: '#f0fdf4' }}>
              <Typography variant="subtitle2" color="success.main">✅ {fr ? 'Utilisateur vérifié' : 'User verified'}</Typography>
              <Typography variant="h6">{userData.full_name}</Typography>
              <Typography variant="body2" color="text.secondary">{userData.email}</Typography>
            </Paper>
          ) : (
            <Button variant="contained" size="large" startIcon={<QrCodeScanner />}
              onClick={() => { setScanTarget('user'); setShowScanner(true); }}
              disabled={loading} sx={{ bgcolor: '#2d6a4f' }}>
              {fr ? 'Scanner QR utilisateur' : 'Scan User QR Code'}
            </Button>
          )}
        </Box>
      )}

      {/* ── Step: Scan Item ── */}
      {activeStep === itemScanStep && (
        <Box sx={{ textAlign: 'center', py: 2 }}>
          <Avatar sx={{ width: 72, height: 72, mx: 'auto', mb: 2, bgcolor: '#2d6a4f' }}>
            <Inventory2 sx={{ fontSize: 40 }} />
          </Avatar>
          <Typography variant="h6" gutterBottom>
            {fr ? "Scanner le code QR de l'article" : 'Scan Item QR Code'}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            {fr ? "Scannez le code QR sur l'article à emprunter"
                : 'Scan the QR code on the item you want to borrow'}
          </Typography>
          {itemData ? (
            <Paper variant="outlined" sx={{ p: 2, mb: 2, bgcolor: '#f0fdf4' }}>
              <Typography variant="subtitle2" color="success.main">✅ {fr ? 'Article trouvé' : 'Item found'}</Typography>
              <Typography variant="h6">{itemData.name}</Typography>
              <Typography variant="body2" color="text.secondary">{itemData.item_code}</Typography>
              <Chip label={fr ? `${itemData.available_quantity} disponible(s)` : `${itemData.available_quantity} available`}
                size="small" color="success" sx={{ mt: 1 }} />
            </Paper>
          ) : (
            <Button variant="contained" size="large" startIcon={<QrCodeScanner />}
              onClick={() => { setScanTarget('item'); setShowScanner(true); }}
              disabled={loading} sx={{ bgcolor: '#2d6a4f' }}>
              {fr ? "Scanner QR article" : 'Scan Item QR Code'}
            </Button>
          )}
        </Box>
      )}

      {/* ── Step: Confirm ── */}
      {activeStep === confirmStep && itemData && (
        <Box>
          <Typography variant="h6" sx={{ mb: 3 }}>
            {fr ? "Confirmer l'emprunt" : 'Confirm Borrow Details'}
          </Typography>
          <Grid container spacing={2}>
            {adminMode && userData && (
              <Grid item xs={12}>
                <Paper variant="outlined" sx={{ p: 2, bgcolor: '#f0fdf4' }}>
                  <Typography variant="subtitle2" color="text.secondary">{fr ? 'Emprunté pour' : 'Borrowing for'}</Typography>
                  <Typography variant="body1" sx={{ fontWeight: 600 }}>{userData.full_name}</Typography>
                  <Typography variant="body2" color="text.secondary">{userData.email}</Typography>
                </Paper>
              </Grid>
            )}
            <Grid item xs={12}>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">{fr ? 'Article' : 'Item'}</Typography>
                <Typography variant="body1" sx={{ fontWeight: 600 }}>{itemData.name}</Typography>
                <Typography variant="body2" color="text.secondary">{itemData.description || itemData.item_code}</Typography>
              </Paper>
            </Grid>
            <Grid item xs={6}>
              <TextField fullWidth label={fr ? 'Quantité' : 'Quantity'} type="number"
                value={quantity}
                placeholder="1"
                onChange={e => {
                  const val = parseInt(e.target.value);
                  if (e.target.value === '') { setQuantity(''); return; }
                  if (!isNaN(val)) setQuantity(Math.max(1, Math.min(itemData.available_quantity, val)));
                }}
                inputProps={{ min: 1, max: itemData.available_quantity }}
                helperText={`Max: ${itemData.available_quantity}`} />
            </Grid>
            <Grid item xs={6}>
              <TextField fullWidth label={fr ? 'Durée (jours)' : 'Duration (days)'} type="number"
                value={borrowDays}
                placeholder={itemData.max_borrow_days ? String(itemData.max_borrow_days) : '7'}
                onChange={e => {
                  const val = parseInt(e.target.value);
                  if (e.target.value === '') { setBorrowDays(''); return; }
                  if (!isNaN(val)) {
                    const max = itemData.max_borrow_days ?? 365;
                    setBorrowDays(Math.min(max, Math.max(1, val)));
                  }
                }}
                InputProps={{ startAdornment: <CalendarMonth sx={{ mr: 1, color: 'action.active' }} /> }}
                inputProps={{ min: 1, max: itemData.max_borrow_days ?? 365 }}
                helperText={itemData.max_borrow_days
                  ? (fr ? `Max: ${itemData.max_borrow_days} jours` : `Max: ${itemData.max_borrow_days} days`)
                  : undefined}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField fullWidth multiline rows={2}
                label={fr ? 'Motif (optionnel)' : 'Purpose (optional)'}
                placeholder={fr ? 'Ex: Activité scoute, sortie, atelier…' : 'e.g. Scout activity, outing, workshop…'}
                value={purpose} onChange={e => setPurpose(e.target.value)} />
            </Grid>
            <Grid item xs={12}>
              <TextField fullWidth multiline rows={2}
                label={fr ? 'Commentaire / Note (optionnel)' : 'Comment / Note (optional)'}
                placeholder={fr ? "Informations supplémentaires pour l'administrateur…" : 'Additional info for the admin…'}
                value={notes} onChange={e => setNotes(e.target.value)} />
            </Grid>
            {borrowDays !== '' && (
              <Grid item xs={12}>
                <Alert severity="info">
                  {fr ? "À retourner avant le " : "Must be returned by "}
                  <strong>{new Date(Date.now() + Number(borrowDays) * 86400000).toLocaleDateString(fr ? 'fr-CA' : 'en-CA')}</strong>
                </Alert>
              </Grid>
            )}
          </Grid>
        </Box>
      )}

      {/* ── Step: Done ── */}
      {activeStep === completeStep && (
        <Box sx={{ textAlign: 'center', py: 3 }}>
          <Avatar sx={{ width: 90, height: 90, mx: 'auto', mb: 2, bgcolor: 'success.main' }}>
            <CheckCircle sx={{ fontSize: 55 }} />
          </Avatar>
          <Typography variant="h5" color="success.main" sx={{ fontWeight: 700, mb: 1 }}>
            {fr ? 'Emprunt réussi !' : 'Borrow Successful!'}
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            {fr ? `Transaction #${transactionId}` : `Transaction #${transactionId}`}
          </Typography>
          <Divider sx={{ my: 2 }} />
          <Grid container spacing={2} sx={{ textAlign: 'left', maxWidth: 400, mx: 'auto' }}>
            {adminMode && userData && (
              <Grid item xs={6}>
                <Typography variant="caption" color="text.secondary">{fr ? 'Emprunté par' : 'Borrowed by'}</Typography>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>{userData.full_name}</Typography>
              </Grid>
            )}
            <Grid item xs={6}>
              <Typography variant="caption" color="text.secondary">{fr ? 'Article' : 'Item'}</Typography>
              <Typography variant="body2" sx={{ fontWeight: 600 }}>{itemData?.name}</Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="caption" color="text.secondary">{fr ? 'Retour avant' : 'Due date'}</Typography>
              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                {new Date(Date.now() + borrowDays * 86400000).toLocaleDateString(fr ? 'fr-CA' : 'en-CA')}
              </Typography>
            </Grid>
          </Grid>
          <Button variant="contained" sx={{ mt: 4, bgcolor: '#2d6a4f' }} onClick={reset}>
            {fr ? 'Nouvel emprunt' : 'Borrow Another'}
          </Button>
        </Box>
      )}

      {/* Navigation */}
      {activeStep < completeStep && (
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 4 }}>
          <Button onClick={activeStep === 0 ? (onCancel || reset) : () => setActiveStep(p => p - 1)}
            startIcon={<ArrowBack />} disabled={loading}>
            {activeStep === 0 ? (fr ? 'Annuler' : 'Cancel') : (fr ? 'Retour' : 'Back')}
          </Button>
          {activeStep === confirmStep && (
            <Button variant="contained" onClick={handleBorrow}
              endIcon={loading ? <CircularProgress size={18} /> : <CheckCircle />}
              disabled={loading || !itemData || !quantity || !borrowDays}
              sx={{ bgcolor: '#2d6a4f' }}>
              {fr ? "Confirmer l'emprunt" : 'Confirm Borrow'}
            </Button>
          )}
        </Box>
      )}

      {/* QR Scanner Dialog */}
      <Dialog open={showScanner} onClose={() => setShowScanner(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {scanTarget === 'user'
            ? (fr ? 'Scanner la carte utilisateur' : 'Scan User Card')
            : (fr ? "Scanner le QR de l'article" : 'Scan Item QR Code')}
        </DialogTitle>
        <DialogContent>
          <QRScanner onScanSuccess={handleScan} onScanError={setError} height={380} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowScanner(false)}>{fr ? 'Annuler' : 'Cancel'}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default BorrowProcess;