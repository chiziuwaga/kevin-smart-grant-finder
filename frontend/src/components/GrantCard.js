import React from 'react';
import { 
  Card, 
  CardContent, 
  Typography, 
  Chip, 
  Box, 
  IconButton, 
  Button,
  useTheme,
  Tooltip // Added for detailed scores
} from '@mui/material';
import { 
  AccessTime as AccessTimeIcon,
  AttachMoney as AttachMoneyIcon,
  BookmarkBorder as BookmarkBorderIcon,
  Bookmark as BookmarkIcon,
  OpenInNew as OpenInNewIcon,
  InfoOutlined as InfoOutlinedIcon // Added for scores tooltip
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
  
  const renderScores = (scores, title) => {
    if (!scores || typeof scores !== 'object' || Object.keys(scores).length === 0) {
      return null;
    }
    // Ensure score values are numbers and format them, otherwise display as is
    const formatScoreValue = (value) => {
      if (typeof value === 'number') {
        return value.toFixed(2);
      }
      if (typeof value === 'string' && !isNaN(parseFloat(value))) {
        return parseFloat(value).toFixed(2);
      }
      return value;
    };

    return (
      <Box mt={1}>
        <Typography variant="caption" fontWeight="bold">{title}:</Typography>
        {Object.entries(scores).map(([key, value]) => (
          <Typography key={key} variant="caption" display="block" sx={{ ml: 1 }}>
            {key.replace(/_/g, ' ').replace(/\\b(\\w)/g, c => c.toUpperCase())}: {formatScoreValue(value)}
          </Typography>
        ))}
      </Box>
    );
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
              bgcolor: grant.overall_composite_score >= 90 
                ? theme.palette.success.main 
                : grant.overall_composite_score >= 80 
                  ? theme.palette.info.main 
                  : grant.overall_composite_score >= 70
                    ? theme.palette.warning.main
                    : theme.palette.error.light, 
              color: 'white',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 'bold',
              fontSize: '0.8rem'
            }}
          >
            {grant.overall_composite_score !== undefined ? grant.overall_composite_score.toFixed(0) : (grant.relevanceScore !== undefined ? grant.relevanceScore : 'N/A')} 
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

        {grant.summary_llm && (
          <Box mt={1}>
            <Typography variant="body2" fontWeight="bold" color="textSecondary">AI Summary:</Typography>
            <Typography variant="body2" sx={{ mb: 1, fontStyle: 'italic' }}>
              {grant.summary_llm.length > 120 
                ? `${grant.summary_llm.substring(0, 120)}...` 
                : grant.summary_llm}
            </Typography>
          </Box>
        )}

        {grant.eligibility_summary_llm && (
          <Box mt={1}>
            <Typography variant="body2" fontWeight="bold" color="textSecondary">AI Eligibility:</Typography>
            <Typography variant="body2" sx={{ mb: 2, fontStyle: 'italic' }}>
              {grant.eligibility_summary_llm.length > 120 
                ? `${grant.eligibility_summary_llm.substring(0, 120)}...` 
                : grant.eligibility_summary_llm}
            </Typography>
          </Box>
        )}
        
        <Box sx={{ mt: 'auto' }}>
          {(grant.research_scores || grant.compliance_scores) && (
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <Tooltip title={
                <React.Fragment>
                  {renderScores(grant.research_scores, "Research Scores")}
                  {renderScores(grant.compliance_scores, "Compliance Scores")}
                </React.Fragment>
              }>
                <Button size="small" startIcon={<InfoOutlinedIcon />} variant="text" sx={{ textTransform: 'none', color: theme.palette.text.secondary }}>
                  View Detailed Scores
                </Button>
              </Tooltip>
            </Box>
          )}

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
              Funding: {grant.funding_amount_display || grant.fundingAmount || 'Not specified'}
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