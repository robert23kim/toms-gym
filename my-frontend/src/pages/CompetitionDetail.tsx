
import React from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { getCompetitionById } from "../lib/data";
import Layout from "../components/Layout";
import { Calendar, MapPin, Clock, Users, ArrowLeft } from "lucide-react";

const CompetitionDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const competition = getCompetitionById(id || "");

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
          <div className="glass p-6 rounded-xl mb-8">
            <h2 className="text-2xl font-semibold mb-4">About the Competition</h2>
            <p className="text-muted-foreground whitespace-pre-line">
              {competition.description}
            </p>
          </div>

          <div className="glass p-6 rounded-xl">
            <h2 className="text-2xl font-semibold mb-6">Participants</h2>
            <div className="space-y-6">
              {competition.participants.map((participant, index) => (
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
                      to={`/competitions/${competition.id}/participants/${participant.id}/video`}
                      className="px-3 py-1 text-sm bg-secondary hover:bg-secondary/70 rounded-md transition-colors"
                    >
                      View Lifts
                    </Link>
                  </div>
                </motion.div>
              ))}
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
