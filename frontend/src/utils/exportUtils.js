// utils/exportUtils.js
import { saveAs } from 'file-saver';
import jsPDF from 'jspdf';
import 'jspdf-autotable';

/**
 * Export grants data to CSV format
 * @param {Array} grants - Array of grant objects
 * @param {string} filename - Filename for the export
 */
export const exportToCSV = (grants, filename = 'grants_export.csv') => {
  const headers = [
    'Title',
    'Category',
    'Funder',
    'Deadline',
    'Funding Amount',
    'Relevance Score',
    'Geographic Scope',
    'Description',
    'Source URL',
    'Keywords',
    'Application Open Date',
    'Created At',
  ];

  const rows = grants.map((grant) => [
    grant.title || '',
    grant.category || grant.identified_sector || '',
    grant.funder_name || '',
    grant.deadline || grant.deadline_date || '',
    grant.funding_amount_display || grant.fundingAmount || '',
    grant.overall_composite_score || grant.relevanceScore || '',
    grant.geographic_scope || '',
    grant.description || '',
    grant.source_url || grant.sourceUrl || '',
    (grant.keywords || []).join('; '),
    grant.application_open_date || '',
    grant.created_at || '',
  ]);

  const csvContent = [headers, ...rows]
    .map((row) =>
      row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(',')
    )
    .join('\n');

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  saveAs(blob, filename);
};

/**
 * Export grants data to PDF format
 * @param {Array} grants - Array of grant objects
 * @param {string} filename - Filename for the export
 * @param {Object} options - Export options
 */
export const exportToPDF = (
  grants,
  filename = 'grants_export.pdf',
  options = {}
) => {
  const pdf = new jsPDF();
  const pageWidth = pdf.internal.pageSize.width;

  // Title
  pdf.setFontSize(20);
  pdf.setFont('helvetica', 'bold');
  pdf.text('Grant Report', pageWidth / 2, 20, { align: 'center' });

  // Subtitle
  pdf.setFontSize(12);
  pdf.setFont('helvetica', 'normal');
  pdf.text(
    `Generated on ${new Date().toLocaleDateString()}`,
    pageWidth / 2,
    30,
    { align: 'center' }
  );
  pdf.text(`Total Grants: ${grants.length}`, pageWidth / 2, 38, {
    align: 'center',
  });

  // Summary statistics
  const summary = generateGrantSummary(grants);
  let yPosition = 50;

  pdf.setFontSize(14);
  pdf.setFont('helvetica', 'bold');
  pdf.text('Summary', 20, yPosition);
  yPosition += 10;

  pdf.setFontSize(10);
  pdf.setFont('helvetica', 'normal');

  Object.entries(summary).forEach(([key, value]) => {
    pdf.text(`${key}: ${value}`, 25, yPosition);
    yPosition += 6;
  });

  yPosition += 10;

  // Grants table
  const tableData = grants.map((grant) => [
    truncateText(grant.title || '', 30),
    grant.category || grant.identified_sector || '',
    truncateText(grant.funder_name || '', 20),
    formatDate(grant.deadline || grant.deadline_date),
    grant.funding_amount_display || '',
    `${grant.overall_composite_score || grant.relevanceScore || 0}%`,
  ]);

  pdf.autoTable({
    head: [['Title', 'Category', 'Funder', 'Deadline', 'Funding', 'Score']],
    body: tableData,
    startY: yPosition,
    styles: { fontSize: 8 },
    headStyles: { fillColor: [41, 128, 185] },
    columnStyles: {
      0: { cellWidth: 45 }, // Title
      1: { cellWidth: 25 }, // Category
      2: { cellWidth: 35 }, // Funder
      3: { cellWidth: 25 }, // Deadline
      4: { cellWidth: 25 }, // Funding
      5: { cellWidth: 20 }, // Score
    },
  });

  // Individual grant details (if requested)
  if (options.includeDetails && grants.length <= 10) {
    grants.forEach((grant, index) => {
      pdf.addPage();
      generateGrantDetailPage(pdf, grant, index + 1);
    });
  }

  pdf.save(filename);
};

/**
 * Export grant deadlines to iCal format
 * @param {Array} grants - Array of grant objects
 * @param {string} filename - Filename for the export
 */
export const exportToCalendar = (grants, filename = 'grant_deadlines.ics') => {
  const icsContent = generateICSContent(grants);
  const blob = new Blob([icsContent], { type: 'text/calendar;charset=utf-8;' });
  saveAs(blob, filename);
};

/**
 * Copy grant information to clipboard
 * @param {Array} grants - Array of grant objects
 * @param {string} format - Format: 'text', 'markdown', 'html'
 */
