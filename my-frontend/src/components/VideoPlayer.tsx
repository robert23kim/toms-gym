import React, { useState, useRef, useEffect } from "react";
import { Play, Pause, Volume2, VolumeX, Maximize, Minimize, SkipBack, SkipForward, MessageSquare, ThumbsUp, ThumbsDown, BarChart2, Activity, Target, Award } from "lucide-react";

interface VideoPlayerProps {
  videoUrl: string;
  title: string;
  onNextVideo?: () => void;
}

interface Comment {
  id: number;
  user: string;
  avatar: string;
  content: string;
  timestamp: string;
  likes: number;
  dislikes: number;
}

const mockComments: Comment[] = [
  {
    id: 1,
    user: "John Smith",
    avatar: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=100&h=100&fit=crop",
    content: "Great form on that squat! The depth was perfect.",
    timestamp: "2 hours ago",
    likes: 12,
    dislikes: 0
  },
  {
    id: 2,
    user: "Sarah Johnson",
    avatar: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&h=100&fit=crop",
    content: "The bar path was a bit forward on the way up. Try to keep it more vertical.",
    timestamp: "1 hour ago",
    likes: 8,
    dislikes: 2
  },
  {
    id: 3,
    user: "Mike Wilson",
    avatar: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&h=100&fit=crop",
    content: "Impressive weight! What's your training program like?",
    timestamp: "30 minutes ago",
    likes: 15,
    dislikes: 0
  }
];

