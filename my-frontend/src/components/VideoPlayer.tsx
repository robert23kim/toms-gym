import React, { useState, useRef, useEffect } from "react";
import { Play, Pause, Volume2, VolumeX, Maximize, Minimize, SkipBack, SkipForward, MessageSquare, ThumbsUp, ThumbsDown, BarChart2, Activity, Target, Award } from "lucide-react";
import { PROD_API_URL } from "../config";
import { getGhibliAvatar } from '../lib/api';

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
    avatar: getGhibliAvatar(1),
    content: "Great form on that squat! The depth was perfect.",
    timestamp: "2 hours ago",
    likes: 12,
    dislikes: 0
  },
  {
    id: 2,
    user: "Sarah Johnson",
    avatar: getGhibliAvatar(2),
    content: "The bar path was a bit forward on the way up. Try to keep it more vertical.",
    timestamp: "1 hour ago",
    likes: 8,
    dislikes: 2
  },
  {
    id: 3,
    user: "Mike Wilson",
    avatar: getGhibliAvatar(3),
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
  const [isMuted, setIsMuted] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isControlsVisible, setIsControlsVisible] = useState(true);
  const [isLoading, setIsLoading] = useState(true);
  const [isMobileDevice, setIsMobileDevice] = useState(false);
  const [useNativeControls, setUseNativeControls] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const controlsTimeoutRef = useRef<number | null>(null);
  const [comments] = useState<Comment[]>(mockComments);
  const [newComment, setNewComment] = useState("");
  const touchStartTimeRef = useRef<number>(0);
  const touchPositionRef = useRef<{ x: number, y: number }>({ x: 0, y: 0 });
  const retryCountRef = useRef<number>(0);
  const [processedVideoUrl, setProcessedVideoUrl] = useState<string>(videoUrl);

  useEffect(() => {
    // Reset error state when video URL changes
    setHasError(false);
    setErrorMessage("");
    setIsLoading(true);
    retryCountRef.current = 0;

    // Detect mobile device
    const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
    setIsMobileDevice(isMobile);
    
    // On mobile devices, use native controls by default for better compatibility
    if (isMobile) {
      setUseNativeControls(true);
    }
    
    const video = videoRef.current;
    if (!video) return;

    // Apply native controls for mobile
    if (isMobile) {
      video.controls = true;
    }

    const onLoadedMetadata = () => {
      console.log("Video metadata loaded successfully");
      setDuration(video.duration);
      setIsLoading(false);
      setHasError(false);
      
      // Force play on mobile after metadata is loaded
      if (isMobile) {
        video.play().catch(err => {
          console.warn("Autoplay failed after metadata load:", err);
        });
      }
    };

    const onTimeUpdate = () => {
      setCurrentTime(video.currentTime);
      setProgress((video.currentTime / video.duration) * 100);
    };
    
    const onError = (e: ErrorEvent) => {
      console.error("Video error detected:", e, video.error);
      setIsLoading(false);
      setHasError(true);
      
      // Get detailed error message
      let message = "Video playback error";
      if (video.error) {
        switch (video.error.code) {
          case 1:
            message = "Video loading aborted";
            break;
          case 2:
            message = "Network error occurred while loading video";
            break;
          case 3:
            message = "Video decoding failed";
            break;
          case 4:
            message = "Video format not supported";
            break;
          default:
            message = `Error code: ${video.error.code}`;
        }
      }
      setErrorMessage(message);
      
      // Fallback to native controls on error
      if (isMobile && video) {
        setUseNativeControls(true);
        video.controls = true;
        
        // Try to reload video on error (up to 3 times)
        if (retryCountRef.current < 3) {
          retryCountRef.current++;
          console.log(`Attempting video reload (${retryCountRef.current}/3)`);
          // Add a small delay before reload
          setTimeout(() => {
            video.load();
          }, 1000);
        }
      }
    };
    
    const onCanPlay = () => {
      console.log("Video can play now");
      setIsLoading(false);
      setHasError(false);
    };

    video.addEventListener("loadedmetadata", onLoadedMetadata);
    video.addEventListener("timeupdate", onTimeUpdate);
    video.addEventListener("ended", () => setIsPlaying(false));
    video.addEventListener("error", onError as any);
    video.addEventListener("canplay", onCanPlay);

    document.addEventListener("fullscreenchange", handleFullscreenChange);

    return () => {
      video.removeEventListener("loadedmetadata", onLoadedMetadata);
      video.removeEventListener("timeupdate", onTimeUpdate);
      video.removeEventListener("ended", () => setIsPlaying(false));
      video.removeEventListener("error", onError as any);
      video.removeEventListener("canplay", onCanPlay);
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
      
      if (controlsTimeoutRef.current) {
        clearTimeout(controlsTimeoutRef.current);
      }
    };
  }, [videoUrl]); // Re-run when videoUrl changes

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

  // Touch handlers for mobile
  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartTimeRef.current = Date.now();
    if (e.touches.length === 1) {
      touchPositionRef.current = { 
        x: e.touches[0].clientX,
        y: e.touches[0].clientY
      };
    }
  };
  
  const handleTouchEnd = (e: React.TouchEvent) => {
    const touchDuration = Date.now() - touchStartTimeRef.current;
    
    // Short tap (less than 300ms) toggles play/pause
    if (touchDuration < 300) {
      togglePlay();
    }
    
    showControls();
  };

  // Process video URL to replace localhost with PROD_API_URL for mobile 
  useEffect(() => {
    // Always replace localhost with production URL, regardless of device
    let finalUrl = videoUrl;
    
    // Check for localhost with specific port pattern
    if (videoUrl.includes('localhost:5001')) {
      console.log('Replacing localhost:5001 URL with production URL');
      
      try {
        // Extract just the path portion after the port
        const urlParts = videoUrl.split('localhost:5001');
        if (urlParts.length > 1) {
          const path = urlParts[1]; // This gets /video/path?params
          
          // Create new URL with production base
          finalUrl = `${PROD_API_URL}${path}`;
          console.log('Original URL:', videoUrl);
          console.log('Processed URL:', finalUrl);
        }
      } catch (err) {
        console.error('Error processing video URL:', err);
      }
    }
    
    setProcessedVideoUrl(finalUrl);
  }, [videoUrl]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2">
        <div className="bg-card rounded-lg shadow-lg overflow-hidden">
          <div 
            className="relative aspect-video bg-black group"
            onMouseMove={showControls}
            onMouseLeave={() => isPlaying && setIsControlsVisible(false)}
            onTouchStart={handleTouchStart}
            onTouchEnd={handleTouchEnd}
          >
            {isLoading && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/50 z-10">
                <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-white"></div>
              </div>
            )}
            
            {hasError && (
              <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/70 z-10 p-4 text-center">
                <div className="text-red-500 mb-4">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  <h3 className="text-xl font-bold">Video Playback Error</h3>
                  <p className="text-sm mt-2">{errorMessage || "There was a problem playing this video."}</p>
                </div>
                <button 
                  className="bg-primary hover:bg-primary/90 text-white font-bold py-2 px-4 rounded-full"
                  onClick={() => {
                    setHasError(false);
                    setIsLoading(true);
                    if (videoRef.current) {
                      videoRef.current.load();
                    }
                  }}
                >
                  Try Again
                </button>
                {onNextVideo && (
                  <button 
                    className="mt-2 bg-transparent hover:bg-white/10 text-white font-bold py-2 px-4 rounded-full"
                    onClick={onNextVideo}
                  >
                    Next Video
                  </button>
                )}
              </div>
            )}
            
            <video
              ref={videoRef}
              src={processedVideoUrl}
              className="w-full h-full object-contain"
              onClick={togglePlay}
              playsInline
              webkit-playsinline="true"
              x5-playsinline="true"
              muted={isMuted}
              controls={useNativeControls}
              controlsList="nodownload"
              onLoadStart={() => setIsLoading(true)}
              onError={(e) => {
                console.error("Video error:", e);
                setIsLoading(false);
                // If there's an error, try showing native controls as fallback
                if (videoRef.current) {
                  setUseNativeControls(true);
                  videoRef.current.controls = true;
                }
              }}
              preload="metadata"
              poster={processedVideoUrl ? processedVideoUrl + '?poster=true' : undefined}
            />
            
            {/* Play/Pause Overlay - Only show on non-mobile devices */}
            {!isMobileDevice && (
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
            )}

            {/* Next Video Overlay - Only show on non-mobile devices */}
            {onNextVideo && !isMobileDevice && (
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
            
            {/* Video Controls - Only show for non-mobile devices */}
            {!useNativeControls && (
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
            )}
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
                  <div className="w-10 h-10 rounded-full bg-accent/10 overflow-hidden flex-shrink-0">
                    <img
                      src={comment.avatar}
                      alt={comment.user}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        // On error, replace with a colored background with initials
                        e.currentTarget.style.display = 'none';
                        e.currentTarget.parentElement.innerHTML = `
                          <div class="w-full h-full flex items-center justify-center bg-accent/10 text-accent font-medium">
                            ${comment.user.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()}
                          </div>
                        `;
                      }}
                    />
                  </div>
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

