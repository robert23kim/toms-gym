import React, { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Play } from 'lucide-react';

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
}

// Component for individual video thumbnail
const VideoThumbnail: React.FC<{ videoUrl: string }> = ({ videoUrl }) => {
  const [thumbnail, setThumbnail] = useState<string | null>(null);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);
  const loadingRef = useRef(true);

  useEffect(() => {
    loadingRef.current = true;
    setLoading(true);
    setError(false);
    setThumbnail(null);

    const video = document.createElement('video');
    video.crossOrigin = 'anonymous';
    video.muted = true;
    video.playsInline = true;
    
    const handleLoadedData = () => {
      // Seek to 0.5 seconds to get a better frame (avoids black frames at start)
      video.currentTime = 0.5;
    };

    const handleSeeked = () => {
      try {
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 360;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
          const dataUrl = canvas.toDataURL('image/jpeg', 0.7);
          setThumbnail(dataUrl);
        }
      } catch (e) {
        console.warn('Failed to generate thumbnail:', e);
        setError(true);
      } finally {
        loadingRef.current = false;
        setLoading(false);
        // Clean up
        video.src = '';
        video.load();
      }
    };

    const handleError = () => {
      console.warn('Failed to load video for thumbnail:', videoUrl);
      setError(true);
      loadingRef.current = false;
      setLoading(false);
    };

    video.addEventListener('loadeddata', handleLoadedData);
    video.addEventListener('seeked', handleSeeked);
    video.addEventListener('error', handleError);

    // Set a timeout to avoid hanging forever
    const timeout = setTimeout(() => {
      if (loadingRef.current) {
        setError(true);
        setLoading(false);
        loadingRef.current = false;
      }
    }, 10000);

    video.src = videoUrl;
    video.load();

    return () => {
      clearTimeout(timeout);
      video.removeEventListener('loadeddata', handleLoadedData);
      video.removeEventListener('seeked', handleSeeked);
      video.removeEventListener('error', handleError);
      video.src = '';
      loadingRef.current = false;
    };
  }, [videoUrl]);

  if (loading) {
    return (
      <div className="absolute inset-0 flex items-center justify-center bg-muted animate-pulse">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !thumbnail) {
    return (
      <div className="absolute inset-0 flex items-center justify-center bg-muted">
        <Play className="w-12 h-12 text-accent/75" />
      </div>
    );
  }

  return (
    <>
      <img 
        src={thumbnail} 
        alt="Video thumbnail" 
        className="absolute inset-0 w-full h-full object-cover"
      />
      <div className="absolute inset-0 flex items-center justify-center bg-black/20 hover:bg-black/30 transition-colors">
        <div className="w-14 h-14 rounded-full bg-white/90 flex items-center justify-center shadow-lg">
          <Play className="w-7 h-7 text-primary ml-1" fill="currentColor" />
        </div>
      </div>
    </>
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
}) => {
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
      
      <div className={gridClassName}>
        {videos.slice(0, maxVideos).map((video) => (
          <Link 
            key={video.attempt_id}
            to={`/challenges/${video.competition_id}/participants/${video.user_id || userId}/video/${video.attempt_id}`}
            className="bg-background rounded-lg overflow-hidden transition-all hover:scale-[1.02] focus:scale-[1.02] shadow-sm"
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
        ))}
      </div>
    </div>
  );
};

export default VideoGallery; 