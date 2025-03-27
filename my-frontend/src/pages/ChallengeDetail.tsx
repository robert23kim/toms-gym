import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Calendar, MapPin, Users, Clock, Trophy, Dumbbell, CheckCircle2, XCircle } from "lucide-react";
import axios from "axios";
import { Challenge } from "../lib/types";
import Layout from "../components/Layout";

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

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        // Fetch challenge details
        const challengeResponse = await axios.get(
          `https://my-app-834341357827.us-east1.run.app/competitions/${id}`
        );

        // Transform the backend data to match our frontend Challenge type
        const backendData = challengeResponse.data.competition;
        const transformedChallenge: Challenge = {
          id: backendData.id,
          title: backendData.name,
          date: backendData.start_date,
          registrationDeadline: backendData.end_date,
          location: backendData.location,
          description: "Join us for an exciting powerlifting competition! This event will feature multiple weight classes and categories. Whether you're a seasoned lifter or just starting out, there's a place for you to compete and showcase your strength.",
          status: determineStatus(backendData.start_date, backendData.end_date),
          categories: [
            ...backendData.lifttypes,
            ...backendData.weightclasses,
            backendData.gender === 'F' ? 'Women' : 'Men'
          ],
          participants: 0, // This will be updated when we implement participant tracking
          prizePool: {
            first: 1000,
            second: 500,
            third: 250,
            total: 1750
          }
        };
        setChallenge(transformedChallenge);
      } catch (err: any) {
        console.error("Error fetching data:", err);
        setError(err.response?.data?.error || "Failed to load challenge details");
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
                <span
                  className={`px-3 py-1 rounded-full text-sm font-medium ${
                    challenge.status === "upcoming"
                      ? "bg-blue-500/10 text-blue-500"
                      : challenge.status === "ongoing"
                      ? "bg-green-500/10 text-green-500"
                      : "bg-gray-500/10 text-gray-500"
                  }`}
                >
                  {challenge.status.charAt(0).toUpperCase() + challenge.status.slice(1)}
                </span>
              </div>

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

          {/* Recent Attempts Section */}
          <div className="bg-card rounded-lg shadow-lg overflow-hidden">
            <div className="p-6 sm:p-8">
              <div className="flex items-center gap-2 mb-6">
                <Dumbbell className="text-primary" size={24} />
                <h2 className="text-xl font-semibold">Recent Attempts</h2>
              </div>

              {attempts.length === 0 ? (
                <p className="text-muted-foreground text-center py-4">No attempts have been submitted yet.</p>
              ) : (
                <div className="space-y-4">
                  {attempts.map((attempt) => (
                    <motion.div
                      key={attempt.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="flex items-center justify-between p-4 bg-secondary/5 rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-full ${
                          attempt.success ? "bg-green-500/10" : "bg-red-500/10"
                        }`}>
                          {attempt.success ? (
                            <CheckCircle2 className="w-5 h-5 text-green-500" />
                          ) : (
                            <XCircle className="w-5 h-5 text-red-500" />
                          )}
                        </div>
                        <div>
                          <h3 className="font-medium">{attempt.type}</h3>
                          <p className="text-sm text-muted-foreground">
                            {new Date(attempt.timestamp).toLocaleString()}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="font-bold">{attempt.weight}kg</span>
                        {attempt.video_url && (
                          <Link
                            to={`/challenges/${id}/participants/${attempt.participant_id}/video/${attempt.id}`}
                            className="text-primary hover:underline text-sm"
                          >
                            Watch Video
                          </Link>
                        )}
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </motion.div>
    </Layout>
  );
};

export default ChallengeDetail;
