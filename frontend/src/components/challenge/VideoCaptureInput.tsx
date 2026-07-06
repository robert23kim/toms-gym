import React from "react";
import { Video, FolderOpen } from "lucide-react";

interface Props {
  selectedFileName: string | null;
  onFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

/**
 * Two-affordance video picker: "Record now" opens the phone camera directly
 * (capture attr — no external Camera app + file hunt); "Choose existing"
 * keeps the standard picker. Desktop degrades to a file dialog for both.
 */
const VideoCaptureInput: React.FC<Props> = ({ selectedFileName, onFileSelect }) => (
  <div className="border-2 border-dashed border-input rounded-lg p-4 text-center hover:border-primary/50 transition-colors">
    <input
      type="file"
      accept="video/*"
      capture="environment"
      onChange={onFileSelect}
      className="hidden"
      id="challenge-video-camera"
    />
    <input
      type="file"
      accept="video/*"
      onChange={onFileSelect}
      className="hidden"
      id="challenge-video-upload"
    />
    <div className="flex gap-3 justify-center flex-wrap">
      <label
        htmlFor="challenge-video-camera"
        className="cursor-pointer inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm"
      >
        <Video className="w-4 h-4" />
        Record now
      </label>
      <label
        htmlFor="challenge-video-upload"
        className="cursor-pointer inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-input text-sm"
      >
        <FolderOpen className="w-4 h-4" />
        Choose existing video
      </label>
    </div>
    {selectedFileName && (
      <p className="text-sm text-muted-foreground mt-3">{selectedFileName}</p>
    )}
  </div>
);

export default VideoCaptureInput;
