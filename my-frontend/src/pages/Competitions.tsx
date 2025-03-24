
import React, { useState } from "react";
import { motion } from "framer-motion";
import Layout from "../components/Layout";
import { competitions } from "../lib/data";
import CompetitionCard from "../components/CompetitionCard";
import { CompetitionStatus } from "../lib/types";

const Competitions = () => {
  const [activeFilter, setActiveFilter] = useState<CompetitionStatus | "all">("all");

  const filteredCompetitions = activeFilter === "all" 
    ? competitions 
    : competitions.filter(competition => competition.status === activeFilter);

  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="mb-8"
      >
        <h1 className="text-3xl font-semibold mb-2">Competitions</h1>
        <p className="text-muted-foreground">
          Browse all available lifting competitions and find the perfect one for you.
        </p>
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
    </Layout>
  );
};

export default Competitions;
