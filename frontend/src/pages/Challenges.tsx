import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { Plus, Timer } from "lucide-react";
import Layout from "../components/Layout";
import RowCard from "../components/RowCard";
import ChallengeCard from "../components/ChallengeCard";
import CreateChallenge from "../components/CreateChallenge";
import { Challenge } from "../lib/types";
import axios from "axios";
import { API_URL, COMPETITIONS_API_URL } from "../config";

const Challenges = () => {
  const [activeFilter, setActiveFilter] = useState<'upcoming' | 'ongoing' | 'completed' | 'all'>("all");
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [challenges, setChallenges] = useState<Challenge[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const determineStatus = (startDate: string, endDate: string): 'upcoming' | 'ongoing' | 'completed' => {
    const now = new Date();
    const start = new Date(startDate);
    const end = new Date(endDate);

    if (now < start) return 'upcoming';
    if (now > end) return 'completed';
    return 'ongoing';
  };

  const fetchChallenges = async () => {
    try {
      setLoading(true);
      setError(null);
      console.log("Fetching challenges from:", `${COMPETITIONS_API_URL}/competitions`);
      const response = await axios.get(`${COMPETITIONS_API_URL}/competitions`);
      console.log("API Response:", response.data);
      const dbChallenges = response.data.competitions;

      if (!dbChallenges || !Array.isArray(dbChallenges)) {
        console.error("Invalid challenges data received:", dbChallenges);
        setError('Received invalid data from the server. Expected an array of challenges.');
        setChallenges([]);
        return;
      }

      console.log(`Transforming ${dbChallenges.length} challenges`);
      
      // Transform the database challenges to match our frontend type
      const transformedChallenges = dbChallenges.map((challenge: any) => ({
        id: challenge.id,
        title: challenge.name,
        date: challenge.start_date,
        registrationDeadline: challenge.end_date,
        location: challenge.location,
        description: challenge.description || '',
        image: challenge.image || 'https://images.unsplash.com/photo-1599058917765-a780eda07a3e?q=80&w=1469&auto=format&fit=crop',
        status: determineStatus(challenge.start_date, challenge.end_date),
        categories: [
          ...(challenge.lifttypes || []),
          ...(challenge.weightclasses || []),
          challenge.gender === 'Female' ? 'Women' : 'Men'
        ],
        participants: challenge.participants || 0,
        prizePool: {
          first: 1000,
          second: 500,
          third: 250,
          total: 1750
        }
      }));

      console.log(`Successfully transformed ${transformedChallenges.length} challenges`);
      setChallenges(transformedChallenges);
    } catch (err: any) {
      console.error('Error fetching challenges:', err);
      let errorMessage = 'Failed to load challenges. Please try again later.';
      
      if (err.response) {
        console.error('API Error response:', err.response.status, err.response.data);
        errorMessage = `Error ${err.response.status}: ${err.response.data?.error || err.response.statusText}`;
      } else if (err.request) {
        console.error('API Request error - no response received:', err.request);
        errorMessage = 'Network error: No response from server. Please check your connection.';
      } else {
        console.error('Error message:', err.message);
        errorMessage = `Error: ${err.message}`;
      }
      
      setError(errorMessage);
      setChallenges([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchChallenges();
  }, []);

  const filteredChallenges = activeFilter === "all"
    ? challenges
    : challenges.filter(challenge => challenge.status === activeFilter);

  const handleCreateChallenge = async (newChallenge: Challenge) => {
    setChallenges(prev => [...prev, newChallenge]);
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-accent"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="mb-8 text-center"
      >
        <h1 className="text-3xl font-semibold mb-2">Challenges</h1>
        <p className="text-muted-foreground mb-4">
          Browse all available lifting challenges and find the perfect one for you.
        </p>
        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-md hover:bg-accent/90 transition-colors"
        >
          <Plus size={20} />
          <span>Create Challenge</span>
        </button>
      </motion.div>

      {error && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-md text-red-500">
          {error}
        </div>
      )}

      {challenges.some((c) => c.status === "ongoing") && (
        <div className="max-w-2xl mx-auto mb-10 flex flex-col gap-2.5">
          <div className="flex items-center gap-3.5 text-xs uppercase tracking-widest text-muted-foreground mb-1">
            <span className="flex-1 h-px bg-border" aria-hidden="true" />
            Open now
            <span className="flex-1 h-px bg-border" aria-hidden="true" />
          </div>
          {challenges
            .filter((c) => c.status === "ongoing")
            .map((c) => (
              <RowCard
                key={c.id}
                to={`/challenges/${c.id}`}
                icon={<Timer className="w-[18px] h-[18px]" />}
                title={c.title}
                pill={c.categories?.[0]}
              />
            ))}
        </div>
      )}

      <div className="mb-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-semibold">All Challenges</h2>
          
          <div className="flex space-x-2">
            {(["all", "upcoming", "ongoing", "completed"] as const).map((filter) => (
              <button
                key={filter}
                onClick={() => setActiveFilter(filter)}
                className={`px-3 py-1 text-sm rounded-full transition-all ${
                  activeFilter === filter
                    ? "bg-accent/15 text-accent border border-accent/30"
                    : "bg-secondary/50 text-muted-foreground hover:text-foreground border border-transparent"
                }`}
              >
                {filter === "all" ? "All" : filter.charAt(0).toUpperCase() + filter.slice(1)}
              </button>
            ))}
          </div>
        </div>
        
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredChallenges.length > 0 ? (
            filteredChallenges.map((challenge, index) => (
              <ChallengeCard key={challenge.id} challenge={challenge} index={index} />
            ))
          ) : (
            <div className="col-span-full py-16 text-center">
              <p className="text-lg text-muted-foreground">
                No {activeFilter !== "all" ? activeFilter : ""} challenges found.
              </p>
            </div>
          )}
        </div>
      </div>

      {isCreateModalOpen && (
        <CreateChallenge
          onClose={() => setIsCreateModalOpen(false)}
          onChallengeCreated={handleCreateChallenge}
        />
      )}
    </Layout>
  );
};

export default Challenges;