const VideoPlayer: React.FC<VideoPlayerProps> = ({ videoUrl, title, onNextVideo }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isControlsVisible, setIsControlsVisible] = useState(true);
  const [isLoading, setIsLoading] = useState(true);
  const controlsTimeoutRef = useRef<number | null>(null);
  const [comments] = useState<Comment[]>(mockComments);
  const [newComment, setNewComment] = useState("");

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const onLoadedMetadata = () => {
      setDuration(video.duration);
      setIsLoading(false);
    };

    const onTimeUpdate = () => {
      setCurrentTime(video.currentTime);
      setProgress((video.currentTime / video.duration) * 100);
    };

    video.addEventListener("loadedmetadata", onLoadedMetadata);
    video.addEventListener("timeupdate", onTimeUpdate);
    video.addEventListener("ended", () => setIsPlaying(false));

    document.addEventListener("fullscreenchange", handleFullscreenChange);

    return () => {
      video.removeEventListener("loadedmetadata", onLoadedMetadata);
      video.removeEventListener("timeupdate", onTimeUpdate);
      video.removeEventListener("ended", () => setIsPlaying(false));
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
      
      if (controlsTimeoutRef.current) {
        clearTimeout(controlsTimeoutRef.current);
      }
    };
  }, []);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    if (isPlaying) {
      video.play().catch((error) => {
        console.error("Error playing video:", error);
        setIsPlaying(false);
      });
    } else {
      video.pause();
    }
  }, [isPlaying]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    video.volume = volume;
    video.muted = isMuted;
  }, [volume, isMuted]);

  const handleFullscreenChange = () => {
    setIsFullscreen(!!document.fullscreenElement);
  };

  const togglePlay = () => {
    setIsPlaying(!isPlaying);
  };

  const handleProgressChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseFloat(e.target.value);
    setProgress(value);
    if (videoRef.current) {
      videoRef.current.currentTime = (value / 100) * duration;
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseFloat(e.target.value);
    setVolume(value);
    setIsMuted(value === 0);
  };

  const toggleMute = () => {
    setIsMuted(!isMuted);
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs < 10 ? "0" : ""}${secs}`;
  };

  const showControls = () => {
    setIsControlsVisible(true);
    if (controlsTimeoutRef.current) {
      clearTimeout(controlsTimeoutRef.current);
    }
    
    if (isPlaying) {
      controlsTimeoutRef.current = window.setTimeout(() => {
        setIsControlsVisible(false);
      }, 3000);
    }
  };

  const skipBackward = () => {
    if (videoRef.current) {
      videoRef.current.currentTime = Math.max(0, videoRef.current.currentTime - 10);
    }
  };

  const skipForward = () => {
    if (videoRef.current) {
      videoRef.current.currentTime = Math.min(
        duration,
        videoRef.current.currentTime + 10
      );
    }
  };

  const handleCommentSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newComment.trim()) return;
    
    // Here you would typically send the comment to your backend
    console.log("New comment:", newComment);
    setNewComment("");
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2">
        <div className="bg-card rounded-lg shadow-lg overflow-hidden">
          <div 
            className="relative aspect-video bg-black group"
            onMouseMove={showControls}
            onMouseLeave={() => isPlaying && setIsControlsVisible(false)}
          >
            {isLoading && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/10">
                <div className="w-12 h-12 border-4 border-t-accent border-opacity-50 rounded-full animate-spin"></div>
              </div>
            )}
            
            <video
              ref={videoRef}
              src={videoUrl}
              className="w-full h-full object-contain"
              onClick={togglePlay}
              playsInline
            />
            
            {/* Play/Pause Overlay */}
            <div 
              className={`absolute inset-0 flex items-center justify-center transition-opacity duration-300 ${
                isPlaying && !isControlsVisible ? "opacity-0" : "opacity-100"
              }`}
            >
              <button
                onClick={togglePlay}
                className="w-16 h-16 flex items-center justify-center rounded-full bg-black/30 backdrop-blur-sm text-white hover:bg-black/50 transition-colors"
              >
                {isPlaying ? <Pause size={32} /> : <Play size={32} />}
              </button>
            </div>

            {/* Next Video Overlay */}
            {onNextVideo && (
              <div 
                className={`absolute right-4 top-1/2 -translate-y-1/2 transition-opacity duration-300 ${
                  (isControlsVisible || !isPlaying) ? "opacity-100" : "opacity-0"
                } group-hover:opacity-100`}
              >
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onNextVideo();
                  }}
                  className="w-12 h-12 flex items-center justify-center rounded-full bg-black/30 backdrop-blur-sm text-white hover:bg-black/50 transition-colors"
                >
                  <SkipForward size={24} />
                </button>
              </div>
            )}
            
            {/* Video Controls */}
            <div 
              className={`absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/80 to-transparent transition-opacity duration-300 ${
                isPlaying && !isControlsVisible ? "opacity-0" : "opacity-100"
              }`}
            >
              <div className="mb-2">
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={progress}
                  onChange={handleProgressChange}
                  className="w-full h-1 bg-white/20 rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-accent"
                />
              </div>
              
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <button
                    onClick={togglePlay}
                    className="text-white hover:text-accent transition-colors"
                  >
                    {isPlaying ? <Pause size={20} /> : <Play size={20} />}
                  </button>
                  
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={skipBackward}
                      className="text-white hover:text-accent transition-colors"
                    >
                      <SkipBack size={20} />
                    </button>
                    <button
                      onClick={skipForward}
                      className="text-white hover:text-accent transition-colors"
                    >
                      <SkipForward size={20} />
                    </button>
                  </div>
                  
                  <div className="text-sm text-white">
                    {formatTime(currentTime)} / {formatTime(duration)}
                  </div>
                </div>
                
                <div className="flex items-center space-x-2">
                  <div className="flex items-center space-x-1">
                    <button
                      onClick={toggleMute}
                      className="text-white hover:text-accent transition-colors"
                    >
                      {isMuted ? <VolumeX size={20} /> : <Volume2 size={20} />}
                    </button>
                    
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.01"
                      value={isMuted ? 0 : volume}
                      onChange={handleVolumeChange}
                      className="w-20 h-1 bg-white/20 rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:h-2 [&::-webkit-slider-thumb]:w-2 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-white"
                    />
                  </div>
                  
                  <button
                    onClick={toggleFullscreen}
                    className="text-white hover:text-accent transition-colors"
                  >
                    {isFullscreen ? <Minimize size={20} /> : <Maximize size={20} />}
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Comments Section */}
          <div className="p-6 border-t border-border">
            <div className="flex items-center gap-2 mb-6">
              <MessageSquare className="text-primary" size={24} />
              <h2 className="text-xl font-semibold">Comments</h2>
            </div>

            {/* Comment Form */}
            <form onSubmit={handleCommentSubmit} className="mb-8">
              <div className="flex gap-4">
                <div className="flex-1">
                  <input
                    type="text"
                    value={newComment}
                    onChange={(e) => setNewComment(e.target.value)}
                    placeholder="Add a comment..."
                    className="w-full px-4 py-2 rounded-lg border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
                  />
                </div>
                <button
                  type="submit"
                  className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors"
                >
                  Post
                </button>
              </div>
            </form>

            {/* Comments List */}
            <div className="space-y-6">
              {comments.map((comment) => (
                <div key={comment.id} className="flex gap-4">
                  <img
                    src={comment.avatar}
                    alt={comment.user}
                    className="w-10 h-10 rounded-full"
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium">{comment.user}</span>
                      <span className="text-sm text-muted-foreground">{comment.timestamp}</span>
                    </div>
                    <p className="text-muted-foreground mb-2">{comment.content}</p>
                    <div className="flex items-center gap-4">
                      <button className="flex items-center gap-1 text-muted-foreground hover:text-primary">
                        <ThumbsUp size={16} />
                        <span className="text-sm">{comment.likes}</span>
                      </button>
                      <button className="flex items-center gap-1 text-muted-foreground hover:text-red-500">
                        <ThumbsDown size={16} />
                        <span className="text-sm">{comment.dislikes}</span>
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Analytics Panel */}
      <div className="lg:col-span-1">
        <div className="bg-card rounded-lg shadow-lg overflow-hidden">
          <div className="p-6">
            <div className="flex items-center gap-2 mb-6">
              <BarChart2 className="text-primary" size={24} />
              <h2 className="text-xl font-semibold">Lift Analytics</h2>
            </div>

            <div className="space-y-6">
              {/* Performance Metrics */}
              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-3">Performance Metrics</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-secondary/5 p-4 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <Activity className="w-4 h-4 text-primary" />
                      <span className="text-sm font-medium">Depth</span>
                    </div>
                    <div className="text-2xl font-bold">95%</div>
                  </div>
                  <div className="bg-secondary/5 p-4 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <Target className="w-4 h-4 text-primary" />
                      <span className="text-sm font-medium">Speed</span>
                    </div>
                    <div className="text-2xl font-bold">0.8s</div>
                  </div>
                  <div className="bg-secondary/5 p-4 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <Award className="w-4 h-4 text-primary" />
                      <span className="text-sm font-medium">Form</span>
                    </div>
                    <div className="text-2xl font-bold">92%</div>
                  </div>
                  <div className="bg-secondary/5 p-4 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <BarChart2 className="w-4 h-4 text-primary" />
                      <span className="text-sm font-medium">Power</span>
                    </div>
                    <div className="text-2xl font-bold">85%</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoPlayer;

