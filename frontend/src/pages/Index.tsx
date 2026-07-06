import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { ArrowRight, Dumbbell, Target, Flag } from "lucide-react";
import ChallengeCard from "../components/ChallengeCard";
import Layout from "../components/Layout";
import TopLifts from "../components/TopLifts";
import { Challenge } from "../lib/types";
import { getFeaturedChallenges } from "../lib/api";
import liftAnalysis from "../assets/lift-analysis.jpeg";
import bowlAnalysis from "../assets/bowl-analysis.jpeg";
import golfAnalysis from "../assets/golf-analysis.jpeg";

// The three analysis verticals — each card leads with real annotated output
// and links straight into that vertical's upload flow.
const features = [
  {
    key: "lift",
    title: "Lifting form analysis",
    description:
      "Per-rep grades on squat, bench, deadlift, and curls, with an annotated replay of every rep.",
    image: liftAnalysis,
    imageAlt: "AI rep breakdown grading a deadlift with per-metric scores",
    icon: Dumbbell,
    uploadTo: "/upload",
    uploadLabel: "Upload a lift",
    hubTo: "/lift",
  },
  {
    key: "bowl",
    title: "Bowling ball tracking",
    description:
      "See your ball's trajectory, entry board, and pocket impact tracked frame by frame.",
    image: bowlAnalysis,
    imageAlt: "Bowling ball trajectory traced down the lane to the pins",
    icon: Target,
    uploadTo: "/bowling/upload",
    uploadLabel: "Upload a throw",
    hubTo: "/bowl",
  },
  {
    key: "golf",
    title: "Scorecard to handicap",
    description:
      "Snap a photo of your scorecard — we read every hole and compute your handicap.",
    image: golfAnalysis,
    imageAlt: "Golf round with per-hole scores read from a scorecard photo",
    icon: Flag,
    uploadTo: "/golf/upload",
    uploadLabel: "Snap a scorecard",
    hubTo: "/golf",
  },
];

const Index = () => {
  const [activeFilter, setActiveFilter] = useState<"all" | "upcoming" | "ongoing" | "completed">("all");
  const [featuredChallenges, setFeaturedChallenges] = useState<Challenge[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchChallenges = async () => {
      try {
        setLoading(true);
        const challenges = await getFeaturedChallenges(2);
        setFeaturedChallenges(challenges);
      } catch (error) {
        console.error("Error fetching featured challenges:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchChallenges();
  }, []);

  const filteredChallenges = activeFilter === "all"
    ? featuredChallenges
    : featuredChallenges.filter(challenge => challenge.status === activeFilter);

  return (
    <Layout>
      <div className="flex flex-col lg:flex-row gap-8">
        <div className="flex-1 min-w-0">
          {/* Hero — lead with the analysis value prop */}
          <section className="mb-20">
            <motion.div
              className="max-w-3xl mb-10"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease: "easeOut" }}
            >
              <h1 className="text-4xl md:text-5xl font-bold mb-4 leading-tight">
                Get AI analysis of your lift, bowl, or round in minutes.
              </h1>
              <p className="text-lg text-muted-foreground">
                Upload a video or snap a photo and get annotated feedback you can't get
                anywhere else. No signup — just your email.
              </p>
            </motion.div>

            {/* Three feature cards — each starts an upload */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {features.map((feature, index) => {
                const Icon = feature.icon;
                return (
                  <motion.div
                    key={feature.key}
                    className="group glass-dark rounded-2xl overflow-hidden shadow-lg flex flex-col"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: index * 0.1, ease: "easeOut" }}
                  >
                    <Link to={feature.uploadTo} className="block">
                      <div className="relative aspect-[16/10] overflow-hidden bg-black">
                        <img
                          src={feature.image}
                          alt={feature.imageAlt}
                          loading="lazy"
                          className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
                        <div className="absolute bottom-3 left-4 flex items-center gap-2 text-white">
                          <Icon className="w-5 h-5" />
                          <span className="font-semibold">{feature.title}</span>
                        </div>
                      </div>
                    </Link>

                    <div className="flex flex-col flex-1 p-5">
                      <p className="text-muted-foreground mb-5 flex-1">{feature.description}</p>
                      <div className="flex items-center justify-between gap-3">
                        <Link
                          to={feature.uploadTo}
                          className="inline-flex items-center gap-2 px-4 py-2 bg-accent text-white font-medium rounded-md shadow-sm hover:bg-accent/90 transition-all"
                        >
                          {feature.uploadLabel}
                          <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" />
                        </Link>
                        <Link
                          to={feature.hubTo}
                          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                        >
                          Learn more
                        </Link>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </section>

          {/* How It Works — passwordless reality (T3) */}
          <section className="mb-20">
            <motion.div
              className="text-center mb-12"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease: "easeOut" }}
            >
              <h2 className="text-3xl font-semibold mb-4">How It Works</h2>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                No account, no password. From upload to analysis in three steps.
              </p>
            </motion.div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {[
                {
                  title: "No signup — just your email",
                  description: "No account or password needed. Enter your email so we can send you the results.",
                  icon: "📧",
                },
                {
                  title: "Upload",
                  description: "Record your lift or throw, or snap a photo of your scorecard, and send it in.",
                  icon: "🎥",
                },
                {
                  title: "Get your analysis",
                  description: "In minutes you get annotated output — rep grades, ball trajectory, or your handicap.",
                  icon: "📊",
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

          {/* Competitions — demoted below the analysis pitch */}
          <section>
            <div id="challenges" className="scroll-mt-20">
              <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 mb-8">
                <div>
                  <motion.h2
                    className="text-3xl font-semibold"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.5, ease: "easeOut" }}
                  >
                    Or join a challenge
                  </motion.h2>
                  <p className="text-muted-foreground mt-1">
                    Compete with the community and climb the leaderboard.
                  </p>
                </div>

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
                {loading ? (
                  <div className="col-span-full py-16 text-center">
                    <div className="flex justify-center">
                      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-accent"></div>
                    </div>
                    <p className="mt-4 text-lg text-muted-foreground">Loading challenges...</p>
                  </div>
                ) : filteredChallenges.length > 0 ? (
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

              <div className="mt-8 text-center">
                <Link
                  to="/challenges"
                  className="inline-flex items-center gap-2 px-6 py-3 bg-secondary hover:bg-secondary/70 text-foreground font-medium rounded-md transition-all"
                >
                  View all challenges
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            </div>
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
