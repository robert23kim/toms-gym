import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Plus } from "lucide-react";
import Layout from "../components/Layout";
import CompetitionCard from "../components/CompetitionCard";
import CreateCompetition from "../components/CreateCompetition";
import { Competition, CompetitionStatus } from "../lib/types";
import axios from "axios";

const Competitions = () => {
  const [activeFilter, setActiveFilter] = useState<CompetitionStatus | "all">("all");
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [competitions, setCompetitions] = useState<Competition[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCompetitions();
  }, []);

  const fetchCompetitions = async () => {
    try {
      const response = await axios.get('https://my-app-834341357827.us-east1.run.app/competitions');
      const dbCompetitions = response.data.competitions;
      
      // Transform the database competitions to match our frontend type
      const transformedCompetitions: Competition[] = dbCompetitions.map((comp: any) => {
        // Determine default image based on gender
        const defaultImage = comp.gender === 'M' 
          ? 'https://images.unsplash.com/photo-1571902943202-507ec2618e8f?w=800&auto=format&fit=crop&q=60&ixlib=rb-4.0.3'
          : comp.gender === 'F'
          ? 'https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=800&auto=format&fit=crop&q=60&ixlib=rb-4.0.3'
          : 'https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=800&auto=format&fit=crop&q=60&ixlib=rb-4.0.3';

        return {
          id: comp.id.toString(),
          title: comp.name,
          date: comp.start_date,
          registrationDeadline: comp.end_date,
          location: comp.location,
          description: `Competition for ${comp.gender === 'M' ? 'Male' : comp.gender === 'F' ? 'Female' : 'Mixed'} athletes with ${comp.lifttypes.join(', ')} lifts and ${comp.weightclasses.join(', ')} weight classes`,
          image: defaultImage,
          status: determineStatus(comp.start_date, comp.end_date),
          categories: [...comp.lifttypes, ...comp.weightclasses],
          participants: [],
          prizePool: {
            first: 1000,
            second: 500,
            third: 250,
            total: 1750
          }
        };
      });

      setCompetitions(transformedCompetitions);
      setError(null);
    } catch (err) {
      console.error('Error fetching competitions:', err);
      setError('Failed to load competitions. Please try again later.');
    } finally {
      setIsLoading(false);
    }
  };

  const determineStatus = (startDate: string, endDate: string): CompetitionStatus => {
    const now = new Date();
    const start = new Date(startDate);
    const end = new Date(endDate);

    if (now < start) return 'upcoming';
    if (now > end) return 'completed';
    return 'ongoing';
  };

  const filteredCompetitions = activeFilter === "all" 
    ? competitions 
    : competitions.filter(competition => competition.status === activeFilter);

  const handleCreateCompetition = async (newCompetition: Omit<Competition, 'id' | 'participants'>) => {
    try {
      // Transform the frontend competition data to match the backend format
      const backendData = {
        name: newCompetition.title,
        location: newCompetition.location,
        lifttypes: newCompetition.categories.filter(cat => 
          ['Squat', 'Bench Press', 'Deadlift'].includes(cat)
        ),
        weightclasses: newCompetition.categories.filter(cat => 
          !['Squat', 'Bench Press', 'Deadlift'].includes(cat)
        ),
        gender: newCompetition.description.includes('Male') ? 'M' : 
                newCompetition.description.includes('Female') ? 'F' : 'X',
        start_date: newCompetition.date,
        end_date: newCompetition.registrationDeadline
      };

      await axios.post('https://my-app-834341357827.us-east1.run.app/create_competition', backendData);
      
      // Refresh the competitions list
      await fetchCompetitions();
      setIsCreateModalOpen(false);
    } catch (err) {
      console.error('Error creating competition:', err);
      // You might want to show an error message to the user here
    }
  };

  if (isLoading) {
    return (
      <Layout>
        <div className="flex items-center justify-center min-h-[50vh]">
          <div className="text-lg text-muted-foreground">Loading competitions...</div>
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <div className="flex items-center justify-center min-h-[50vh]">
          <div className="text-lg text-red-500">{error}</div>
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
            <h1 className="text-3xl font-semibold mb-2">Competitions</h1>
            <p className="text-muted-foreground">
              Browse all available lifting competitions and find the perfect one for you.
            </p>
          </div>

          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-md hover:bg-accent/90 transition-colors"
          >
            <Plus size={20} />
            <span>Create Competition</span>
          </button>
        </div>
      </motion.div>

      <div className="mb-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-semibold">All Competitions</h2>
          
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
          {filteredCompetitions.length > 0 ? (
            filteredCompetitions.map((competition, index) => (
              <CompetitionCard key={competition.id} competition={competition} index={index} />
            ))
          ) : (
            <div className="col-span-full py-16 text-center">
              <p className="text-lg text-muted-foreground">
                No {activeFilter !== "all" ? activeFilter : ""} competitions found.
              </p>
            </div>
          )}
        </div>
      </div>

      {isCreateModalOpen && (
        <CreateCompetition
          onClose={() => setIsCreateModalOpen(false)}
          onSubmit={handleCreateCompetition}
        />
      )}
    </Layout>
  );
};

export default Competitions;
