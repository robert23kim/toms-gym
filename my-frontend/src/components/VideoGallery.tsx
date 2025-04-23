import React from 'react';
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
            to={`/video-player/${video.competition_id}/${video.user_id || userId}/${video.attempt_id}`}
            className="bg-background rounded-lg overflow-hidden transition-all hover:scale-[1.02] focus:scale-[1.02] shadow-sm"
          >
            <div className="aspect-video bg-muted relative">
              <div className="absolute inset-0 flex items-center justify-center">
                <Play className="w-12 h-12 text-accent/75" />
              </div>
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