export const copyToClipboard = async (grants, format = 'text') => {
  let content;

  switch (format) {
    case 'markdown':
      content = generateMarkdownContent(grants);
      break;
    case 'html':
      content = generateHTMLContent(grants);
      break;
    default:
      content = generateTextContent(grants);
  }

  try {
    await navigator.clipboard.writeText(content);
    return true;
  } catch (err) {
    console.error('Failed to copy to clipboard:', err);
    return false;
  }
};

// Helper functions
const generateGrantSummary = (grants) => {
  const categories = grants.reduce((acc, grant) => {
    const category = grant.category || grant.identified_sector || 'Other';
    acc[category] = (acc[category] || 0) + 1;
    return acc;
  }, {});

  const upcomingDeadlines = grants.filter((grant) => {
    if (!grant.deadline && !grant.deadline_date) return false;
    const deadline = new Date(grant.deadline || grant.deadline_date);
    const daysToDeadline = Math.ceil(
      (deadline - new Date()) / (1000 * 60 * 60 * 24)
    );
    return daysToDeadline > 0 && daysToDeadline <= 30;
  }).length;

  const avgScore =
    grants.reduce(
      (sum, grant) =>
        sum + (grant.overall_composite_score || grant.relevanceScore || 0),
      0
    ) / grants.length;

  return {
    'Total Grants': grants.length,
    Categories: Object.keys(categories).length,
    'Upcoming Deadlines (30 days)': upcomingDeadlines,
    'Average Relevance Score': `${(avgScore || 0).toFixed(1)}%`,
    'Top Category':
      Object.entries(categories).sort(([, a], [, b]) => b - a)[0]?.[0] || 'N/A',
  };
};

const generateGrantDetailPage = (pdf, grant, pageNumber) => {
  let yPosition = 20;
  const pageWidth = pdf.internal.pageSize.width;

  pdf.setFontSize(16);
  pdf.setFont('helvetica', 'bold');
  pdf.text(`Grant ${pageNumber}: ${grant.title || 'Untitled'}`, 20, yPosition);
  yPosition += 15;

  pdf.setFontSize(12);
  pdf.setFont('helvetica', 'normal');

  const details = [
    ['Funder', grant.funder_name || 'Not specified'],
    ['Category', grant.category || grant.identified_sector || 'Not specified'],
    [
      'Deadline',
      formatDate(grant.deadline || grant.deadline_date) || 'Not specified',
    ],
    ['Funding Amount', grant.funding_amount_display || 'Not specified'],
    [
      'Relevance Score',
      `${grant.overall_composite_score || grant.relevanceScore || 0}%`,
    ],
    ['Geographic Scope', grant.geographic_scope || 'Not specified'],
  ];

  details.forEach(([label, value]) => {
    pdf.setFont('helvetica', 'bold');
    pdf.text(`${label}:`, 20, yPosition);
    pdf.setFont('helvetica', 'normal');
    pdf.text(value, 60, yPosition);
    yPosition += 8;
  });

  yPosition += 5;

  if (grant.description) {
    pdf.setFont('helvetica', 'bold');
    pdf.text('Description:', 20, yPosition);
    yPosition += 8;

    pdf.setFont('helvetica', 'normal');
    const splitDescription = pdf.splitTextToSize(
      grant.description,
      pageWidth - 40
    );
    pdf.text(splitDescription, 20, yPosition);
    yPosition += splitDescription.length * 5;
  }

  if (grant.keywords && grant.keywords.length > 0) {
    yPosition += 5;
    pdf.setFont('helvetica', 'bold');
    pdf.text('Keywords:', 20, yPosition);
    yPosition += 8;

    pdf.setFont('helvetica', 'normal');
    pdf.text(grant.keywords.join(', '), 20, yPosition);
  }
};

const generateICSContent = (grants) => {
  const now = new Date();
  const icsEvents = grants
    .filter((grant) => grant.deadline || grant.deadline_date)
    .map((grant) => {
      const deadline = new Date(grant.deadline || grant.deadline_date);
      const eventDate = formatICSDate(deadline);
      const eventId = `grant-${grant.id}-${deadline.getTime()}`;

      return [
        'BEGIN:VEVENT',
        `UID:${eventId}`,
        `DTSTAMP:${formatICSDate(now)}`,
        `DTSTART;VALUE=DATE:${eventDate}`,
        `SUMMARY:Grant Deadline: ${grant.title || 'Untitled Grant'}`,
        `DESCRIPTION:Funder: ${
          grant.funder_name || 'Not specified'
        }\\nAmount: ${
          grant.funding_amount_display || 'Not specified'
        }\\nScore: ${
          grant.overall_composite_score || grant.relevanceScore || 0
        }%`,
        'END:VEVENT',
      ].join('\n');
    });

  return [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//Smart Grant Finder//Grant Deadlines//EN',
    ...icsEvents,
    'END:VCALENDAR',
  ].join('\n');
};

