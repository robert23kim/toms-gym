
import React, { useState } from "react";
import { motion } from "framer-motion";
import Layout from "../components/Layout";
import { competitions } from "../lib/data";
import { Search } from "lucide-react";

const Athletes = () => {
  const [searchQuery, setSearchQuery] = useState("");
  
  // Extract unique participants from all competitions
  const allParticipants = competitions.flatMap(comp => comp.participants);
  const uniqueParticipants = Array.from(
    new Map(allParticipants.map(item => [item.id, item])).values()
  );
  
  // Filter participants based on search query
  const filteredParticipants = searchQuery 
    ? uniqueParticipants.filter(participant => 
        participant.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        participant.country.toLowerCase().includes(searchQuery.toLowerCase()) ||
        participant.weightClass.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : uniqueParticipants;

  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="mb-8"
      >
        <h1 className="text-3xl font-semibold mb-2">Athletes</h1>
        <p className="text-muted-foreground">
          Discover top lifting athletes from around the world participating in our competitions.
        </p>
      </motion.div>
      
      <div className="glass p-4 rounded-xl mb-8">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground" size={18} />
          <input
            type="text"
            placeholder="Search athletes by name, country, or weight class..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 rounded-md border border-border bg-white/50 focus:outline-none focus:ring-2 focus:ring-accent/50"
          />
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredParticipants.length > 0 ? (
          filteredParticipants.map((participant, index) => (
            <motion.div
              key={participant.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.05 }}
              className="glass p-6 rounded-xl"
            >
              <div className="flex items-center mb-4">
                <img 
                  src={participant.avatar} 
                  alt={participant.name} 
                  className="w-16 h-16 rounded-full mr-4 object-cover"
                />
                <div>
                  <h2 className="text-xl font-medium">{participant.name}</h2>
                  <p className="text-muted-foreground">{participant.country}</p>
                </div>
              </div>
              
              <div className="flex justify-between items-center mb-4">
                <div>
                  <span className="text-sm text-muted-foreground">Weight Class</span>
                  <p className="font-medium">{participant.weightClass}</p>
                </div>
                
                {participant.totalWeight && (
                  <div>
                    <span className="text-sm text-muted-foreground">Total</span>
                    <p className="font-medium">{participant.totalWeight}kg</p>
                  </div>
                )}
              </div>
              
              {participant.attempts && (
                <div className="space-y-2 mb-4">
                  <h3 className="text-sm font-medium text-muted-foreground mb-1">Best Attempts</h3>
                  
                  <div className="grid grid-cols-3 gap-2">
                    <div className="text-center p-2 bg-secondary/40 rounded">
                      <p className="text-xs text-muted-foreground">Squat</p>
                      <p className="font-medium">
                        {Math.max(...participant.attempts.squat.filter(w => w > 0))}kg
                      </p>
                    </div>
                    <div className="text-center p-2 bg-secondary/40 rounded">
                      <p className="text-xs text-muted-foreground">Bench</p>
                      <p className="font-medium">
                        {Math.max(...participant.attempts.bench.filter(w => w > 0))}kg
                      </p>
                    </div>
                    <div className="text-center p-2 bg-secondary/40 rounded">
                      <p className="text-xs text-muted-foreground">Deadlift</p>
                      <p className="font-medium">
                        {Math.max(...participant.attempts.deadlift.filter(w => w > 0))}kg
                      </p>
                    </div>
                  </div>
                </div>
              )}
              
              <button className="w-full px-3 py-2 text-sm bg-secondary hover:bg-secondary/70 rounded-md transition-colors">
                View Athlete Profile
              </button>
            </motion.div>
          ))
        ) : (
          <div className="col-span-full py-16 text-center">
            <p className="text-lg text-muted-foreground">
              No athletes found matching your search criteria.
            </p>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default Athletes;
