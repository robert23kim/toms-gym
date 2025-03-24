import React, { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { getCompetitionById, getLiftsByParticipantId, sampleLifts } from "../lib/data";
import Layout from "../components/Layout";
import VideoPlayerComponent from "../components/VideoPlayer";
import { ArrowLeft, Activity, BarChart2, Timer, Ruler, MessageCircle, Smile, Heart, Fire, ThumbsUp, Send } from "lucide-react";

interface Comment {
  id: string;
  userId: string;
  userName: string;
  userAvatar: string;
  text: string;
  timestamp: string;
  reactions: { [key: string]: string[] };
}

interface VideoReaction {
  emoji: string;
  count: number;
  users: string[];
}

const VideoPlayerPage = () => {
  const { competitionId, participantId, liftId } = useParams<{
    competitionId: string;
    participantId: string;
    liftId?: string;
  }>();
  
  const navigate = useNavigate();
  const competition = getCompetitionById(competitionId || "");
  const participant = competition?.participants.find(p => p.id === participantId);
  const lifts = getLiftsByParticipantId(participantId || "") || sampleLifts;
  const currentLift = liftId ? lifts.find(lift => lift.id === liftId) : lifts[0];

  // Mock comments data
  const [comments, setComments] = useState<Comment[]>([
    {
      id: 'c1',
      userId: 'u1',
      userName: 'John Doe',
      userAvatar: 'https://randomuser.me/api/portraits/men/1.jpg',
      text: 'Great form on this lift! 💪',
      timestamp: '2024-03-15T10:30:00Z',
      reactions: {
        '❤️': ['u2', 'u3'],
        '👏': ['u4']
      }
    },
    {
      id: 'c2',
      userId: 'u2',
      userName: 'Sarah Smith',
      userAvatar: 'https://randomuser.me/api/portraits/women/1.jpg',
      text: 'The speed off the floor was impressive!',
      timestamp: '2024-03-15T11:15:00Z',
      reactions: {
        '🔥': ['u1', 'u3', 'u4'],
      }
    }
  ]);

  // Mock video reactions
  const [videoReactions, setVideoReactions] = useState<VideoReaction[]>([
    { emoji: '❤️', count: 24, users: [] },
    { emoji: '🔥', count: 18, users: [] },
    { emoji: '💪', count: 15, users: [] },
    { emoji: '👏', count: 12, users: [] },
  ]);

  const [newComment, setNewComment] = useState('');
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);

  // Mock analytics data
  const analytics = {
    barSpeed: "0.8 m/s",
    totalMovement: "2.1 meters",
    timeUnderTension: "3.2 seconds",
    peakVelocity: "1.2 m/s",
    averagePower: "850 watts",
    rangeOfMotion: "0.95 meters",
  };

  const formatLiftType = (type: string) => {
    return type.charAt(0).toUpperCase() + type.slice(1);
  };

  const handleAddComment = () => {
    if (!newComment.trim()) return;

    const comment: Comment = {
      id: `c${comments.length + 1}`,
      userId: 'currentUser',
      userName: 'Current User',
      userAvatar: 'https://randomuser.me/api/portraits/men/99.jpg',
      text: newComment,
      timestamp: new Date().toISOString(),
      reactions: {}
    };

    setComments([...comments, comment]);
    setNewComment('');
  };

  const addReactionToComment = (commentId: string, emoji: string) => {
    setComments(comments.map(comment => {
      if (comment.id === commentId) {
        const reactions = { ...comment.reactions };
        if (!reactions[emoji]) reactions[emoji] = [];
        if (!reactions[emoji].includes('currentUser')) {
          reactions[emoji] = [...reactions[emoji], 'currentUser'];
        }
        return { ...comment, reactions };
      }
      return comment;
    }));
  };

  const addReactionToVideo = (emoji: string) => {
    setVideoReactions(reactions => 
      reactions.map(reaction => 
        reaction.emoji === emoji
          ? { ...reaction, count: reaction.count + 1 }
          : reaction
      )
    );
  };

  if (!competition || !participant || !currentLift) {
    return (
      <Layout>
        <div className="min-h-[60vh] flex flex-col items-center justify-center">
          <h2 className="text-2xl font-semibold mb-4">Content Not Found</h2>
          <p className="text-muted-foreground mb-6">
            The requested content doesn't exist or has been removed.
          </p>
          <button
            onClick={() => navigate("/")}
            className="flex items-center px-4 py-2 rounded-md bg-accent text-white hover:bg-accent/90 transition-colors"
          >
            <ArrowLeft size={16} className="mr-2" /> Return to Home
          </button>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="mb-6 flex items-center">
        <button
          onClick={() => navigate(`/competitions/${competitionId}`)}
          className="mr-4 flex items-center text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft size={16} className="mr-1" /> Back to Competition
        </button>
        <h1 className="text-2xl font-semibold">Lift Video</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Sidebar - Details & All Lifts */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
          className="lg:col-span-3 order-last lg:order-first"
        >
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="glass p-6 rounded-xl mb-6"
          >
            <h2 className="text-xl font-semibold mb-4">
              {formatLiftType(currentLift.type)} - {currentLift.weight}kg
              <span className={`ml-3 inline-flex items-center px-2.5 py-0.5 text-xs font-medium rounded-full ${
                currentLift.success 
                  ? "bg-green-100 text-green-800" 
                  : "bg-red-100 text-red-800"
              }`}>
                {currentLift.success ? "Good Lift" : "No Lift"}
              </span>
            </h2>
            
            <div className="flex items-center mb-6">
              <img
                src={participant.avatar}
                alt={participant.name}
                className="w-10 h-10 rounded-full mr-3"
              />
              <div>
                <h3 className="font-medium">{participant.name}</h3>
                <div className="text-sm text-muted-foreground">
                  {participant.weightClass} | {participant.country}
                </div>
              </div>
            </div>
            
            <div className="border-t border-border/50 pt-4">
              <h3 className="font-medium mb-2">About This Lift</h3>
              <p className="text-muted-foreground">
                {`This is a ${formatLiftType(currentLift.type)} attempt at ${currentLift.weight}kg by ${participant.name} 
                during the ${competition.title}. The lift was ${currentLift.success ? 'successful' : 'unsuccessful'}.`}
              </p>
            </div>
          </motion.div>

          <div className="glass p-6 rounded-xl sticky top-20">
            <h2 className="text-xl font-semibold mb-4">All Lifts</h2>
            <div className="space-y-3">
              {lifts.map((lift, index) => (
                <motion.div
                  key={lift.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: 0.05 * index }}
                >
                  <button
                    onClick={() => navigate(`/competitions/${competitionId}/participants/${participantId}/video/${lift.id}`)}
                    className={`w-full flex items-center justify-between p-3 rounded-lg transition-colors ${
                      currentLift.id === lift.id
                        ? "bg-accent/10 border border-accent/30"
                        : "hover:bg-secondary/70"
                    }`}
                  >
                    <div className="flex items-center">
                      <div className={`w-2 h-2 rounded-full mr-3 ${
                        lift.success ? "bg-green-500" : "bg-red-500"
                      }`}></div>
                      <div className="text-left">
                        <div className="font-medium">
                          {formatLiftType(lift.type)} ({lift.weight}kg)
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {new Date(lift.timestamp).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </div>
                      </div>
                    </div>
                    <div className={`text-xs font-medium ${
                      lift.success ? "text-green-600" : "text-red-600"
                    }`}>
                      {lift.success ? "Good Lift" : "No Lift"}
                    </div>
                  </button>
                </motion.div>
              ))}
            </div>
          </div>
        </motion.div>

        {/* Main Content - Video & Comments */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="lg:col-span-6"
        >
          <div className="glass rounded-xl overflow-hidden mb-6">
            <VideoPlayerComponent
              videoUrl={currentLift.videoUrl}
              title={`${participant.name} - ${formatLiftType(currentLift.type)} (${currentLift.weight}kg)`}
            />
          </div>

          {/* Video Reactions */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="glass p-4 rounded-xl mb-6"
          >
            <div className="flex items-center justify-between">
              <div className="flex gap-4">
                {videoReactions.map(reaction => (
                  <button
                    key={reaction.emoji}
                    onClick={() => addReactionToVideo(reaction.emoji)}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-full bg-secondary/50 hover:bg-secondary transition-colors"
                  >
                    <span>{reaction.emoji}</span>
                    <span className="text-sm font-medium">{reaction.count}</span>
                  </button>
                ))}
              </div>
            </div>
          </motion.div>

          {/* Comments Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="glass p-6 rounded-xl"
          >
            <div className="flex items-center gap-2 mb-6">
              <MessageCircle className="w-5 h-5" />
              <h2 className="text-xl font-semibold">Comments</h2>
            </div>

            {/* Comment Input */}
            <div className="flex gap-4 mb-8">
              <img
                src="https://randomuser.me/api/portraits/men/99.jpg"
                alt="Your avatar"
                className="w-10 h-10 rounded-full"
              />
              <div className="flex-1">
                <div className="relative">
                  <textarea
                    value={newComment}
                    onChange={(e) => setNewComment(e.target.value)}
                    placeholder="Add a comment..."
                    className="w-full px-4 py-2 rounded-lg bg-secondary/30 border border-border focus:outline-none focus:ring-2 focus:ring-accent/50 resize-none"
                    rows={2}
                  />
                  <div className="absolute right-2 bottom-2 flex gap-2">
                    <button
                      onClick={() => setShowEmojiPicker(!showEmojiPicker)}
                      className="p-1.5 rounded-full hover:bg-secondary/70 transition-colors"
                    >
                      <Smile className="w-5 h-5 text-muted-foreground" />
                    </button>
                    <button
                      onClick={handleAddComment}
                      disabled={!newComment.trim()}
                      className="p-1.5 rounded-full hover:bg-secondary/70 transition-colors disabled:opacity-50"
                    >
                      <Send className="w-5 h-5 text-accent" />
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Comments List */}
            <div className="space-y-6">
              {comments.map((comment) => (
                <motion.div
                  key={comment.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex gap-4"
                >
                  <img
                    src={comment.userAvatar}
                    alt={comment.userName}
                    className="w-10 h-10 rounded-full"
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium">{comment.userName}</span>
                      <span className="text-xs text-muted-foreground">
                        {new Date(comment.timestamp).toLocaleDateString()}
                      </span>
                    </div>
                    <p className="text-sm mb-2">{comment.text}</p>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => addReactionToComment(comment.id, '❤️')}
                        className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                      >
                        Like
                      </button>
                      <button
                        onClick={() => addReactionToComment(comment.id, '🔥')}
                        className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                      >
                        Fire
                      </button>
                      {Object.entries(comment.reactions).map(([emoji, users]) => (
                        <span key={emoji} className="text-sm">
                          {emoji} {users.length}
                        </span>
                      ))}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </motion.div>

        {/* Right Sidebar - Analytics */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
          className="lg:col-span-3"
        >
          <div className="glass p-6 rounded-xl sticky top-20">
            <div className="flex items-center gap-2 mb-4">
              <Activity className="w-5 h-5 text-accent" />
              <h2 className="text-xl font-semibold">Lift Analytics</h2>
            </div>
            
            <div className="space-y-4">
              <div className="p-4 bg-secondary/30 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <BarChart2 className="w-4 h-4 text-muted-foreground" />
                  <h3 className="font-medium">Bar Speed</h3>
                </div>
                <p className="text-2xl font-semibold">{analytics.barSpeed}</p>
                <p className="text-sm text-muted-foreground">Average velocity</p>
              </div>

              <div className="p-4 bg-secondary/30 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Timer className="w-4 h-4 text-muted-foreground" />
                  <h3 className="font-medium">Time Under Tension</h3>
                </div>
                <p className="text-2xl font-semibold">{analytics.timeUnderTension}</p>
                <p className="text-sm text-muted-foreground">Total time</p>
              </div>

              <div className="p-4 bg-secondary/30 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Ruler className="w-4 h-4 text-muted-foreground" />
                  <h3 className="font-medium">Range of Motion</h3>
                </div>
                <p className="text-2xl font-semibold">{analytics.rangeOfMotion}</p>
                <p className="text-sm text-muted-foreground">Total movement</p>
              </div>

              <div className="mt-6 space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Peak Velocity</span>
                  <span className="font-medium">{analytics.peakVelocity}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Average Power</span>
                  <span className="font-medium">{analytics.averagePower}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Total Movement</span>
                  <span className="font-medium">{analytics.totalMovement}</span>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </Layout>
  );
};

export default VideoPlayerPage;
