export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  // Image-specific
  image_width: number | null;
  image_height: number | null;
  exif: Record<string, string> | null;
  // PDF-specific
  pdf_pages: number | null;
  pdf_author: string | null;
  pdf_title: string | null;
  // Audio/Video
  duration_seconds: number | null;
  codec: string | null;
  bitrate: number | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// --- Call analytics domain ---

export type CallQueue =
  | "sales"
  | "support"
  | "billing"
  | "retention"
  | "collections";
export type SpeakerCount = "2" | "3" | "auto";
export type AsrQuality = "fast" | "accurate";
export type CallStatus = "uploaded" | "processing" | "done" | "error";

export interface Call {
  call_id: string;
  title: string;
  queue: CallQueue;
  date: string;
  language: string;
  expected_speakers: SpeakerCount;
  asr_quality: AsrQuality;
  agent_label: string;
  customer_label: string;
  compliance_keywords: string[];
  notes: string;
  status: CallStatus;
  recording_key: string;
  recording_filename: string;
  duration_sec: number | null;
  num_speakers: number | null;
  sentiment_label: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface TranscriptSegment {
  start: number;
  end: number;
  speaker: string;
  text: string;
  emotion: string | null;
}

export interface FlaggedPhrase {
  phrase: string;
  count: number;
}

export interface CallAnalytics {
  num_speakers: number;
  duration_sec: number;
  sentiment_score: number;
  sentiment_label: string;
  silence_ratio: number;
  talk_time: Record<string, number>;
  flagged_phrases: FlaggedPhrase[];
  emotions: Record<string, number>;
}

export interface CallStats {
  total_calls: number;
  calls_done: number;
  calls_processing: number;
  audio_hours: number;
  artifacts_written: number;
  fan_out_ratio: number;
  avg_sentiment: number | null;
  queue_breakdown: Record<string, number>;
}

export interface CreateCallInput {
  file: File;
  title: string;
  queue: CallQueue;
  date: string;
  expected_speakers: SpeakerCount;
  asr_quality: AsrQuality;
  agent_label: string;
  customer_label: string;
  compliance_keywords: string;
  notes: string;
  analyze: boolean;
}

export interface UpdateCallInput {
  title?: string;
  language?: string;
  expected_speakers?: SpeakerCount;
  asr_quality?: AsrQuality;
  agent_label?: string;
  customer_label?: string;
  compliance_keywords?: string[];
  notes?: string;
}
