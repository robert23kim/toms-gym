import React from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { getCompetitionById, sampleLifts } from "../lib/data";
import Layout from "../components/Layout";
import { Calendar, MapPin, Clock, Users, ArrowLeft, Trophy, Play, Award } from "lucide-react";

const CompetitionDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const competition = getCompetitionById(id || "");

  // Helper function to get best lifts
  const getBestLifts = () => {
    if (!competition) return null;

    const categories = ['squat', 'bench', 'deadlift'] as const;
    const bestLifts = categories.map(category => {
      const best = competition.participants
        .map(participant => {
          const maxAttempt = participant.attempts?.[category]?.reduce((max, current) => Math.max(max, current), 0) || 0;
          // Find the corresponding lift video
          const lift = sampleLifts.find(l => 
            l.participantId === participant.id && 
            l.type === category && 
            l.weight === maxAttempt
          ) || sampleLifts.find(l => l.type === category); // Fallback to any lift of this type

          return {
            participant,
            weight: maxAttempt,
            liftId: lift?.id
          };
        })
        .sort((a, b) => b.weight - a.weight)[0];

      // Add thumbnail based on category
      const thumbnail = category === 'squat' 
        ? 'https://images.unsplash.com/photo-1541534741688-6078c6bfb5c5?q=80&w=2669&auto=format&fit=crop'
        : category === 'bench'
        ? 'https://images.unsplash.com/photo-1583454110551-21f2fa2afe61?q=80&w=2670&auto=format&fit=crop'
        : 'https://images.unsplash.com/photo-1603287681836-b174ce5074c2?q=80&w=2671&auto=format&fit=crop';

      return {
        category,
        thumbnail,
        ...best
      };
    });

    return bestLifts;
  };

  if (!competition) {
    return (
      <Layout>
        <div className="min-h-[60vh] flex flex-col items-center justify-center">
          <h2 className="text-2xl font-semibold mb-4">Competition Not Found</h2>
          <p className="text-muted-foreground mb-6">
            The competition you're looking for doesn't exist or has been removed.
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

  const formatDate = (dateString: string) => {
    const options: Intl.DateTimeFormatOptions = {
      year: "numeric",
      month: "long",
      day: "numeric",
    };
    return new Date(dateString).toLocaleDateString(undefined, options);
  };

  const bestLifts = getBestLifts();

  return (
    <Layout>
      <div className="mb-6 flex items-center">
        <button
          onClick={() => navigate("/")}
          className="mr-4 flex items-center text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft size={16} className="mr-1" /> Back
        </button>
        <h1 className="text-2xl font-semibold">Competition Details</h1>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative rounded-xl overflow-hidden glass-dark shadow-lg mb-10"
      >
        <div className="absolute inset-0 z-0">
          <img
            src={competition.image}
            alt={competition.title}
            className="w-full h-full object-cover object-center opacity-80"
          />
          <div className="absolute inset-0 bg-gradient-to-r from-black/70 to-black/30"></div>
        </div>

        <div className="relative z-10 px-6 py-16 md:py-24 max-w-4xl">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium mb-4 ${
                competition.status === "upcoming"
                  ? "bg-blue-100 text-blue-800"
                  : competition.status === "ongoing"
                  ? "bg-green-100 text-green-800"
                  : "bg-gray-100 text-gray-800"
              }`}
            >
              {competition.status.charAt(0).toUpperCase() + competition.status.slice(1)}
            </span>
          </motion.div>

          <motion.h1
            className="text-3xl md:text-4xl lg:text-5xl font-bold text-white mb-6"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            {competition.title}
          </motion.h1>

          <motion.div
            className="flex flex-wrap gap-6 text-white"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <div className="flex items-center">
              <Calendar size={18} className="mr-2 text-white/80" />
              <span>{formatDate(competition.date)}</span>
            </div>
            <div className="flex items-center">
              <MapPin size={18} className="mr-2 text-white/80" />
              <span>{competition.location}</span>
            </div>
            <div className="flex items-center">
              <Clock size={18} className="mr-2 text-white/80" />
              <span>Registration Deadline: {formatDate(competition.registrationDeadline)}</span>
            </div>
            <div className="flex items-center">
              <Users size={18} className="mr-2 text-white/80" />
              <span>{competition.participants.length} Participants</span>
            </div>
          </motion.div>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="lg:col-span-2"
        >
          {/* Prize Pool Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="glass p-6 rounded-xl mb-8"
          >
            <div className="flex items-center gap-2 mb-6">
              <Award className="w-6 h-6 text-yellow-400" />
              <h2 className="text-2xl font-semibold">Prize Pool</h2>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="glass p-6 rounded-lg text-center bg-gradient-to-b from-yellow-500/10 to-transparent">
                <div className="text-yellow-500 font-bold text-3xl mb-2">
                  {competition.prizePool.first.toLocaleString()} LD
                </div>
                <div className="text-sm text-muted-foreground">1st Place</div>
              </div>
              
              <div className="glass p-6 rounded-lg text-center bg-gradient-to-b from-gray-400/10 to-transparent">
                <div className="text-gray-400 font-bold text-2xl mb-2">
                  {competition.prizePool.second.toLocaleString()} LD
                </div>
                <div className="text-sm text-muted-foreground">2nd Place</div>
              </div>
              
              <div className="glass p-6 rounded-lg text-center bg-gradient-to-b from-amber-600/10 to-transparent">
                <div className="text-amber-600 font-bold text-2xl mb-2">
                  {competition.prizePool.third.toLocaleString()} LD
                </div>
                <div className="text-sm text-muted-foreground">3rd Place</div>
              </div>
            </div>
            
            <div className="mt-6 text-center text-sm text-muted-foreground">
              Total Prize Pool: <span className="font-semibold text-foreground">{competition.prizePool.total.toLocaleString()} LD</span>
            </div>
          </motion.div>

          {/* Best Lifts Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="glass p-6 rounded-xl mb-8"
          >
            <div className="flex items-center gap-2 mb-6">
              <Trophy className="w-6 h-6 text-yellow-400" />
              <h2 className="text-2xl font-semibold">Best Lifts</h2>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {bestLifts?.map(({ category, participant, weight, thumbnail, liftId }) => (
                <div key={category} className="glass overflow-hidden rounded-lg">
                  <div className="relative aspect-video mb-3">
                    <img
                      src={thumbnail}
                      alt={`${category} lift`}
                      className="absolute inset-0 w-full h-full object-cover"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
                    <div className="absolute bottom-2 left-2 right-2 flex items-center justify-between text-white">
                      <span className="text-lg font-medium capitalize">{category}</span>
                      <span className="text-xl font-bold">{weight}kg</span>
                    </div>
                  </div>
                  
                  <div className="p-4">
                    <div className="flex items-center gap-3 mb-3">
                      <img
                        src={participant.avatar}
                        alt={participant.name}
                        className="w-10 h-10 rounded-full"
                      />
                      <div>
                        <div className="font-medium">{participant.name}</div>
                        <div className="text-sm text-muted-foreground">{participant.weightClass}</div>
                      </div>
                    </div>
                    
                    <Link
                      to={`/competitions/${competition.id}/participants/${participant.id}/video/${liftId || 'l1'}`}
                      className="flex items-center justify-center gap-1 w-full px-3 py-2 text-sm bg-secondary hover:bg-secondary/70 rounded-md transition-colors"
                    >
                      <Play className="w-4 h-4" />
                      Watch Lift
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>

          <div className="glass p-6 rounded-xl mb-8">
            <h2 className="text-2xl font-semibold mb-4">About the Competition</h2>
            <p className="text-muted-foreground whitespace-pre-line">
              {competition.description}
            </p>
          </div>

          <div className="glass p-6 rounded-xl">
            <h2 className="text-2xl font-semibold mb-6">Participants</h2>
            <div className="space-y-6">
              {competition.participants.map((participant, index) => {
                // Find the participant's best lift video for each category
                const participantLifts = sampleLifts.filter(
                  lift => lift.participantId === participant.id
                );
                const firstLiftId = participantLifts[0]?.id || 'l1';

                return (
                  <motion.div
                    key={participant.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3, delay: 0.1 * index }}
                    className="flex items-center justify-between border-b border-border/50 pb-4 last:border-0 last:pb-0"
                  >
                    <div className="flex items-center">
                      <img
                        src={participant.avatar}
                        alt={participant.name}
                        className="w-12 h-12 rounded-full mr-4 object-cover"
                      />
                      <div>
                        <h3 className="font-medium">{participant.name}</h3>
                        <div className="flex items-center text-sm text-muted-foreground">
                          <span className="mr-2">{participant.weightClass}</span>
                          <span>|</span>
                          <span className="ml-2">{participant.country}</span>
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-4">
                      {participant.totalWeight && (
                        <div className="text-right">
                          <div className="text-sm text-muted-foreground">Total</div>
                          <div className="font-medium">{participant.totalWeight}kg</div>
                        </div>
                      )}
                      
                      <Link
                        to={`/competitions/${competition.id}/participants/${participant.id}/video/${firstLiftId}`}
                        className="px-3 py-1 text-sm bg-secondary hover:bg-secondary/70 rounded-md transition-colors"
                      >
                        View Lifts
                      </Link>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <div className="glass p-6 rounded-xl sticky top-20">
            <h2 className="text-xl font-semibold mb-4">Categories</h2>
            <div className="flex flex-wrap gap-2 mb-6">
              {competition.categories.map((category) => (
                <span
                  key={category}
                  className="px-3 py-1 text-sm bg-secondary rounded-md"
                >
                  {category}
                </span>
              ))}
            </div>

            <div className="mb-6">
              <h3 className="text-lg font-medium mb-3">Schedule</h3>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Registration Ends:</span>
                  <span>{formatDate(competition.registrationDeadline)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Competition Date:</span>
                  <span>{formatDate(competition.date)}</span>
                </div>
              </div>
            </div>

            <button className="w-full px-4 py-3 bg-accent text-white font-medium rounded-md hover:bg-accent/90 transition-colors mb-3">
              Register Now
            </button>
            <button className="w-full px-4 py-3 bg-secondary text-foreground font-medium rounded-md hover:bg-secondary/70 transition-colors">
              Share Competition
            </button>
          </div>
        </motion.div>
      </div>
    </Layout>
  );
};

export default CompetitionDetail;
