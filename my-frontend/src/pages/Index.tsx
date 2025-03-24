import React, { useState } from "react";
import { motion } from "framer-motion";
import { competitions } from "../lib/data";
import CompetitionCard from "../components/CompetitionCard";
import Layout from "../components/Layout";
import TopLifts from "../components/TopLifts";
import { CompetitionStatus } from "../lib/types";

const Index = () => {
  const [activeFilter, setActiveFilter] = useState<CompetitionStatus | "all">("all");

  const filteredCompetitions = activeFilter === "all" 
    ? competitions 
    : competitions.filter(competition => competition.status === activeFilter);

  return (
    <Layout>
      <section className="mb-20">
        <motion.div 
          className="relative overflow-hidden rounded-2xl glass-dark shadow-lg mb-16"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        >
          <div className="absolute inset-0 z-0">
            <img
              src="https://images.unsplash.com/photo-1599058917765-a780eda07a3e?q=80&w=1469&auto=format&fit=crop"
              alt="Hero background"
              className="w-full h-full object-cover object-center opacity-70"
            />
            <div className="absolute inset-0 bg-gradient-to-r from-black/80 to-black/40"></div>
          </div>
          
          <div className="relative z-10 px-6 py-20 md:py-32 max-w-4xl">
            <motion.h1 
              className="text-4xl md:text-5xl font-bold text-white mb-4"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1, ease: "easeOut" }}
            >
              Online Lifting Competitions for Everyone
            </motion.h1>
            
            <motion.p 
              className="text-xl text-white/90 mb-8 max-w-2xl"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2, ease: "easeOut" }}
            >
              Compete from anywhere in the world, showcase your strength, and connect with the global lifting community.
            </motion.p>
            
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3, ease: "easeOut" }}
            >
              <a 
                href="#competitions"
                className="inline-block px-6 py-3 bg-accent text-white font-medium rounded-md shadow-lg hover:bg-accent/90 transition-all hover-lift"
              >
                Browse Competitions
              </a>
            </motion.div>
          </div>
        </motion.div>
        
        <div id="competitions" className="scroll-mt-20">
          <div className="flex justify-between items-center mb-8">
            <motion.h2 
              className="text-3xl font-semibold"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, ease: "easeOut" }}
            >
              Open Competitions
            </motion.h2>
            
            <motion.div 
              className="flex space-x-2"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, ease: "easeOut" }}
            >
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
            </motion.div>
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
      </section>
      
      <TopLifts />
      
      <section className="mb-20">
        <motion.div 
          className="text-center mb-12"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        >
          <h2 className="text-3xl font-semibold mb-4">How It Works</h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Participating in online lifting competitions has never been easier. Follow these simple steps to start your competitive journey.
          </p>
        </motion.div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {[
            {
              title: "Register",
              description: "Choose a competition that matches your preferences and complete the registration process.",
              icon: "📝",
            },
            {
              title: "Record",
              description: "Record your lifts following the competition guidelines and submit them before the deadline.",
              icon: "🎥",
            },
            {
              title: "Compete",
              description: "Get your lifts judged, see the leaderboard, and potentially win prizes and recognition.",
              icon: "🏆",
            },
          ].map((step, index) => (
            <motion.div
              key={index}
              className="relative glass p-6 rounded-lg text-center"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: index * 0.1, ease: "easeOut" }}
            >
              <div className="w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center text-3xl bg-secondary">
                {step.icon}
              </div>
              <h3 className="text-xl font-medium mb-2">{step.title}</h3>
              <p className="text-muted-foreground">{step.description}</p>
            </motion.div>
          ))}
        </div>
      </section>
      
      <section>
        <motion.div 
          className="text-center mb-12"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        >
          <h2 className="text-3xl font-semibold mb-4">Join the Community</h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Connect with lifters from around the world, share your progress, and receive support from the community.
          </p>
        </motion.div>
        
        <motion.div 
          className="glass p-8 rounded-lg text-center max-w-xl mx-auto"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        >
          <form className="space-y-4">
            <div>
              <input
                type="email"
                placeholder="Your email address"
                className="w-full px-4 py-3 rounded-md border border-border bg-white/50 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-accent/50"
              />
            </div>
            <button
              type="submit"
              className="w-full px-6 py-3 bg-accent text-white font-medium rounded-md shadow hover:bg-accent/90 transition-all hover-lift"
            >
              Subscribe to Newsletter
            </button>
          </form>
        </motion.div>
      </section>
    </Layout>
  );
};

export default Index;
