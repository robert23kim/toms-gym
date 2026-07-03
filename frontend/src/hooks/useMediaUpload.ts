// Shared file-selection state for the upload pages (golf scorecards, bowling
// and lifting videos): input + drag-drop handlers, type/size validation, and
// object-URL preview lifecycle.
import { useState } from "react";
import type { ChangeEvent, DragEvent } from "react";

interface UseMediaUploadOptions {
  accept: "image" | "video";
  maxBytes: number;
}

export function useMediaUpload({ accept, maxBytes }: UseMediaUploadOptions) {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const label = accept === "image" ? "Image" : "Video";

  const takeFile = (candidate: File | null | undefined) => {
    if (!candidate) return;
    if (!candidate.type.startsWith(`${accept}/`)) {
      setError(`Please choose ${accept === "image" ? "an image" : "a video"} file`);
      return;
    }
    if (candidate.size > maxBytes) {
      setError(`${label} must be under ${Math.round(maxBytes / (1024 * 1024))}MB`);
      return;
    }
    setFile(candidate);
    setPreviewUrl((old) => {
      if (old) URL.revokeObjectURL(old);
      return URL.createObjectURL(candidate);
    });
    setError(null);
  };

  const onInputChange = (e: ChangeEvent<HTMLInputElement>) => takeFile(e.target.files?.[0]);

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    takeFile(e.dataTransfer.files?.[0]);
  };

  const onDragOver = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const onDragLeave = () => setIsDragging(false);

  return {
    file,
    previewUrl,
    isDragging,
    error,
    setError,
    onInputChange,
    onDrop,
    onDragOver,
    onDragLeave,
  };
}
