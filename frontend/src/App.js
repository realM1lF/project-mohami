import React, { useState, useEffect } from 'react';
import { 
  AppBar, 
  Toolbar, 
  Typography, 
  Fab, 
  Box, 
  CircularProgress,
  Container,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import KanbanBoard from './components/KanbanBoard';
import TicketDetail from './components/TicketDetail';
import NewTicketModal from './components/NewTicketModal';
import EditTicketModal from './components/EditTicketModal';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [tickets, setTickets] = useState([]);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [editingTicket, setEditingTicket] = useState(null);
  const [showNewTicket, setShowNewTicket] = useState(false);
  const [loading, setLoading] = useState(true);

  // Fetch tickets
  const fetchTickets = async () => {
    try {
      const response = await fetch(`${API_URL}/tickets`);
      const data = await response.json();
      setTickets(data);
    } catch (error) {
      console.error('Error fetching tickets:', error);
    } finally {
      setLoading(false);
    }
  };

  // Poll every 3 seconds for updates
  useEffect(() => {
    fetchTickets();
    const interval = setInterval(fetchTickets, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleTicketClick = (ticket) => {
    setSelectedTicket(ticket);
  };

  const ALLOWED_MOVES = {
    backlog:        ['in_progress'],
    in_progress:    ['backlog'],
    clarification:  [],
    testing:        ['done', 'in_progress'],
    done:           [],
  };

  const handleTicketMove = async (ticketId, newStatus) => {
    const ticket = tickets.find(t => t.id === ticketId);
    if (!ticket) return;

    const allowed = ALLOWED_MOVES[ticket.status] || [];
    if (!allowed.includes(newStatus)) {
      return;
    }

    try {
      const response = await fetch(`${API_URL}/tickets/${ticketId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      
      if (response.ok) {
        setTickets(prev => prev.map(t => 
          t.id === ticketId ? { ...t, status: newStatus } : t
        ));
        fetchTickets();
      }
    } catch (error) {
      console.error('Error moving ticket:', error);
    }
  };

  const handleCreateTicket = async (ticketData) => {
    try {
      const { agent, ...createData } = ticketData;
      const response = await fetch(`${API_URL}/tickets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(createData),
      });
      if (response.ok) {
        const created = await response.json();
        if (agent) {
          await fetch(`${API_URL}/tickets/${created.id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ agent }),
          });
        }
        fetchTickets();
        setShowNewTicket(false);
      }
    } catch (error) {
      console.error('Error creating ticket:', error);
    }
  };

  const handleUpdateTicket = async (ticketId, updates) => {
    try {
      const response = await fetch(`${API_URL}/tickets/${ticketId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      
      if (response.ok) {
        fetchTickets();
        setEditingTicket(null);
        if (selectedTicket && selectedTicket.id === ticketId) {
          const updated = await response.json();
          setSelectedTicket(updated);
        }
      }
    } catch (error) {
      console.error('Error updating ticket:', error);
    }
  };

  const handleDeleteTicket = async (ticketId) => {
    if (!window.confirm('Ticket wirklich löschen?')) return;
    
    try {
      const response = await fetch(`${API_URL}/tickets/${ticketId}`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        fetchTickets();
        setSelectedTicket(null);
        setEditingTicket(null);
      }
    } catch (error) {
      console.error('Error deleting ticket:', error);
    }
  };

  const handleAddComment = async (ticketId, content) => {
    try {
      await fetch(`${API_URL}/tickets/${ticketId}/comments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ author: 'user', content }),
      });
      const response = await fetch(`${API_URL}/tickets/${ticketId}`);
      const updatedTicket = await response.json();
      setSelectedTicket(updatedTicket);
      fetchTickets();
    } catch (error) {
      console.error('Error adding comment:', error);
    }
  };

  if (loading) {
    return (
      <Box 
        sx={{ 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center', 
          height: '100vh',
          backgroundColor: '#FDFCFF',
        }}
      >
        <Box sx={{ textAlign: 'center' }}>
          <SmartToyIcon 
            sx={{ 
              fontSize: 64, 
              color: '#006495', 
              mb: 2,
              animation: 'pulse 2s infinite',
            }} 
          />
          <Typography variant="titleMedium" color="text.secondary">
            Mohami wird geladen...
          </Typography>
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={{ 
      minHeight: '100vh', 
      display: 'flex', 
      flexDirection: 'column',
      backgroundColor: '#FDFCFF',
    }}>
      {/* Material Design 3 App Bar */}
      <AppBar 
        position="static" 
        elevation={0}
        sx={{ 
          backgroundColor: '#FDFCFF',
          borderBottom: '1px solid #DDE3EA',
        }}
      >
        <Toolbar sx={{ px: { xs: 2, sm: 3 } }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Box
              sx={{
                width: 40,
                height: 40,
                borderRadius: 3,
                backgroundColor: '#006495',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <SmartToyIcon sx={{ color: 'white', fontSize: 24 }} />
            </Box>
            <Box>
              <Typography 
                variant="titleLarge" 
                sx={{ 
                  color: '#1A1C1E',
                  fontWeight: 600,
                  letterSpacing: '-0.015em',
                }}
              >
                Mohami
              </Typography>
              <Typography 
                variant="bodySmall" 
                sx={{ 
                  color: '#72787E',
                  display: 'block',
                  lineHeight: 1,
                }}
              >
                KI-Mitarbeiter Board
              </Typography>
            </Box>
          </Box>
          
          <Box sx={{ flexGrow: 1 }} />
          
          <Typography 
            variant="bodyMedium" 
            sx={{ 
              color: '#72787E',
              display: { xs: 'none', sm: 'block' },
            }}
          >
            {tickets.length} Tickets
          </Typography>
        </Toolbar>
      </AppBar>

      {/* Main Content */}
      <Box 
        component="main" 
        sx={{ 
          flex: 1, 
          p: 2,
          overflow: 'hidden',
        }}
      >
        <Container 
          maxWidth={false} 
          sx={{ 
            height: '100%',
            px: { xs: 1, sm: 2 } 
          }}
        >
          <KanbanBoard 
            tickets={tickets} 
            onTicketClick={handleTicketClick}
            onTicketMove={handleTicketMove}
          />
        </Container>
      </Box>

      {/* Material Design 3 FAB */}
      <Fab
        color="primary"
        aria-label="Neues Ticket"
        onClick={() => setShowNewTicket(true)}
        sx={{
          position: 'fixed',
          bottom: 24,
          right: 24,
          backgroundColor: '#65587B',
          '&:hover': {
            backgroundColor: '#4A3F5C',
          },
          boxShadow: '0px 4px 8px rgba(0,0,0,0.15), 0px 1px 3px rgba(0,0,0,0.1)',
        }}
      >
        <AddIcon />
      </Fab>

      {/* Modals */}
      {selectedTicket && (
        <TicketDetail
          ticket={selectedTicket}
          onClose={() => setSelectedTicket(null)}
          onAddComment={handleAddComment}
          onEdit={() => {
            setEditingTicket(selectedTicket);
            setSelectedTicket(null);
          }}
          onDelete={() => handleDeleteTicket(selectedTicket.id)}
        />
      )}

      {showNewTicket && (
        <NewTicketModal
          onClose={() => setShowNewTicket(false)}
          onCreate={handleCreateTicket}
        />
      )}

      {editingTicket && (
        <EditTicketModal
          ticket={editingTicket}
          onClose={() => setEditingTicket(null)}
          onUpdate={handleUpdateTicket}
          onDelete={handleDeleteTicket}
        />
      )}
    </Box>
  );
}

export default App;
