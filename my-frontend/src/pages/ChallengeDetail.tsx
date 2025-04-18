import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Calendar, MapPin, Users, Clock, Trophy, Dumbbell, CheckCircle2, XCircle, ArrowRight } from "lucide-react";
import axios from "axios";
import { Challenge } from "../lib/types";
import Layout from "../components/Layout";
import { API_URL } from "../config";

// Use the local API URL for competitions
const COMPETITIONS_API_URL = API_URL;

interface Attempt {
  id: number;
  participant_id: number;
  type: string;
  weight: number;
  success: boolean;
  video_url: string | null;
  timestamp: string;
}

// Mock attempts data
const mockAttempts: Attempt[] = [
  {
    id: 1,
    participant_id: 1,
    type: "Squat",
    weight: 225,
    success: true,
    video_url: "https://example.com/video1",
    timestamp: "2024-03-20T10:30:00Z"
  },
  {
    id: 2,
    participant_id: 2,
    type: "Bench Press",
    weight: 180,
    success: true,
    video_url: "https://example.com/video2",
    timestamp: "2024-03-20T11:15:00Z"
  },
  {
    id: 3,
    participant_id: 3,
    type: "Deadlift",
    weight: 275,
    success: false,
    video_url: null,
    timestamp: "2024-03-20T12:00:00Z"
  },
  {
    id: 4,
    participant_id: 1,
    type: "Squat",
    weight: 235,
    success: true,
    video_url: "https://example.com/video4",
    timestamp: "2024-03-20T13:45:00Z"
  },
  {
    id: 5,
    participant_id: 2,
    type: "Bench Press",
    weight: 185,
    success: true,
    video_url: "https://example.com/video5",
    timestamp: "2024-03-20T14:30:00Z"
  }
];

const ChallengeDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [attempts] = useState<Attempt[]>(mockAttempts);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isJoining, setIsJoining] = useState(false);
  const [joinError, setJoinError] = useState<string | null>(null);
  const [participants, setParticipants] = useState<any[]>([]);
  const [hasJoined, setHasJoined] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        const userId = localStorage.getItem('userId');
        
        // Fetch challenge, participants, and check if user has joined
        const [challengeData, participantsData] = await Promise.all([
          axios.get(`${COMPETITIONS_API_URL}/competitions/${id}`),
          axios.get(`${COMPETITIONS_API_URL}/competitions/${id}/participants`)
        ]);

        const backendData = challengeData.data.competition;
        const participantsDataBackend = participantsData.data.participants || [];
        setParticipants(participantsDataBackend);

        // Check if the current user has already joined
        if (userId) {
          const hasUserJoined = participantsDataBackend.some((p: any) => p.id === userId);
          setHasJoined(hasUserJoined);
        }

        // Transform backend data to match frontend Challenge type
        const transformedChallenge: Challenge = {
          id: backendData.id,
          title: backendData.name,
          date: backendData.start_date,
          registrationDeadline: backendData.end_date,
          location: backendData.location || (backendData.description ? backendData.description.split(' - ')[0] : ""),
          description: backendData.description || "",
          status: determineStatus(backendData.start_date, backendData.end_date),
          categories: [],
          participants: participantsDataBackend.length,
          prizePool: {
            first: 1000,
            second: 500,
            third: 250,
            total: 1750
          }
        };

        // Add categories from metadata fields if available
        if (backendData.lifttypes || backendData.weightclasses || backendData.gender) {
          const categories = [
            ...(backendData.lifttypes || []),
            ...(backendData.weightclasses || []),
            backendData.gender === 'F' ? 'Women' : 'Men'
          ];
          transformedChallenge.categories = categories;
        } 
        // Otherwise try to parse metadata from description field if it exists
        else if (backendData.description && backendData.description.includes(' - ')) {
          try {
            // Extract the JSON part from the description
            const metadataString = backendData.description.split(' - ')[1];
            const metadata = JSON.parse(metadataString);
            
            // Add categories from metadata
            const categories = [
              ...(metadata.lifttypes || []),
              ...(metadata.weightclasses || [])
            ];
            
            if (metadata.gender) {
              categories.push(metadata.gender === 'F' ? 'Women' : 'Men');
            }
            
            transformedChallenge.categories = categories;
          } catch (err) {
            console.warn('Failed to parse competition metadata from description', err);
            // Use empty categories if parsing fails
            transformedChallenge.categories = [];
          }
        }

        setChallenge(transformedChallenge);
      } catch (err: any) {
        console.error("Error fetching data:", err);
        console.error("Error details:", {
          message: err.message,
          response: err.response?.data,
          status: err.response?.status,
          url: `${COMPETITIONS_API_URL}/competitions/${id}`
        });
        setError(
          err.response?.data?.error || 
          err.message || 
          "Failed to load challenge details"
        );
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [id]);

  const determineStatus = (startDate: string, endDate: string): "upcoming" | "ongoing" | "completed" => {
    const now = new Date();
    const start = new Date(startDate);
    const end = new Date(endDate);

    if (now < start) return "upcoming";
    if (now > end) return "completed";
    return "ongoing";
  };

  const handleJoinChallenge = async () => {
    try {
      setIsJoining(true);
      setJoinError(null);

      const userId = localStorage.getItem('userId');
      if (!userId) {
        setJoinError('Please create a profile before joining a challenge');
        return;
      }
      
      await axios.post(
        `${COMPETITIONS_API_URL}/join_competition`,
        {
          user_id: userId,
          competition_id: id,
          weight_class: "83kg",
          gender: "M"
        }
      );

      // Fetch updated participants count
      const participantsResponse = await axios.get(`${COMPETITIONS_API_URL}/competitions/${id}/participants`);
      const participantsData = participantsResponse.data.participants || [];
      
      // Update the challenge with the new participants count
      if (challenge) {
        setChallenge({
          ...challenge,
          participants: participantsData.length
        });
      }

      // Update hasJoined state
      setHasJoined(true);
      setParticipants(participantsData);
    } catch (err: any) {
      console.error("Error joining challenge:", err);
      setJoinError(err.response?.data?.error || "Failed to join challenge. Please try again.");
    } finally {
      setIsJoining(false);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8">
          <div className="max-w-7xl mx-auto">
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <div className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8">
          <div className="max-w-7xl mx-auto">
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 text-red-500">
              {error}
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  if (!challenge) {
    return (
      <Layout>
        <div className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8">
          <div className="max-w-7xl mx-auto">
            <div className="text-center">
              <h2 className="text-2xl font-bold">Challenge not found</h2>
              <Link to="/challenges" className="text-primary hover:underline mt-4 inline-block">
                Return to Challenges
              </Link>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8"
      >
        <div className="max-w-4xl mx-auto">
          <Link
            to="/challenges"
            className="inline-flex items-center text-muted-foreground hover:text-foreground mb-8"
          >
            <ArrowLeft className="mr-2" size={16} />
            Back to Challenges
          </Link>

          <div className="bg-card rounded-lg shadow-lg overflow-hidden mb-8">
            <div className="p-6 sm:p-8">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6">
                <h1 className="text-3xl font-bold mb-4 sm:mb-0">{challenge.title}</h1>
                <div className="flex items-center gap-2">
                  <span
                    className={`px-3 py-1.5 rounded-full text-sm font-medium ${
                      challenge.status === "upcoming"
                        ? "bg-blue-500/10 text-blue-500"
                        : challenge.status === "ongoing"
                        ? "bg-green-500/10 text-green-500"
                        : "bg-gray-500/10 text-gray-500"
                    }`}
                  >
                    {challenge.status.charAt(0).toUpperCase() + challenge.status.slice(1)}
                  </span>
                  {hasJoined && (
                    <div className="flex items-center gap-2 bg-green-500/10 text-green-500 px-3 py-1.5 rounded-full text-sm font-medium">
                      <CheckCircle2 className="w-4 h-4" />
                      <span>You've joined this challenge</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Join Challenge Button - Moved outside the header */}
              {!hasJoined && (
                <div className="mb-6">
                  {challenge?.status === "upcoming" ? (
                    <>
                      <button
                        onClick={handleJoinChallenge}
                        disabled={isJoining}
                        className={`w-full sm:w-auto sm:px-8 py-3 px-4 rounded-lg bg-green-500 text-white font-medium 
                          shadow-sm transition-all hover:bg-green-600 hover:shadow
                          ${isJoining ? 'opacity-50 cursor-not-allowed' : 'hover:translate-y-[-1px]'}`}
                      >
                        {isJoining ? 'Joining...' : 'Join Challenge'}
                      </button>
                      {joinError && (
                        <p className="mt-2 text-sm text-red-500">{joinError}</p>
                      )}
                    </>
                  ) : challenge?.status === "completed" ? (
                    <div className="text-center text-muted-foreground">
                      This challenge has ended
                    </div>
                  ) : (
                    <div className="text-center text-muted-foreground">
                      Registration is closed
                    </div>
                  )}
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
                <div className="flex items-center text-muted-foreground">
                  <Calendar className="mr-2" size={16} />
                  <span>{new Date(challenge.date).toLocaleDateString()}</span>
                </div>
                <div className="flex items-center text-muted-foreground">
                  <MapPin className="mr-2" size={16} />
                  <span>{challenge.location}</span>
                </div>
                <div className="flex items-center text-muted-foreground">
                  <Users className="mr-2" size={16} />
                  <span>{challenge.participants} Participants</span>
                </div>
                <div className="flex items-center text-muted-foreground">
                  <Clock className="mr-2" size={16} />
                  <span>Registration until {new Date(challenge.registrationDeadline).toLocaleDateString()}</span>
                </div>
              </div>

              <div className="mb-6">
                <h2 className="text-xl font-semibold mb-2">Description</h2>
                <p className="text-muted-foreground">{challenge.description}</p>
              </div>

              <div className="mb-6">
                <h2 className="text-xl font-semibold mb-2">Categories</h2>
                <div className="flex flex-wrap gap-2">
                  {challenge.categories.map((category) => (
                    <span
                      key={category}
                      className="px-3 py-1 bg-primary/10 text-primary rounded-full text-sm"
                    >
                      {category}
                    </span>
                  ))}
                </div>
              </div>

              {/* Upload Video Call to Action */}
              {hasJoined && (
                <div className="mb-8 bg-blue-500/5 rounded-lg p-6 border border-blue-500/10">
                  <div className="flex items-start gap-4">
                    <div className="p-3 bg-blue-500/10 rounded-lg">
                      <Dumbbell className="w-6 h-6 text-blue-500" />
                    </div>
                    <div className="flex-1">
                      <h2 className="text-xl font-semibold mb-2">Submit Your Lift</h2>
                      <p className="text-muted-foreground mb-4">
                        Ready to showcase your strength? Upload a video of your lift to participate in the challenge.
                      </p>
                      <Link
                        to={`/challenges/${id}/upload`}
                        className="inline-flex items-center gap-2 bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition-colors"
                      >
                        Upload Video
                        <ArrowRight className="w-4 h-4" />
                      </Link>
                    </div>
                  </div>
                </div>
              )}

              {/* Participants Section */}
              <div className="mb-6">
                <h2 className="text-xl font-semibold mb-4 flex items-center">
                  <Users className="mr-2" size={20} />
                  Top Participants
                </h2>
                <div className="space-y-2">
                  {participants.slice(0, 5).map((participant) => (
                    <div key={participant.id} className="p-3 bg-card rounded-lg shadow">
                      <div className="flex justify-between items-center mb-1">
                        <h4 className="text-lg font-semibold">{participant.name}</h4>
                        <span className="text-sm text-muted-foreground">{participant.weight_class}</span>
                      </div>
                      
                      {/* Horizontal layout for attempts */}
                      <div className="flex flex-wrap gap-x-3 gap-y-2">
                        {participant.attempts?.filter(attempt => attempt.weight).map((attempt, index) => (
                          <div 
                            key={index} 
                            className={`flex items-center text-sm rounded-full px-3 py-1 ${
                              attempt.status === 'completed' 
                                ? 'bg-green-500/10 border border-green-500/20' 
                                : 'bg-red-500/10 border border-red-500/20'
                            }`}
                          >
                            <Link 
                              to={`/random-video?type=${attempt.lift_type}`}
                              className={`hover:underline ${
                                attempt.status === 'completed' 
                                  ? 'text-green-600 font-medium' 
                                  : 'text-red-600 line-through'
                              }`}
                            >
                              {attempt.lift_type}
                            </Link>
                            <span className="mx-1 font-bold">{attempt.weight}kg</span>
                            {attempt.video_url && (
                              <Link
                                to={`/challenges/${id}/participants/${participant.id}/video/${index}`}
                                className="text-primary hover:underline text-xs ml-1"
                              >
                                (watch)
                              </Link>
                            )}
                          </div>
                        ))}
                        <div className="text-sm text-muted-foreground ml-auto self-center">
                          Total: {participant.total_weight}kg
                        </div>
                      </div>
                    </div>
                  ))}
                  {participants.length > 5 && (
                    <p className="text-sm text-muted-foreground mt-1">
                      And {participants.length - 5} more participants...
                    </p>
                  )}
                </div>
              </div>

              <div className="bg-primary/5 rounded-lg p-6">
                <h2 className="text-xl font-semibold mb-4 flex items-center">
                  <Trophy className="mr-2" size={20} />
                  Prize Pool
                </h2>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-primary">${challenge.prizePool.first}</div>
                    <div className="text-sm text-muted-foreground">1st Place</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-primary">${challenge.prizePool.second}</div>
                    <div className="text-sm text-muted-foreground">2nd Place</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-primary">${challenge.prizePool.third}</div>
                    <div className="text-sm text-muted-foreground">3rd Place</div>
                  </div>
                </div>
                <div className="mt-4 text-center">
                  <div className="text-lg font-semibold text-primary">
                    Total Prize Pool: ${challenge.prizePool.total}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </Layout>
  );
};

export default ChallengeDetail;
