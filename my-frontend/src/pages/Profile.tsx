import React, { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { motion } from "framer-motion";
import Layout from "../components/Layout";
import { Calendar, MapPin, Trophy, Activity, Award, ArrowLeft, Users, BarChart2, User, Dumbbell, Play } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import axios from "axios";
import { API_URL } from "../config";
import VideoGallery from '../components/VideoGallery';

// Interfaces for API response data
interface UserData {
  id: string;
  name: string;
  email: string;
  username?: string;
  created_at?: string;
  updated_at?: string;
  [key: string]: any; // To allow for additional fields
}

interface Competition {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  description: string;
  weight_class: string;
  status: string;
  total_weight: number;
  successful_lifts: number;
}

interface BestLift {
  type: string;
  best_weight: number;
  competition_name: string;
  competition_id: string;
}

interface Achievements {
  total_competitions: number;
  total_successful_lifts: number;
  heaviest_lift: number;
  best_snatch: number;
  best_clean_and_jerk: number;
}

interface UploadedVideo {
  attempt_id: string;
  lift_type: string;
  weight: number;
  video_url: string;
  created_at: string;
  status: string;
  competition_id: string;
  competition_name: string;
}

interface ProfileData {
  user: UserData;
  competitions: Competition[];
  best_lifts: BestLift[];
  achievements: Achievements;
  uploaded_videos?: UploadedVideo[];
}

const Profile = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user, isAuthenticated, loading: authLoading } = useAuth();
  const [profileData, setProfileData] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const fetchProfileData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Use the id from URL params or the authenticated user's id
      const userId = id || localStorage.getItem('userId');
      
      if (!userId) {
        setError("No user ID found");
        setLoading(false);
        return;
      }
      
      console.log(`Fetching profile data for user ID: ${userId}`);
      
      // Fetch user profile data from the API
      const response = await axios.get(`${API_URL}/users/${userId}/profile`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      });
      
      console.log('Profile response:', response.data);
      setProfileData(response.data);
    } catch (err: any) {
      console.error('Error fetching profile data:', err);
      const errorMessage = err.response?.data?.error || 'Failed to load profile data';
      setError(`${errorMessage} (${err.message})`);
    } finally {
      setLoading(false);
    }
  }, [id]);
  
  useEffect(() => {
    // Only fetch profile data if user is authenticated or an ID is provided
    if (!authLoading && (isAuthenticated || id)) {
      fetchProfileData();
    }
  }, [id, isAuthenticated, authLoading, fetchProfileData]);

  const formatDate = (dateString: string) => {
    const options: Intl.DateTimeFormatOptions = {
      year: "numeric",
      month: "long",
      day: "numeric",
    };
    return new Date(dateString).toLocaleDateString(undefined, options);
  };

  const getJoinDate = (createdAt?: string) => {
    if (!createdAt) return "N/A";
    const date = new Date(createdAt);
    return `${date.toLocaleString('default', { month: 'long' })} ${date.getFullYear()}`;
  };

  if (authLoading || loading) {
    return (
      <Layout>
        <div className="flex justify-center items-center h-[60vh]">
          <p>Loading profile...</p>
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <div className="flex flex-col justify-center items-center h-[60vh]">
          <p className="text-red-500 mb-4">{error}</p>
          <button 
            onClick={() => fetchProfileData()}
            className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
          >
            Try Again
          </button>
        </div>
      </Layout>
    );
  }

  if (!isAuthenticated && !id) {
    // Redirect to login if not authenticated and no specific profile ID
    navigate('/');
    return null;
  }

  if (!profileData) {
    return (
      <Layout>
        <div className="flex justify-center items-center h-[60vh]">
          <p>No profile data found</p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="mb-6 flex items-center">
        <button
          onClick={() => navigate("/")}
          className="mr-4 flex items-center text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft size={16} className="mr-1" /> Back
        </button>
        <h1 className="text-2xl font-semibold">Profile</h1>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-4xl mx-auto"
      >
        {/* Profile Header */}
        <div className="bg-card rounded-xl p-6 mb-6 shadow-sm">
          <div className="flex items-center gap-6">
            <div className="w-24 h-24 rounded-full bg-accent/10 flex items-center justify-center">
              <User size={48} className="text-accent" />
            </div>
            <div>
              <h1 className="text-3xl font-bold mb-2">{profileData.user.name}</h1>
              <p className="text-muted-foreground">{profileData.user.email}</p>
            </div>
          </div>
          <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Calendar size={18} />
              <span>Joined {getJoinDate(profileData.user.created_at)}</span>
            </div>
            {profileData.user.username && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <User size={18} />
                <span>@{profileData.user.username}</span>
              </div>
            )}
          </div>
        </div>

        {/* Stats Section */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <div className="bg-card rounded-xl p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-4">
              <Trophy className="text-accent" size={24} />
              <h2 className="text-xl font-semibold">Competition Stats</h2>
            </div>
            <div className="space-y-2">
              <p>Total Competitions: {profileData.achievements.total_competitions}</p>
              <p>Successful Lifts: {profileData.achievements.total_successful_lifts}</p>
            </div>
          </div>
          <div className="bg-card rounded-xl p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-4">
              <Dumbbell className="text-accent" size={24} />
              <h2 className="text-xl font-semibold">Personal Bests</h2>
            </div>
            <div className="space-y-2">
              {profileData.best_lifts.map(lift => (
                <p key={lift.type}>
                  {lift.type}: {lift.best_weight}kg
                </p>
              ))}
              {profileData.best_lifts.length === 0 && (
                <p className="text-muted-foreground">No personal bests recorded yet</p>
              )}
            </div>
          </div>
          <div className="bg-card rounded-xl p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-4">
              <Award className="text-accent" size={24} />
              <h2 className="text-xl font-semibold">Achievements</h2>
            </div>
            <div className="space-y-2">
              <p>Heaviest Lift: {profileData.achievements.heaviest_lift}kg</p>
              {profileData.achievements.best_snatch > 0 && (
                <p>Best Snatch: {profileData.achievements.best_snatch} lifts</p>
              )}
              {profileData.achievements.best_clean_and_jerk > 0 && (
                <p>Best Clean & Jerk: {profileData.achievements.best_clean_and_jerk} lifts</p>
              )}
            </div>
          </div>
        </div>

        {/* Uploaded Videos */}
        {profileData.uploaded_videos && profileData.uploaded_videos.length > 0 && (
          <div className="bg-card rounded-xl p-6 shadow-sm mb-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <Play className="text-accent" size={24} />
                <h2 className="text-xl font-semibold">My Videos</h2>
              </div>
              <Link to="/random-video" className="text-accent hover:underline text-sm">
                See all videos →
              </Link>
            </div>

            {/* Group videos by competition if from multiple competitions */}
            {(() => {
              // Check if videos are from multiple competitions
              const uniqueCompetitions = [...new Set(profileData.uploaded_videos?.map(video => video.competition_id))];
              
              if (uniqueCompetitions.length > 1) {
                // Group videos by competition
                return uniqueCompetitions.map(competitionId => {
                  const competitionVideos = profileData.uploaded_videos?.filter(
                    video => video.competition_id === competitionId
                  ) || [];
                  
                  if (competitionVideos.length === 0) return null;
                  
                  const competitionName = competitionVideos[0].competition_name;
                  
                  return (
                    <div key={competitionId} className="mb-6 last:mb-0">
                      <div className="flex items-center justify-between mb-2">
                        <Link 
                          to={`/competitions/${competitionId}`} 
                          className="text-lg font-medium hover:text-accent"
                        >
                          {competitionName}
                        </Link>
                        <span className="text-sm text-muted-foreground">
                          {competitionVideos.length} {competitionVideos.length === 1 ? 'video' : 'videos'}
                        </span>
                      </div>
                      
                      <VideoGallery 
                        videos={competitionVideos}
                        maxVideos={3}
                        showCompetitionName={false}
                        userId={profileData.user.id}
                      />
                    </div>
                  );
                });
              } else {
                // Standard display for videos from a single competition or unaffiliated videos
                return (
                  <VideoGallery 
                    videos={profileData.uploaded_videos}
                    maxVideos={6}
                    userId={profileData.user.id}
                  />
                );
              }
            })()}
          </div>
        )}

        {/* Recent Competitions */}
        <div className="bg-card rounded-xl p-6 shadow-sm">
          <h2 className="text-xl font-semibold mb-4">Competition History</h2>
          <div className="space-y-4">
            {profileData.competitions.length > 0 ? (
              profileData.competitions.map((competition) => {
                // Find videos for this competition
                const competitionVideos = profileData.uploaded_videos?.filter(
                  video => video.competition_id === competition.id
                ) || [];
                
                return (
                  <div
                    key={competition.id}
                    className="flex flex-col p-4 bg-background rounded-lg"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <Link 
                          to={`/competitions/${competition.id}`}
                          className="font-medium hover:text-accent"
                        >
                          {competition.name}
                        </Link>
                        <p className="text-sm text-muted-foreground">
                          {formatDate(competition.start_date)} • {competition.weight_class}
                        </p>
                      </div>
                      <div className="text-right">
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          competition.status === 'completed' ? 'bg-green-100 text-green-800' : 
                          competition.status === 'upcoming' ? 'bg-blue-100 text-blue-800' : 
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {competition.status}
                        </span>
                        {competition.total_weight > 0 && (
                          <p className="text-accent font-medium mt-1">{competition.total_weight}kg total</p>
                        )}
                      </div>
                    </div>
                    
                    {/* Videos for this competition */}
                    {competitionVideos.length > 0 && (
                      <div className="mt-3">
                        <p className="text-sm font-medium mb-2">
                          {competitionVideos.length} {competitionVideos.length === 1 ? 'video' : 'videos'} submitted:
                        </p>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                          {competitionVideos.map((video) => (
                            <Link 
                              key={video.attempt_id}
                              to={`/challenges/${video.competition_id}/participants/${profileData.user.id}/video/${video.attempt_id}`}
                              className="flex items-center p-2 bg-accent/5 rounded-md hover:bg-accent/10 transition-colors"
                            >
                              <div className="w-10 h-10 bg-accent/10 rounded flex items-center justify-center mr-3">
                                <Play size={16} className="text-accent" />
                              </div>
                              <div>
                                <p className="font-medium text-sm">{video.lift_type} - {video.weight}kg</p>
                                <p className="text-xs text-muted-foreground">
                                  {new Date(video.created_at).toLocaleDateString()}
                                </p>
                              </div>
                              <span className={`ml-auto text-xs px-2 py-0.5 rounded-full ${
                                video.status === 'completed' ? 'bg-green-100 text-green-800' : 
                                video.status === 'failed' ? 'bg-red-100 text-red-800' : 
                                'bg-gray-100 text-gray-800'
                              }`}>
                                {video.status}
                              </span>
                            </Link>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })
            ) : (
              <p className="text-muted-foreground text-center py-4">No competitions yet</p>
            )}
          </div>
        </div>
      </motion.div>
    </Layout>
  );
};

export default Profile; 