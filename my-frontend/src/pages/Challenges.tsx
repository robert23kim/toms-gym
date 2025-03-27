import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { Plus } from "lucide-react";
import Layout from "../components/Layout";
import ChallengeCard from "../components/ChallengeCard";
import CreateChallenge from "../components/CreateChallenge";
import { Challenge } from "../lib/types";
import axios from "axios";

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
      const response = await axios.get('https://my-app-834341357827.us-east1.run.app/competitions');
      const dbChallenges = response.data.competitions;

      // Transform the database challenges to match our frontend type
      const transformedChallenges = dbChallenges.map((challenge: any) => ({
        id: challenge.id,
        title: challenge.name,
        date: challenge.start_date,
        registrationDeadline: challenge.end_date,
        location: challenge.location,
        description: challenge.description || '',
        image: challenge.image || 'https://images.unsplash.com/photo-1571902943202-507ec2618e8f?w=800&auto=format&fit=crop&q=60&ixlib=rb-4.0.3',
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

      setChallenges(transformedChallenges);
    } catch (err) {
      console.error('Error fetching challenges:', err);
      setError('Failed to load challenges. Please try again later.');
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
        className="mb-8"
      >
        <div className="flex justify-between items-center mb-4">
          <div>
            <h1 className="text-3xl font-semibold mb-2">Challenges</h1>
            <p className="text-muted-foreground">
              Browse all available lifting challenges and find the perfect one for you.
            </p>
          </div>

          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-md hover:bg-accent/90 transition-colors"
          >
            <Plus size={20} />
            <span>Create Challenge</span>
          </button>
        </div>
      </motion.div>

      {error && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-md text-red-500">
          {error}
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
                    ? "bg-accent text-white shadow-sm"
                    : "bg-secondary hover:bg-secondary/70 text-foreground"
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
          isOpen={isCreateModalOpen}
          onClose={() => setIsCreateModalOpen(false)}
          onChallengeCreated={handleCreateChallenge}
        />
      )}
    </Layout>
  );
};

export default Challenges;