const generateMarkdownContent = (grants) => {
  const content = [
    '# Grant Export Report',
    `Generated on ${new Date().toLocaleDateString()}`,
    `Total Grants: ${grants.length}`,
    '',
    '## Grants',
    '',
  ];

  grants.forEach((grant, index) => {
    content.push(`### ${index + 1}. ${grant.title || 'Untitled'}`);
    content.push(`- **Funder:** ${grant.funder_name || 'Not specified'}`);
    content.push(
      `- **Category:** ${
        grant.category || grant.identified_sector || 'Not specified'
      }`
    );
    content.push(
      `- **Deadline:** ${
        formatDate(grant.deadline || grant.deadline_date) || 'Not specified'
      }`
    );
    content.push(
      `- **Funding:** ${grant.funding_amount_display || 'Not specified'}`
    );
    content.push(
      `- **Score:** ${
        grant.overall_composite_score || grant.relevanceScore || 0
      }%`
    );
    if (grant.description) {
      content.push(`- **Description:** ${grant.description}`);
    }
    content.push('');
  });

  return content.join('\n');
};

const generateHTMLContent = (grants) => {
  const summaryStats = generateGrantSummary(grants);

  let html = `
    <h1>Grant Export Report</h1>
    <p>Generated on ${new Date().toLocaleDateString()}</p>
    
    <h2>Summary</h2>
    <ul>
  `;

  Object.entries(summaryStats).forEach(([key, value]) => {
    html += `<li><strong>${key}:</strong> ${value}</li>`;
  });

  html += `
    </ul>
    
    <h2>Grants</h2>
    <table border="1" style="border-collapse: collapse; width: 100%;">
      <thead>
        <tr>
          <th>Title</th>
          <th>Category</th>
          <th>Funder</th>
          <th>Deadline</th>
          <th>Funding</th>
          <th>Score</th>
        </tr>
      </thead>
      <tbody>
  `;

  grants.forEach((grant) => {
    html += `
      <tr>
        <td>${grant.title || 'Untitled'}</td>
        <td>${grant.category || grant.identified_sector || 'Not specified'}</td>
        <td>${grant.funder_name || 'Not specified'}</td>
        <td>${
          formatDate(grant.deadline || grant.deadline_date) || 'Not specified'
        }</td>
        <td>${grant.funding_amount_display || 'Not specified'}</td>
        <td>${grant.overall_composite_score || grant.relevanceScore || 0}%</td>
      </tr>
    `;
  });

  html += `
      </tbody>
    </table>
  `;

  return html;
};

const generateTextContent = (grants) => {
  const content = [
    'GRANT EXPORT REPORT',
    '===================',
    `Generated on ${new Date().toLocaleDateString()}`,
    `Total Grants: ${grants.length}`,
    '',
    'GRANTS',
    '------',
    '',
  ];

  grants.forEach((grant, index) => {
    content.push(`${index + 1}. ${grant.title || 'Untitled'}`);
    content.push(`   Funder: ${grant.funder_name || 'Not specified'}`);
    content.push(
      `   Category: ${
        grant.category || grant.identified_sector || 'Not specified'
      }`
    );
    content.push(
      `   Deadline: ${
        formatDate(grant.deadline || grant.deadline_date) || 'Not specified'
      }`
    );
    content.push(
      `   Funding: ${grant.funding_amount_display || 'Not specified'}`
    );
    content.push(
      `   Score: ${grant.overall_composite_score || grant.relevanceScore || 0}%`
    );
    content.push('');
  });

  return content.join('\n');
};

// Utility functions
const truncateText = (text, maxLength) => {
  return text.length > maxLength
    ? text.substring(0, maxLength - 3) + '...'
    : text;
};

const formatDate = (dateString) => {
  if (!dateString) return null;
  try {
    return new Date(dateString).toLocaleDateString();
  } catch {
    return dateString;
  }
};

const formatICSDate = (date) => {
  return date
    .toISOString()
    .replace(/[-:]/g, '')
    .replace(/\.\d{3}/, '');
};

const exportUtils = {
  exportToCSV,
  exportToPDF,
  exportToCalendar,
  copyToClipboard,
};

export default exportUtils;
