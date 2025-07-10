import {
  AccessTime as AccessTimeIcon,
  AttachMoney as AttachMoneyIcon,
  BookmarkBorder as BookmarkBorderIcon,
  Bookmark as BookmarkIcon,
  InfoOutlined as InfoOutlinedIcon, // Added for scores tooltip
  OpenInNew as OpenInNewIcon,
} from '@mui/icons-material';
import {
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Chip,
  IconButton,
  Tooltip, // Added for detailed scores
  Typography,
  useTheme,
} from '@mui/material';
import { differenceInDays, format, parseISO } from 'date-fns';
import React from 'react';

const GrantCard = ({
  grant,
  onSave,
  isSaved,
  onViewDetails,
  onSelect,
  isSelected,
}) => {
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
    Other: theme.palette.grey[500],
  };

  const daysToDeadline =
    grant.deadline || grant.deadline_date
      ? differenceInDays(
          parseISO(grant.deadline || grant.deadline_date),
          new Date()
        )
      : null;

  const isExpired = daysToDeadline !== null && daysToDeadline < 0;
  const isUrgent =
    daysToDeadline !== null && daysToDeadline > 0 && daysToDeadline < 14;

  const renderScores = (scores, title) => {
    if (
      !scores ||
      typeof scores !== 'object' ||
      Object.keys(scores).length === 0
    ) {
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
        <Typography variant="caption" fontWeight="bold">
          {title}:
        </Typography>
        {Object.entries(scores).map(([key, value]) => (
          <Typography
            key={key}
            variant="caption"
            display="block"
            sx={{ ml: 1 }}
          >
            {key
              .replace(/_/g, ' ')
              .replace(/\\b(\\w)/g, (c) => c.toUpperCase())}
            : {formatScoreValue(value)}
          </Typography>
        ))}
      </Box>
    );
  };

  return (
    <Card
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        transition: 'transform 0.2s, box-shadow 0.2s',
        border: isSelected ? '2px solid' : '1px solid transparent',
        borderColor: isSelected ? 'primary.main' : 'transparent',
        '&:hover': {
          transform: 'translateY(-4px)',
          boxShadow: '0 10px 20px rgba(0,0,0,0.1)',
        },
      }}
    >
      <CardContent
        sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}
      >
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            mb: 2,
          }}
        >
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', flex: 1 }}>
            <Chip
              label={grant.category || grant.identified_sector || 'Other'}
              size="small"
              sx={{
                backgroundColor:
                  categoryColors[grant.category] || categoryColors.Other,
                color: 'white',
              }}
            />
            {isExpired && (
              <Chip
                label="EXPIRED"
                size="small"
                color="error"
                sx={{ fontWeight: 'bold' }}
              />
            )}
            {isUrgent && (
              <Chip
                label={`${daysToDeadline} days left`}
                size="small"
                color="warning"
                sx={{ fontWeight: 'bold' }}
              />
            )}
          </Box>

          {/* Selection Checkbox */}
          {onSelect && (
            <Checkbox
              checked={isSelected || false}
              onChange={(e) => onSelect(grant.id, e.target.checked)}
              size="small"
              sx={{ p: 0.5 }}
            />
          )}

          <Box
            sx={{
              width: 36,
              height: 36,
              borderRadius: '50%',
              bgcolor:
                grant.overall_composite_score >= 90
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
              fontSize: '0.8rem',
            }}
          >
            {grant.overall_composite_score !== undefined &&
            grant.overall_composite_score !== null
              ? grant.overall_composite_score.toFixed(0)
              : grant.relevanceScore !== undefined &&
                grant.relevanceScore !== null
              ? grant.relevanceScore.toString()
              : 'N/A'}
          </Box>
        </Box>

        <Typography variant="h6" component="h2" gutterBottom>
          {grant.title}
        </Typography>

        {grant.funder_name && (
          <Typography
            variant="body2"
            color="primary"
            sx={{ mb: 1, fontWeight: 'medium' }}
          >
            Funder: {grant.funder_name}
          </Typography>
        )}

        <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
          {grant.source_name || grant.source || 'Unknown Source'}
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
            <Typography variant="body2" fontWeight="bold" color="textSecondary">
              AI Summary:
            </Typography>
            <Typography variant="body2" sx={{ mb: 1, fontStyle: 'italic' }}>
              {grant.summary_llm.length > 120
                ? `${grant.summary_llm.substring(0, 120)}...`
                : grant.summary_llm}
            </Typography>
          </Box>
        )}

        {grant.eligibility_summary_llm && (
          <Box mt={1}>
            <Typography variant="body2" fontWeight="bold" color="textSecondary">
              AI Eligibility:
            </Typography>
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
              <Tooltip
                title={
                  <React.Fragment>
                    {renderScores(grant.research_scores, 'Research Scores')}
                    {renderScores(grant.compliance_scores, 'Compliance Scores')}
                  </React.Fragment>
                }
              >
                <Button
                  size="small"
                  startIcon={<InfoOutlinedIcon />}
                  variant="text"
                  sx={{
                    textTransform: 'none',
                    color: theme.palette.text.secondary,
                  }}
                >
                  View Detailed Scores
                </Button>
              </Tooltip>
            </Box>
          )}

          <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
            <AccessTimeIcon
              fontSize="small"
              sx={{
                mr: 1,
                color: isExpired
                  ? theme.palette.error.main
                  : isUrgent
                  ? theme.palette.warning.main
                  : theme.palette.text.secondary,
              }}
            />
            <Typography variant="body2">
              Deadline:{' '}
              {grant.deadline || grant.deadline_date
                ? format(
                    parseISO(grant.deadline || grant.deadline_date),
                    'MMM d, yyyy'
                  )
                : 'Not specified'}
              {daysToDeadline !== null && (
                <Typography
                  component="span"
                  variant="caption"
                  sx={{
                    color: isExpired
                      ? theme.palette.error.main
                      : isUrgent
                      ? theme.palette.warning.main
                      : 'text.secondary',
                    ml: 1,
                    fontWeight: isExpired || isUrgent ? 'bold' : 'normal',
                  }}
                >
                  ({isExpired ? 'Expired' : `${daysToDeadline} days`})
                </Typography>
              )}
            </Typography>
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <AttachMoneyIcon
              fontSize="small"
              sx={{ mr: 1, color: theme.palette.success.main }}
            />
            <Typography variant="body2">
              Funding:{' '}
              {grant.funding_amount_display ||
                grant.fundingAmount ||
                'Not specified'}
            </Typography>
          </Box>

          {grant.geographic_scope && (
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <Typography variant="body2" color="textSecondary">
                <strong>Geographic Scope:</strong> {grant.geographic_scope}
              </Typography>
            </Box>
          )}

          {grant.keywords && grant.keywords.length > 0 && (
            <Box sx={{ mb: 2 }}>
              <Typography
                variant="caption"
                color="textSecondary"
                display="block"
                sx={{ mb: 0.5 }}
              >
                Keywords:
              </Typography>
              <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                {grant.keywords.slice(0, 3).map((keyword, idx) => (
                  <Chip
                    key={idx}
                    label={keyword}
                    size="small"
                    variant="outlined"
                    sx={{ fontSize: '0.7rem', height: '20px' }}
                  />
                ))}
                {grant.keywords.length > 3 && (
                  <Typography
                    variant="caption"
                    color="textSecondary"
                    sx={{ alignSelf: 'center' }}
                  >
                    +{grant.keywords.length - 3} more
                  </Typography>
                )}
              </Box>
            </Box>
          )}

          <Box
            sx={{ display: 'flex', justifyContent: 'space-between', gap: 1 }}
          >
            <Button
              size="small"
              variant="outlined"
              color="primary"
              onClick={() => onViewDetails && onViewDetails(grant)}
            >
              Full Details
            </Button>

            <Button
              size="small"
              variant="outlined"
              color="primary"
              endIcon={<OpenInNewIcon />}
              href={grant.source_url || grant.sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              disabled={!grant.source_url && !grant.sourceUrl}
            >
              View Original
            </Button>

            <IconButton
              color={isSaved ? 'secondary' : 'default'}
              onClick={() => onSave && onSave(grant.id, !isSaved)}
              size="small"
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
