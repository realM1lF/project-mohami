import React, { useState } from 'react';
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { 
  Paper, 
  Typography, 
  Box, 
  Chip,
  Card,
  CardContent,
} from '@mui/material';
import TicketCard from './TicketCard';
import { statusColors, priorityColors } from '../theme';

const COLUMNS = [
  { id: 'backlog', title: 'Backlog', icon: 'inbox' },
  { id: 'in_progress', title: 'In Progress', icon: 'engineering' },
  { id: 'clarification', title: 'Rückfrage', icon: 'help' },
  { id: 'testing', title: 'Testing', icon: 'science' },
  { id: 'done', title: 'Done', icon: 'check_circle' },
];

const getStatusColor = (status) => {
  return statusColors[status] || statusColors.backlog;
};

// Droppable Column Component with M3 styling
function DroppableColumn({ column, tickets, onTicketClick, isOver }) {
  const { setNodeRef } = useSortable({
    id: column.id,
    data: {
      type: 'column',
      column,
    },
  });

  const ticketIds = tickets.map(t => t.id);
  const statusColor = getStatusColor(column.id);

  return (
    <Paper
      ref={setNodeRef}
      elevation={isOver ? 2 : 0}
      sx={{
        minWidth: 280,
        maxWidth: 320,
        flex: 1,
        backgroundColor: isOver ? '#E8F4FD' : '#F2F4F7',
        borderRadius: 3,
        p: 2,
        minHeight: 500,
        display: 'flex',
        flexDirection: 'column',
        border: isOver ? '2px dashed #006495' : '2px solid transparent',
        transition: 'all 0.2s ease-in-out',
      }}
    >
      {/* Column Header */}
      <Box 
        sx={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          mb: 2,
          pb: 1.5,
          borderBottom: `2px solid ${statusColor.container}`,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <span className="material-symbols-rounded" style={{ 
            color: statusColor.main,
            fontSize: 20,
          }}>
            {column.icon}
          </span>
          <Typography 
            variant="titleMedium" 
            sx={{ 
              fontWeight: 600,
              color: '#1A1C1E',
              textTransform: 'uppercase',
              letterSpacing: '0.025em',
              fontSize: '0.875rem',
            }}
          >
            {column.title}
          </Typography>
        </Box>
        <Chip
          label={tickets.length}
          size="small"
          sx={{
            backgroundColor: statusColor.container,
            color: statusColor.onContainer,
            fontWeight: 600,
            height: 24,
            minWidth: 32,
          }}
        />
      </Box>

      {/* Tickets Container */}
      <SortableContext
        items={ticketIds}
        strategy={verticalListSortingStrategy}
      >
        <Box 
          sx={{ 
            flex: 1,
            minHeight: 400,
            borderRadius: 2,
            backgroundColor: isOver ? 'rgba(0, 100, 149, 0.04)' : 'transparent',
            transition: 'background-color 0.2s ease-in-out',
          }}
        >
          {tickets.map(ticket => (
            <TicketCard
              key={ticket.id}
              ticket={ticket}
              onClick={onTicketClick}
            />
          ))}
        </Box>
      </SortableContext>
    </Paper>
  );
}

// Drag Overlay Card (shown while dragging)
function DragOverlayCard({ ticket }) {
  const priorityColor = priorityColors[ticket.priority] || priorityColors.medium;
  const statusColor = statusColors[ticket.status] || statusColors.backlog;

  return (
    <Card
      elevation={4}
      sx={{
        width: 280,
        transform: 'rotate(3deg)',
        cursor: 'grabbing',
        borderLeft: `4px solid ${statusColor.main}`,
        backgroundColor: '#FDFCFF',
      }}
    >
      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
        <Chip
          label={ticket.priority.toUpperCase()}
          size="small"
          sx={{
            mb: 1,
            backgroundColor: priorityColor.container,
            color: priorityColor.onContainer,
            fontWeight: 600,
            fontSize: '0.625rem',
            height: 20,
          }}
        />
        <Typography 
          variant="titleMedium" 
          sx={{ 
            display: 'block',
            lineHeight: 1.4,
            color: '#1A1C1E',
          }}
        >
          {ticket.title}
        </Typography>
      </CardContent>
    </Card>
  );
}

function KanbanBoard({ tickets, onTicketClick, onTicketMove }) {
  const [activeId, setActiveId] = useState(null);
  const [overColumn, setOverColumn] = useState(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: (event) => {
        const { active } = event;
        return active?.rect?.current?.translated;
      },
    })
  );

  const handleDragStart = (event) => {
    setActiveId(event.active.id);
  };

  const handleDragOver = (event) => {
    const { over } = event;
    
    if (over) {
      const overColumnId = over.data?.current?.column?.id || over.id;
      if (COLUMNS.find(c => c.id === overColumnId)) {
        setOverColumn(overColumnId);
      }
    }
  };

  const handleDragEnd = (event) => {
    const { active, over } = event;
    
    setActiveId(null);
    setOverColumn(null);

    if (!over) return;

    const ticketId = active.id;
    
    let targetColumnId;
    
    if (over.data?.current?.type === 'column') {
      targetColumnId = over.data.current.column.id;
    } else if (over.data?.current?.type === 'ticket') {
      targetColumnId = over.data.current.ticket.status;
    } else {
      targetColumnId = over.id;
    }

    if (!COLUMNS.find(c => c.id === targetColumnId)) {
      return;
    }

    const ticket = tickets.find(t => t.id === ticketId);
    if (!ticket) return;

    if (ticket.status !== targetColumnId) {
      console.log(`Moving ticket ${ticketId} from ${ticket.status} to ${targetColumnId}`);
      onTicketMove(ticketId, targetColumnId);
    }
  };

  const activeTicket = activeId ? tickets.find(t => t.id === activeId) : null;

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
    >
      <Box
        sx={{
          display: 'flex',
          gap: 2,
          overflowX: 'auto',
          pb: 2,
          px: 1,
          minHeight: 'calc(100vh - 200px)',
          '&::-webkit-scrollbar': {
            height: 8,
          },
          '&::-webkit-scrollbar-track': {
            backgroundColor: '#F2F4F7',
            borderRadius: 4,
          },
          '&::-webkit-scrollbar-thumb': {
            backgroundColor: '#C1C7CE',
            borderRadius: 4,
          },
          '&::-webkit-scrollbar-thumb:hover': {
            backgroundColor: '#72787E',
          },
        }}
      >
        {COLUMNS.map(column => {
          const columnTickets = tickets.filter(t => t.status === column.id);
          
          return (
            <DroppableColumn
              key={column.id}
              column={column}
              tickets={columnTickets}
              onTicketClick={onTicketClick}
              isOver={overColumn === column.id}
            />
          );
        })}
      </Box>

      <DragOverlay>
        {activeTicket ? (
          <DragOverlayCard ticket={activeTicket} />
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}

export default KanbanBoard;
