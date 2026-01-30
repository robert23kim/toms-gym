import React, { useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Play, Trash2, X } from 'lucide-react';
import axios from 'axios';
import { API_URL } from '../config';

interface Video {
  attempt_id: string;
  user_id?: string;
  lift_type: string;
  weight: number;
  status: string;
  created_at: string;
  video_url: string;
  competition_id: string;
  competition_name?: string;
}

interface VideoGalleryProps {
  videos: Video[];
  title?: string;
  emptyMessage?: string;
  maxVideos?: number;
  showCompetitionName?: boolean;
  containerClassName?: string;
  gridClassName?: string;
  userId?: string;
  onVideoDeleted?: () => void;
  showDeleteButton?: boolean;
}

// Component for individual video thumbnail using native video element
const VideoThumbnail: React.FC<{ videoUrl: string }> = ({ videoUrl }) => {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);

  const handleLoadedData = () => {
    setLoaded(true);
    // Seek to 0.5 seconds for a better frame
    if (videoRef.current) {
      videoRef.current.currentTime = 0.5;
    }
  };

  const handleError = () => {
    console.warn('Failed to load video for thumbnail:', videoUrl);
    setError(true);
  };

  if (error) {
    return (
      <div className="absolute inset-0 flex items-center justify-center bg-muted">
        <Play className="w-12 h-12 text-accent/75" />
      </div>
    );
  }

  return (
    <>
      {/* Loading state */}
      {!loaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-muted">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      )}
      
      {/* Video element as thumbnail */}
      <video
        ref={videoRef}
        src={videoUrl}
        muted
        playsInline
        preload="metadata"
        onLoadedData={handleLoadedData}
        onError={handleError}
        className={`absolute inset-0 w-full h-full object-cover ${loaded ? 'opacity-100' : 'opacity-0'}`}
      />
      
      {/* Play button overlay */}
      {loaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/20 hover:bg-black/30 transition-colors">
          <div className="w-14 h-14 rounded-full bg-white/90 flex items-center justify-center shadow-lg">
            <Play className="w-7 h-7 text-primary ml-1" fill="currentColor" />
          </div>
        </div>
      )}
    </>
  );
};

// Delete confirmation modal component
const DeleteConfirmModal: React.FC<{
  isOpen: boolean;
  videoName: string;
  onConfirm: () => void;
  onCancel: () => void;
  isDeleting: boolean;
}> = ({ isOpen, videoName, onConfirm, onCancel, isDeleting }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onCancel} />
      <div className="relative bg-card rounded-lg p-6 max-w-md w-full mx-4 shadow-xl">
        <button
          onClick={onCancel}
          className="absolute top-4 right-4 text-muted-foreground hover:text-foreground"
        >
          <X className="w-5 h-5" />
        </button>
        <h3 className="text-lg font-semibold mb-2">Delete Video</h3>
        <p className="text-muted-foreground mb-6">
          Are you sure you want to delete <span className="font-medium text-foreground">{videoName}</span>? This action cannot be undone.
        </p>
        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            disabled={isDeleting}
            className="px-4 py-2 rounded-lg border border-input hover:bg-secondary transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isDeleting}
            className="px-4 py-2 rounded-lg bg-red-500 text-white hover:bg-red-600 transition-colors disabled:opacity-50"
          >
            {isDeleting ? 'Deleting...' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  );
};

const VideoGallery: React.FC<VideoGalleryProps> = ({
  videos,
  title,
  emptyMessage = "No videos available",
  maxVideos = 6,
  showCompetitionName = true,
  containerClassName = "",
  gridClassName = "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4",
  userId,
  onVideoDeleted,
  showDeleteButton = true,
}) => {
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [videoToDelete, setVideoToDelete] = useState<Video | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handleDeleteClick = (e: React.MouseEvent, video: Video) => {
    e.preventDefault();
    e.stopPropagation();
    setVideoToDelete(video);
    setDeleteModalOpen(true);
    setDeleteError(null);
  };

  const handleDeleteConfirm = async () => {
    if (!videoToDelete) return;

    setIsDeleting(true);
    setDeleteError(null);

    try {
      await axios.delete(`${API_URL}/attempts/${videoToDelete.attempt_id}`);
      setDeleteModalOpen(false);
      setVideoToDelete(null);
      if (onVideoDeleted) {
        onVideoDeleted();
      }
    } catch (error: any) {
      console.error('Error deleting video:', error);
      setDeleteError(error.response?.data?.error || 'Failed to delete video. Please try again.');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteModalOpen(false);
    setVideoToDelete(null);
    setDeleteError(null);
  };

  if (videos.length === 0) {
    return (
      <div className={`text-center py-6 ${containerClassName}`}>
        <p className="text-muted-foreground">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className={containerClassName}>
      {title && (
        <h2 className="text-xl font-semibold mb-4">{title}</h2>
      )}
      
      {deleteError && (
        <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-500 text-sm">
          {deleteError}
        </div>
      )}
      
      <div className={gridClassName}>
        {videos.slice(0, maxVideos).map((video) => (
          <div key={video.attempt_id} className="relative group">
            <Link 
              to={`/challenges/${video.competition_id}/participants/${video.user_id || userId}/video/${video.attempt_id}`}
              className="block bg-background rounded-lg overflow-hidden transition-all hover:scale-[1.02] focus:scale-[1.02] shadow-sm"
            >
              <div className="aspect-video bg-muted relative overflow-hidden">
                <VideoThumbnail videoUrl={video.video_url} />
              </div>
              <div className="p-3">
                <h3 className="font-medium">{video.lift_type} - {video.weight}kg</h3>
                <p className="text-sm text-muted-foreground">
                  {new Date(video.created_at).toLocaleDateString()}
                  {showCompetitionName && video.competition_name && ` • ${video.competition_name}`}
                </p>
                <span className={`mt-2 inline-block px-2 py-0.5 rounded-full text-xs ${
                  video.status === 'completed' ? 'bg-green-100 text-green-800' : 
                  video.status === 'failed' ? 'bg-red-100 text-red-800' : 
                  'bg-gray-100 text-gray-800'
                }`}>
                  {video.status}
                </span>
              </div>
            </Link>
            
            {/* Delete button */}
            {showDeleteButton && (
              <button
                onClick={(e) => handleDeleteClick(e, video)}
                className="absolute top-2 right-2 p-2 bg-red-500/90 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-600 shadow-lg"
                title="Delete video"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Delete confirmation modal */}
      <DeleteConfirmModal
        isOpen={deleteModalOpen}
        videoName={videoToDelete ? `${videoToDelete.lift_type} - ${videoToDelete.weight}kg` : ''}
        onConfirm={handleDeleteConfirm}
        onCancel={handleDeleteCancel}
        isDeleting={isDeleting}
      />
    </div>
  );
};

export default VideoGallery; 