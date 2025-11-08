/**
 * Cloudflare R2 Storage Service
 * Document storage for user uploads (50MB max per file)
 */

import { S3Client, PutObjectCommand, GetObjectCommand, DeleteObjectCommand } from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';
import { APIUsageLog } from './cost-tracker';
import { prisma } from '@/lib/prisma';
import { DocumentType } from '@prisma/client';

const R2_ACCOUNT_ID = process.env.R2_ACCOUNT_ID || '';
const R2_ACCESS_KEY_ID = process.env.R2_ACCESS_KEY_ID || '';
const R2_SECRET_ACCESS_KEY = process.env.R2_SECRET_ACCESS_KEY || '';
const R2_BUCKET_NAME = process.env.R2_BUCKET_NAME || 'grant-finder-documents';
const R2_PUBLIC_URL = process.env.R2_PUBLIC_URL || '';

if (!R2_ACCOUNT_ID || !R2_ACCESS_KEY_ID || !R2_SECRET_ACCESS_KEY) {
  console.warn('R2 credentials not configured');
}

const r2Client = new S3Client({
  region: 'auto',
  endpoint: `https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
  credentials: {
    accessKeyId: R2_ACCESS_KEY_ID,
    secretAccessKey: R2_SECRET_ACCESS_KEY,
  },
});

export interface UploadOptions {
  userId: string;
  file: Buffer;
  filename: string;
  mimeType: string;
  documentType: DocumentType;
}

export interface UploadResult {
  id: string;
  url: string;
  key: string;
  size: number;
}

export class R2StorageService {
  private static readonly MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
  private static readonly ALLOWED_MIME_TYPES = [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'text/plain',
    'image/jpeg',
    'image/png',
  ];

  /**
   * Upload file to R2
   */
  static async upload(options: UploadOptions): Promise<UploadResult> {
    // Validate file size
    if (options.file.length > this.MAX_FILE_SIZE) {
      throw new Error(`File size exceeds maximum of 50MB`);
    }

    // Validate MIME type
    if (!this.ALLOWED_MIME_TYPES.includes(options.mimeType)) {
      throw new Error(`File type ${options.mimeType} is not allowed`);
    }

    // Generate unique key
    const timestamp = Date.now();
    const sanitizedFilename = options.filename.replace(/[^a-zA-Z0-9.-]/g, '_');
    const key = `${options.userId}/${timestamp}_${sanitizedFilename}`;

    const startTime = Date.now();

    try {
      // Upload to R2
      await r2Client.send(
        new PutObjectCommand({
          Bucket: R2_BUCKET_NAME,
          Key: key,
          Body: options.file,
          ContentType: options.mimeType,
          Metadata: {
            userId: options.userId,
            originalName: options.filename,
            documentType: options.documentType,
          },
        })
      );

      const url = `${R2_PUBLIC_URL}/${key}`;
      const duration = Date.now() - startTime;

      // Log usage (R2 is very cheap, approximate cost)
      await APIUsageLog.log({
        userId: options.userId,
        service: 'R2',
        operation: 'upload',
        costUSD: 0.00001, // Negligible cost
        duration,
        success: true,
        requestData: { filename: options.filename, size: options.file.length },
      });

      // Save to database
      const document = await prisma.document.create({
        data: {
          userId: options.userId,
          filename: sanitizedFilename,
          originalName: options.filename,
          fileType: options.documentType,
          mimeType: options.mimeType,
          size: options.file.length,
          r2Key: key,
          r2Url: url,
        },
      });

      return {
        id: document.id,
        url,
        key,
        size: options.file.length,
      };
    } catch (error) {
      const duration = Date.now() - startTime;

      await APIUsageLog.log({
        userId: options.userId,
        service: 'R2',
        operation: 'upload',
        costUSD: 0,
        duration,
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });

      throw error;
    }
  }

  /**
   * Get signed URL for private file access
   */
  static async getSignedUrl(key: string, expiresIn: number = 3600): Promise<string> {
    const command = new GetObjectCommand({
      Bucket: R2_BUCKET_NAME,
      Key: key,
    });

    return getSignedUrl(r2Client, command, { expiresIn });
  }

  /**
   * Delete file from R2
   */
  static async delete(key: string, userId?: string): Promise<void> {
    const startTime = Date.now();

    try {
      await r2Client.send(
        new DeleteObjectCommand({
          Bucket: R2_BUCKET_NAME,
          Key: key,
        })
      );

      const duration = Date.now() - startTime;

      await APIUsageLog.log({
        userId,
        service: 'R2',
        operation: 'delete',
        costUSD: 0.00001,
        duration,
        success: true,
      });

      // Delete from database
      await prisma.document.deleteMany({
        where: { r2Key: key },
      });
    } catch (error) {
      const duration = Date.now() - startTime;

      await APIUsageLog.log({
        userId,
        service: 'R2',
        operation: 'delete',
        costUSD: 0,
        duration,
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });

      throw error;
    }
  }

  /**
   * Get all documents for a user
   */
  static async getUserDocuments(userId: string) {
    return prisma.document.findMany({
      where: { userId },
      orderBy: { createdAt: 'desc' },
    });
  }

  /**
   * Get document by ID
   */
  static async getDocument(documentId: string, userId: string) {
    return prisma.document.findFirst({
      where: {
        id: documentId,
        userId, // Ensure user owns the document
      },
    });
  }

  /**
   * Mark document as processed
   */
  static async markAsProcessed(documentId: string, extractedData: any) {
    return prisma.document.update({
      where: { id: documentId },
      data: {
        isProcessed: true,
        extractedData,
      },
    });
  }
}

export default R2StorageService;
