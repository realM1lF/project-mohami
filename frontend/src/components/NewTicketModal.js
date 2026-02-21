import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Typography,
  Box,
  IconButton,
  Grid,
  CircularProgress,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import AddIcon from '@mui/icons-material/Add';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const PRIORITY_OPTIONS = [
  { value: 'low', label: 'Niedrig' },
  { value: 'medium', label: 'Mittel' },
  { value: 'high', label: 'Hoch' },
];

const selectSx = {
  '& .MuiOutlinedInput-root': {
    borderRadius: 2,
    backgroundColor: '#F2F4F7',
    '& fieldset': { borderColor: 'transparent' },
    '&:hover fieldset': { borderColor: '#C1C7CE' },
    '&.Mui-focused fieldset': { borderColor: '#006495' },
  },
};

const inputLabelSx = {
  color: '#72787E',
  '&.Mui-focused': { color: '#006495' },
};

function NewTicketModal({ onClose, onCreate }) {
  const [customers, setCustomers] = useState([]);
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);

  const [formData, setFormData] = useState({
    title: '',
    description: '',
    customer: '',
    repository: '',
    agent: '',
    priority: 'medium',
  });

  useEffect(() => {
    Promise.all([
      fetch(`${API_URL}/config/customers`).then(r => r.json()).catch(() => []),
      fetch(`${API_URL}/config/agents`).then(r => r.json()).catch(() => []),
    ]).then(([c, a]) => {
      setCustomers(c);
      setAgents(a);
      if (c.length === 1) {
        const repos = c[0].repositories || [];
        setFormData(prev => ({
          ...prev,
          customer: c[0].id,
          repository: repos.length === 1 ? repos[0].repo : '',
        }));
      }
      if (a.length === 1) {
        setFormData(prev => ({ ...prev, agent: a[0].id }));
      }
      setLoading(false);
    });
  }, []);

  const selectedCustomer = customers.find(c => c.id === formData.customer);
  const availableRepos = selectedCustomer?.repositories || [];

  const handleSubmit = (e) => {
    e.preventDefault();
    const { agent, ...ticketData } = formData;
    onCreate({ ...ticketData, agent });
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => {
      const next = { ...prev, [name]: value };
      if (name === 'customer') {
        next.repository = '';
        const cust = customers.find(c => c.id === value);
        if (cust?.repositories?.length === 1) {
          next.repository = cust.repositories[0].repo;
        }
      }
      return next;
    });
  };

  const isValid = formData.title.trim() && formData.description.trim() &&
    formData.customer && formData.repository && formData.agent;

  if (loading) {
    return (
      <Dialog open={true} onClose={onClose} maxWidth="sm" fullWidth
        PaperProps={{ sx: { borderRadius: 4, backgroundColor: '#FDFCFF' } }}>
        <DialogContent sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={true} onClose={onClose} maxWidth="sm" fullWidth
      PaperProps={{ sx: { borderRadius: 4, backgroundColor: '#FDFCFF' } }}>
      <form onSubmit={handleSubmit}>
        <DialogTitle sx={{
          px: 3, py: 2.5,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          borderBottom: '1px solid #DDE3EA',
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Box sx={{
              width: 36, height: 36, borderRadius: 2, backgroundColor: '#EBDDFF',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <AddIcon sx={{ color: '#65587B', fontSize: 20 }} />
            </Box>
            <Typography variant="headlineSmall" sx={{ color: '#1A1C1E', fontWeight: 500 }}>
              Neues Ticket erstellen
            </Typography>
          </Box>
          <IconButton onClick={onClose} size="small" sx={{ color: '#72787E' }}>
            <CloseIcon />
          </IconButton>
        </DialogTitle>

        <DialogContent sx={{ px: 3, py: 3 }}>
          <Grid container spacing={2.5}>
            {/* Title */}
            <Grid item xs={12}>
              <TextField fullWidth label="Titel" name="title"
                value={formData.title} onChange={handleChange}
                placeholder="z.B. Bug in Checkout fixen" required
                variant="outlined" sx={selectSx}
                InputLabelProps={{ sx: inputLabelSx }} />
            </Grid>

            {/* Description */}
            <Grid item xs={12}>
              <TextField fullWidth label="Beschreibung" name="description"
                value={formData.description} onChange={handleChange}
                placeholder="Detaillierte Beschreibung des Problems oder der Anforderung..."
                required multiline rows={4} variant="outlined" sx={selectSx}
                InputLabelProps={{ sx: inputLabelSx }} />
            </Grid>

            {/* Customer Dropdown */}
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth required sx={selectSx}>
                <InputLabel id="customer-label" sx={inputLabelSx}>Kunde</InputLabel>
                <Select labelId="customer-label" name="customer"
                  value={formData.customer} onChange={handleChange} label="Kunde">
                  {customers.map(c => (
                    <MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            {/* Repository Dropdown */}
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth required sx={selectSx}
                disabled={!formData.customer || availableRepos.length === 0}>
                <InputLabel id="repo-label" sx={inputLabelSx}>Repository</InputLabel>
                <Select labelId="repo-label" name="repository"
                  value={formData.repository} onChange={handleChange} label="Repository">
                  {availableRepos.map(r => (
                    <MenuItem key={r.repo} value={r.repo}>{r.repo}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            {/* Agent Dropdown */}
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth required sx={selectSx}>
                <InputLabel id="agent-label" sx={inputLabelSx}>KI-Mitarbeiter</InputLabel>
                <Select labelId="agent-label" name="agent"
                  value={formData.agent} onChange={handleChange} label="KI-Mitarbeiter">
                  {agents.map(a => (
                    <MenuItem key={a.id} value={a.id}>
                      {a.name}{a.description ? ` — ${a.description}` : ''}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            {/* Priority Dropdown */}
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth sx={selectSx}>
                <InputLabel id="priority-label" sx={inputLabelSx}>Priorität</InputLabel>
                <Select labelId="priority-label" name="priority"
                  value={formData.priority} onChange={handleChange} label="Priorität">
                  {PRIORITY_OPTIONS.map(opt => (
                    <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </DialogContent>

        <DialogActions sx={{ px: 3, py: 2.5, borderTop: '1px solid #DDE3EA', gap: 1 }}>
          <Button type="button" onClick={onClose} sx={{
            color: '#72787E', textTransform: 'none', borderRadius: 5, px: 3,
          }}>
            Abbrechen
          </Button>
          <Button type="submit" variant="contained" disabled={!isValid} sx={{
            backgroundColor: '#006495', textTransform: 'none', borderRadius: 5, px: 4,
            '&:hover': { backgroundColor: '#004B6F' },
            '&.Mui-disabled': { backgroundColor: '#DDE3EA', color: '#72787E' },
          }}>
            Ticket erstellen
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}

export default NewTicketModal;
