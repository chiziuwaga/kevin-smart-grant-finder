import { Button, Dialog, DialogActions, DialogContent, DialogTitle, Table, TableBody, TableCell, TableHead, TableRow } from '@mui/material';
import React, { useEffect, useState } from 'react';
import API from '../../api/apiClient';

const RunHistoryModal = ({ open, onClose }) => {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    if(open){
      API.getRunHistory().then(setHistory).catch(console.error);
    }
  }, [open]);

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Recent Discovery Runs</DialogTitle>
      <DialogContent dividers>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Started</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Stored/Total</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {history.map((h,i)=>(
              <TableRow key={i}>
                <TableCell>{new Date(h.start).toLocaleString()}</TableCell>
                <TableCell>{h.status}</TableCell>
                <TableCell>{h.stored ?? '-'} / {h.total ?? '-'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

export default RunHistoryModal; 