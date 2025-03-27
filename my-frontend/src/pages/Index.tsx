import React, { useState } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import ChallengeCard from "../components/ChallengeCard";
import Layout from "../components/Layout";
import TopLifts from "../components/TopLifts";
import { Challenge } from "../lib/types";

const Index = () => {
  const [activeFilter, setActiveFilter] = useState<"all" | "upcoming" | "ongoing" | "completed">("all");

  // Mock data for featured challenges
  const featuredChallenges: Challenge[] = [
    {
      id: 1,
      title: "Summer Powerlifting Championship",
      date: "2024-07-15",
      registrationDeadline: "2024-07-01",
      location: "New York, NY",
      description: "Join us for the biggest powerlifting event of the summer!",
      image: "https://images.unsplash.com/photo-1571902943202-507ec2618e8f?w=800&auto=format&fit=crop&q=60&ixlib=rb-4.0.3",
      status: "upcoming",
      categories: ["Powerlifting", "Open"],
      participants: 0,
      prizePool: {
        first: 1000,
        second: 500,
        third: 250,
        total: 1750
      }
    },
    {
      id: 2,
      title: "Women's Weightlifting Open",
      date: "2024-06-20",
      registrationDeadline: "2024-06-05",
      location: "Los Angeles, CA",
      description: "A celebration of women's strength and athleticism.",
      image: "https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=800&auto=format&fit=crop&q=60&ixlib=rb-4.0.3",
      status: "upcoming",
      categories: ["Weightlifting", "Women"],
      participants: 0,
      prizePool: {
        first: 800,
        second: 400,
        third: 200,
        total: 1400
      }
    }
  ];

  const filteredChallenges = activeFilter === "all" 
    ? featuredChallenges 
    : featuredChallenges.filter(challenge => challenge.status === activeFilter);

  return (
    <Layout>
      <div className="flex flex-col lg:flex-row gap-8">
        <div className="flex-1">
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
                  Online Lifting Challenges for Everyone
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
                  <Link 
                    to="/challenges"
                    className="inline-block px-6 py-3 bg-accent text-white font-medium rounded-md shadow-lg hover:bg-accent/90 transition-all hover-lift"
                  >
                    Browse Challenges
                  </Link>
                </motion.div>
              </div>
            </motion.div>
            
            <div id="challenges" className="scroll-mt-20">
              <div className="flex justify-between items-center mb-8">
                <motion.h2 
                  className="text-3xl font-semibold"
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.5, ease: "easeOut" }}
                >
                  Open Challenges
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
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
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
          </section>
          
          <section className="mb-20">
            <motion.div 
              className="text-center mb-12"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease: "easeOut" }}
            >
              <h2 className="text-3xl font-semibold mb-4">How It Works</h2>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                Participating in online lifting challenges has never been easier. Follow these simple steps to start your competitive journey.
              </p>
            </motion.div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {[
                {
                  title: "Register",
                  description: "Choose a challenge that matches your preferences and complete the registration process.",
                  icon: "📝",
                },
                {
                  title: "Record",
                  description: "Record your lifts following the challenge guidelines and submit them before the deadline.",
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
              <h2 className="text-3xl font-semibold mb-4">Ready to Show Your Strength?</h2>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                Join our upcoming challenges and compete for prizes while pushing your limits.
              </p>
            </motion.div>
            
            <motion.div 
              className="glass p-8 rounded-lg text-center max-w-xl mx-auto"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, ease: "easeOut" }}
            >
              <div className="space-y-6">
                <div className="flex items-center justify-center gap-4">
                  <div className="text-4xl">🏋️‍♂️</div>
                  <div className="text-left">
                    <h3 className="text-xl font-semibold">Summer Powerlifting Championship</h3>
                    <p className="text-muted-foreground">July 15, 2024 • Prize Pool: $1,750</p>
                  </div>
                </div>
                <div className="flex items-center justify-center gap-4">
                  <div className="text-4xl">💪</div>
                  <div className="text-left">
                    <h3 className="text-xl font-semibold">Women's Weightlifting Open</h3>
                    <p className="text-muted-foreground">June 20, 2024 • Prize Pool: $1,400</p>
                  </div>
                </div>
                <div className="pt-4">
                  <Link
                    to="/challenges"
                    className="inline-block px-8 py-4 bg-accent text-white font-medium rounded-md shadow-lg hover:bg-accent/90 transition-all hover-lift text-lg"
                  >
                    Sign Up for a Challenge
                  </Link>
                </div>
              </div>
            </motion.div>
          </section>
        </div>
        
        <div className="lg:w-80 flex-shrink-0 sticky top-20 h-fit">
          <TopLifts />
        </div>
      </div>
    </Layout>
  );
};

export default Index;
