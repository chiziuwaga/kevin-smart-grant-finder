import React from 'react';
import { 
  Card, 
  CardContent, 
  Typography, 
  Chip, 
  Box, 
  IconButton, 
  Button,
  useTheme
} from '@mui/material';
import { 
  AccessTime as AccessTimeIcon,
  AttachMoney as AttachMoneyIcon,
  BookmarkBorder as BookmarkBorderIcon,
  Bookmark as BookmarkIcon,
  OpenInNew as OpenInNewIcon
} from '@mui/icons-material';
import { format, parseISO, differenceInDays } from 'date-fns';

const GrantCard = ({ grant, onSave, isSaved }) => {
  const theme = useTheme();
  
  const categoryColors = {
    Research: theme.palette.info.main,
    Education: theme.palette.success.main,
    Community: theme.palette.warning.main,
    Healthcare: theme.palette.error.main,
    Environment: theme.palette.secondary.main,
    Arts: '#9c27b0',
    Business: '#795548',
    Energy: '#607d8b',
    Other: theme.palette.grey[500]
  };
  
  const daysToDeadline = differenceInDays(
    parseISO(grant.deadline),
    new Date()
  );
  
  const formatFunding = (fundingAmount) => {
    if (!fundingAmount) return 'Not specified';
    return fundingAmount;
  };
  
  return (
    <Card sx={{ 
      height: '100%', 
      display: 'flex', 
      flexDirection: 'column',
      transition: 'transform 0.2s, box-shadow 0.2s',
      '&:hover': {
        transform: 'translateY(-4px)',
        boxShadow: '0 10px 20px rgba(0,0,0,0.1)'
      }
    }}>
      <CardContent sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Chip 
            label={grant.category} 
            size="small" 
            sx={{ 
              backgroundColor: categoryColors[grant.category] || categoryColors.Other,
              color: 'white'
            }}
          />
          <Box
            sx={{
              width: 36,
              height: 36,
              borderRadius: '50%',
              bgcolor: grant.relevanceScore >= 90 
                ? theme.palette.success.main 
                : grant.relevanceScore >= 80 
                  ? theme.palette.info.main 
                  : theme.palette.warning.main,
              color: 'white',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 'bold',
              fontSize: '0.8rem'
            }}
          >
            {grant.relevanceScore}
          </Box>
        </Box>
        
        <Typography variant="h6" component="h2" gutterBottom>
          {grant.title}
        </Typography>
        
        <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
          {grant.source}
        </Typography>
        
        {grant.description && (
          <Typography variant="body2" sx={{ mb: 2 }}>
            {grant.description.length > 140 
              ? `${grant.description.substring(0, 140)}...` 
              : grant.description}
          </Typography>
        )}
        
        <Box sx={{ mt: 'auto' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
            <AccessTimeIcon fontSize="small" sx={{ 
              mr: 1, 
              color: daysToDeadline < 14 
                ? theme.palette.error.main 
                : theme.palette.text.secondary 
            }} />
            <Typography variant="body2">
              Deadline: {format(parseISO(grant.deadline), 'MMM d, yyyy')}
              <Typography component="span" variant="caption" sx={{ 
                color: daysToDeadline < 14 ? theme.palette.error.main : 'text.secondary', 
                ml: 1,
                fontWeight: daysToDeadline < 14 ? 'bold' : 'normal'
              }}>
                ({daysToDeadline} days)
              </Typography>
            </Typography>
          </Box>
          
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <AttachMoneyIcon fontSize="small" sx={{ mr: 1, color: theme.palette.success.main }} />
            <Typography variant="body2">
              Funding: {formatFunding(grant.fundingAmount)}
            </Typography>
          </Box>
          
          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
            <Button 
              size="small" 
              variant="outlined" 
              color="primary"
              endIcon={<OpenInNewIcon />}
              href={grant.sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
            >
              View Details
            </Button>
            
            <IconButton 
              color={isSaved ? 'secondary' : 'default'} 
              onClick={() => onSave && onSave(grant.id, !isSaved)}
              size="small"
              sx={{ ml: 1 }}
            >
              {isSaved ? <BookmarkIcon /> : <BookmarkBorderIcon />}
            </IconButton>
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
};

export default GrantCard; 