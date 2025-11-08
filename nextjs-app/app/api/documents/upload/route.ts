import { auth } from '@/auth';
import { R2StorageService } from '@/lib/services/r2-storage';
import { NextResponse } from 'next/server';
import { DocumentType } from '@prisma/client';

export async function POST(req: Request) {
  try {
    const session = await auth();

    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const formData = await req.formData();
    const file = formData.get('file') as File;
    const documentType = (formData.get('type') as DocumentType) || 'OTHER';

    if (!file) {
      return NextResponse.json({ error: 'No file provided' }, { status: 400 });
    }

    // Convert File to Buffer
    const bytes = await file.arrayBuffer();
    const buffer = Buffer.from(bytes);

    const result = await R2StorageService.upload({
      userId: session.user.id,
      file: buffer,
      filename: file.name,
      mimeType: file.type,
      documentType,
    });

    return NextResponse.json(result);
  } catch (error) {
    console.error('Upload error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Upload failed' },
      { status: 500 }
    );
  }
}
