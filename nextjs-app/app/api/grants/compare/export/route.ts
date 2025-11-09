import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/auth';
import { prisma } from '@/lib/prisma';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

export async function POST(req: Request) {
  try {
    const session = await getServerSession(authOptions);

    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { grantIds } = await req.json();

    if (!Array.isArray(grantIds) || grantIds.length === 0) {
      return NextResponse.json(
        { error: 'Invalid grant IDs' },
        { status: 400 }
      );
    }

    // Fetch grants
    const grants = await prisma.grant.findMany({
      where: {
        id: { in: grantIds },
        search: {
          userId: session.user.id,
        },
      },
    });

    if (grants.length === 0) {
      return NextResponse.json({ error: 'No grants found' }, { status: 404 });
    }

    // Generate PDF
    const doc = new jsPDF('p', 'mm', 'a4');
    const pageWidth = doc.internal.pageSize.getWidth();

    // Title
    doc.setFontSize(20);
    doc.setFont('helvetica', 'bold');
    doc.text('Grant Comparison Report', pageWidth / 2, 20, { align: 'center' });

    // Date
    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    doc.text(
      `Generated on ${new Date().toLocaleDateString()}`,
      pageWidth / 2,
      28,
      { align: 'center' }
    );

    let yPos = 40;

    // For each grant
    grants.forEach((grant, index) => {
      if (yPos > 250) {
        doc.addPage();
        yPos = 20;
      }

      // Grant header
      doc.setFontSize(14);
      doc.setFont('helvetica', 'bold');
      doc.text(`${index + 1}. ${grant.title}`, 15, yPos);
      yPos += 7;

      doc.setFontSize(10);
      doc.setFont('helvetica', 'italic');
      doc.text(grant.organization, 15, yPos);
      yPos += 10;

      // Grant details table
      doc.setFont('helvetica', 'normal');
      const details = [
        ['Match Score', grant.score.toString()],
        [
          'Funding Amount',
          `$${(grant.amount as any).min.toLocaleString()} - $${(grant.amount as any).max.toLocaleString()}`,
        ],
        ['Deadline', new Date(grant.deadline).toLocaleDateString()],
        ['Grant Type', (grant.grantType as string[]).join(', ')],
        ['Geographic Focus', (grant.geographicFocus as string[]).join(', ')],
        ['Application URL', grant.applicationUrl],
      ];

      autoTable(doc, {
        startY: yPos,
        head: [],
        body: details,
        theme: 'plain',
        styles: { fontSize: 9, cellPadding: 2 },
        columnStyles: {
          0: { fontStyle: 'bold', cellWidth: 40 },
          1: { cellWidth: 'auto' },
        },
        margin: { left: 15, right: 15 },
      });

      yPos = (doc as any).lastAutoTable.finalY + 5;

      // Match Reason
      doc.setFontSize(9);
      doc.setFont('helvetica', 'bold');
      doc.text('Why It Matches:', 15, yPos);
      yPos += 5;

      doc.setFont('helvetica', 'normal');
      const matchReasonLines = doc.splitTextToSize(
        grant.matchReason,
        pageWidth - 30
      );
      doc.text(matchReasonLines, 15, yPos);
      yPos += matchReasonLines.length * 5 + 5;

      // Eligibility
      doc.setFont('helvetica', 'bold');
      doc.text('Eligibility:', 15, yPos);
      yPos += 5;

      doc.setFont('helvetica', 'normal');
      (grant.eligibility as string[]).forEach((item) => {
        if (yPos > 280) {
          doc.addPage();
          yPos = 20;
        }
        doc.text(`• ${item}`, 20, yPos);
        yPos += 5;
      });
      yPos += 3;

      // Requirements
      if (yPos > 250) {
        doc.addPage();
        yPos = 20;
      }

      doc.setFont('helvetica', 'bold');
      doc.text('Requirements:', 15, yPos);
      yPos += 5;

      doc.setFont('helvetica', 'normal');
      (grant.requirements as string[]).forEach((item) => {
        if (yPos > 280) {
          doc.addPage();
          yPos = 20;
        }
        doc.text(`• ${item}`, 20, yPos);
        yPos += 5;
      });

      yPos += 10;

      // Separator line
      if (index < grants.length - 1) {
        doc.setDrawColor(200);
        doc.line(15, yPos, pageWidth - 15, yPos);
        yPos += 10;
      }
    });

    // Generate PDF buffer
    const pdfBuffer = doc.output('arraybuffer');

    // Return PDF as response
    return new NextResponse(pdfBuffer, {
      headers: {
        'Content-Type': 'application/pdf',
        'Content-Disposition': `attachment; filename="grant-comparison-${Date.now()}.pdf"`,
      },
    });
  } catch (error) {
    console.error('Failed to generate PDF:', error);
    return NextResponse.json(
      { error: 'Failed to generate PDF' },
      { status: 500 }
    );
  }
}
