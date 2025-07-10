import {
  AccessTime as AccessTimeIcon,
  Assessment as AssessmentIcon,
  AttachMoney as AttachMoneyIcon,
  Business as BusinessIcon,
  Category as CategoryIcon,
  LocationOn as LocationOnIcon,
  OpenInNew as OpenInNewIcon,
} from '@mui/icons-material';
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  List,
  ListItem,
  ListItemText,
  Typography,
} from '@mui/material';
import { differenceInDays, format, parseISO } from 'date-fns';

const GrantDetailsModal = ({ grant, open, onClose }) => {
  if (!grant) return null;

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

  const renderScoreSection = (scores, title) => {
    if (
      !scores ||
      typeof scores !== 'object' ||
      Object.keys(scores).length === 0
    ) {
      return null;
    }

    return (
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom startIcon={<AssessmentIcon />}>
            {title}
          </Typography>
          <Grid container spacing={2}>
            {Object.entries(scores).map(([key, value]) => (
              <Grid item xs={6} sm={4} key={key}>
                <Typography variant="body2" color="textSecondary">
                  {key
                    .replace(/_/g, ' ')
                    .replace(/\b\w/g, (c) => c.toUpperCase())}
                </Typography>
                <Typography variant="h6" color="primary">
                  {typeof value === 'number' ? value.toFixed(2) : value}
                </Typography>
              </Grid>
            ))}
          </Grid>
        </CardContent>
      </Card>
    );
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle sx={{ pb: 1 }}>
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
          }}
        >
          <Typography variant="h5" component="div" sx={{ flexGrow: 1, pr: 2 }}>
            {grant.title}
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {isExpired && <Chip label="EXPIRED" size="small" color="error" />}
            {isUrgent && (
              <Chip
                label={`${daysToDeadline} days left`}
                size="small"
                color="warning"
              />
            )}
            <Chip
              label={grant.category || grant.identified_sector || 'Other'}
              size="small"
              color="primary"
            />
          </Box>
        </Box>
      </DialogTitle>

      <DialogContent dividers>
        <Grid container spacing={3}>
          {/* Basic Information */}
          <Grid item xs={12} md={8}>
            <Typography variant="h6" gutterBottom>
              Description
            </Typography>
            <Typography variant="body1" paragraph>
              {grant.description || 'No description available'}
            </Typography>

            {grant.summary_llm && (
              <>
                <Typography variant="h6" gutterBottom>
                  AI-Generated Summary
                </Typography>
                <Typography
                  variant="body1"
                  paragraph
                  sx={{
                    fontStyle: 'italic',
                    bgcolor: 'grey.50',
                    p: 2,
                    borderRadius: 1,
                  }}
                >
                  {grant.summary_llm}
                </Typography>
              </>
            )}

            {grant.eligibility_summary_llm && (
              <>
                <Typography variant="h6" gutterBottom>
                  Eligibility Requirements
                </Typography>
                <Typography
                  variant="body1"
                  paragraph
                  sx={{
                    fontStyle: 'italic',
                    bgcolor: 'primary.50',
                    p: 2,
                    borderRadius: 1,
                  }}
                >
                  {grant.eligibility_summary_llm}
                </Typography>
              </>
            )}
          </Grid>

          {/* Key Details Sidebar */}
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Key Details
                </Typography>

                {/* Funder */}
                {grant.funder_name && (
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <BusinessIcon sx={{ mr: 1, color: 'primary.main' }} />
                    <Box>
                      <Typography variant="caption" color="textSecondary">
                        Funder
                      </Typography>
                      <Typography variant="body2" fontWeight="medium">
                        {grant.funder_name}
                      </Typography>
                    </Box>
                  </Box>
                )}

                {/* Funding Amount */}
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <AttachMoneyIcon sx={{ mr: 1, color: 'success.main' }} />
                  <Box>
                    <Typography variant="caption" color="textSecondary">
                      Funding
                    </Typography>
                    <Typography variant="body2" fontWeight="medium">
                      {grant.funding_amount_display ||
                        grant.fundingAmount ||
                        'Not specified'}
                    </Typography>
                  </Box>
                </Box>

                {/* Deadline */}
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <AccessTimeIcon
                    sx={{
                      mr: 1,
                      color: isExpired
                        ? 'error.main'
                        : isUrgent
                        ? 'warning.main'
                        : 'text.secondary',
                    }}
                  />
                  <Box>
                    <Typography variant="caption" color="textSecondary">
                      Deadline
                    </Typography>
                    <Typography
                      variant="body2"
                      fontWeight="medium"
                      color={
                        isExpired
                          ? 'error.main'
                          : isUrgent
                          ? 'warning.main'
                          : 'text.primary'
                      }
                    >
                      {grant.deadline || grant.deadline_date
                        ? format(
                            parseISO(grant.deadline || grant.deadline_date),
                            'MMM d, yyyy'
                          )
                        : 'Not specified'}
                    </Typography>
                    {daysToDeadline !== null && (
                      <Typography variant="caption" color="textSecondary">
                        {isExpired
                          ? 'Expired'
                          : `${daysToDeadline} days remaining`}
                      </Typography>
                    )}
                  </Box>
                </Box>

                {/* Geographic Scope */}
                {grant.geographic_scope && (
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <LocationOnIcon sx={{ mr: 1, color: 'info.main' }} />
                    <Box>
                      <Typography variant="caption" color="textSecondary">
                        Geographic Scope
                      </Typography>
                      <Typography variant="body2" fontWeight="medium">
                        {grant.geographic_scope}
                      </Typography>
                    </Box>
                  </Box>
                )}

                {/* Source */}
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <CategoryIcon sx={{ mr: 1, color: 'text.secondary' }} />
                  <Box>
                    <Typography variant="caption" color="textSecondary">
                      Source
                    </Typography>
                    <Typography variant="body2" fontWeight="medium">
                      {grant.source_name || grant.source || 'Unknown'}
                    </Typography>
                  </Box>
                </Box>

                {/* Overall Score */}
                {grant.overall_composite_score !== null &&
                  grant.overall_composite_score !== undefined && (
                    <Box
                      sx={{
                        textAlign: 'center',
                        mt: 2,
                        p: 2,
                        bgcolor: 'primary.50',
                        borderRadius: 1,
                      }}
                    >
                      <Typography variant="caption" color="textSecondary">
                        Overall Relevance Score
                      </Typography>
                      <Typography
                        variant="h4"
                        color="primary.main"
                        fontWeight="bold"
                      >
                        {grant.overall_composite_score !== null &&
                        grant.overall_composite_score !== undefined
                          ? grant.overall_composite_score.toFixed(1)
                          : 'N/A'}
                      </Typography>
                    </Box>
                  )}
              </CardContent>
            </Card>
          </Grid>

          {/* Keywords */}
          {grant.keywords && grant.keywords.length > 0 && (
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>
                Keywords
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                {grant.keywords.map((keyword, idx) => (
                  <Chip
                    key={idx}
                    label={keyword}
                    size="small"
                    variant="outlined"
                  />
                ))}
              </Box>
            </Grid>
          )}

          {/* Detailed Scores */}
          <Grid item xs={12}>
            {renderScoreSection(grant.research_scores, 'Research Scores')}
            {renderScoreSection(grant.compliance_scores, 'Compliance Scores')}
          </Grid>

          {/* Enrichment Log */}
          {grant.enrichment_log && grant.enrichment_log.length > 0 && (
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>
                Processing Log
              </Typography>
              <List dense>
                {grant.enrichment_log.map((log, idx) => (
                  <ListItem key={idx}>
                    <ListItemText
                      primary={log}
                      primaryTypographyProps={{ variant: 'body2' }}
                    />
                  </ListItem>
                ))}
              </List>
            </Grid>
          )}
        </Grid>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>Close</Button>
        {(grant.source_url || grant.sourceUrl) && (
          <Button
            variant="contained"
            endIcon={<OpenInNewIcon />}
            href={grant.source_url || grant.sourceUrl}
            target="_blank"
            rel="noopener noreferrer"
          >
            View Original Grant
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default GrantDetailsModal;
