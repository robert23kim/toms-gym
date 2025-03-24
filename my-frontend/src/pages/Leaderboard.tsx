import React, { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import Layout from '../components/Layout';
import { competitions } from '../lib/data';
import { Participant } from '../lib/types';

type LiftCategory = 'squat' | 'bench' | 'deadlift' | 'total';

const Leaderboard = () => {
  const [activeCategory, setActiveCategory] = useState<LiftCategory>('total');
  const [selectedWeightClass, setSelectedWeightClass] = useState<string>('all');
  const [selectedLocation, setSelectedLocation] = useState<string>('all');

  // Get all participants and their locations
  const { allParticipants, locations } = useMemo(() => {
    const participants = competitions.flatMap(c => 
      c.participants.map(p => ({
        ...p,
        location: c.location // Add competition location to participant
      }))
    );
    
    const uniqueLocations = Array.from(
      new Set(competitions.map(c => c.location))
    ).sort();

    return { allParticipants: participants, locations: uniqueLocations };
  }, []);

  // Get all unique weight classes
  const weightClasses = useMemo(() => 
    Array.from(
      new Set(allParticipants.map(p => p.weightClass))
    ).sort()
  , [allParticipants]);

  // Filter and sort participants based on active category, weight class, and location
  const getFilteredAndSortedParticipants = () => {
    let filtered = allParticipants;
    
    if (selectedWeightClass !== 'all') {
      filtered = filtered.filter(p => p.weightClass === selectedWeightClass);
    }

    if (selectedLocation !== 'all') {
      filtered = filtered.filter(p => p.location === selectedLocation);
    }

    return filtered.sort((a, b) => {
      if (activeCategory === 'total') {
        return (b.totalWeight || 0) - (a.totalWeight || 0);
      }
      
      const getMaxLift = (participant: Participant & { location: string }, type: LiftCategory) => {
        return participant.attempts?.[type]?.reduce((max, current) => Math.max(max, current), 0) || 0;
      };

      return getMaxLift(b, activeCategory) - getMaxLift(a, activeCategory);
    });
  };

  const sortedParticipants = getFilteredAndSortedParticipants();

  return (
    <Layout>
      <section className="mb-20">
        <motion.div
          className="text-center mb-12"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        >
          <h1 className="text-4xl font-bold mb-4">Global Leaderboard</h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Track the strongest lifts across all competitions and weight classes.
          </p>
        </motion.div>

        <div className="mb-8 flex flex-wrap gap-4 justify-center">
          <div className="flex space-x-2">
            {(['total', 'squat', 'bench', 'deadlift'] as const).map((category) => (
              <button
                key={category}
                onClick={() => setActiveCategory(category)}
                className={`px-4 py-2 rounded-full transition-all ${
                  activeCategory === category
                    ? "bg-accent text-white shadow-sm"
                    : "bg-secondary hover:bg-secondary/70 text-foreground"
                }`}
              >
                {category.charAt(0).toUpperCase() + category.slice(1)}
              </button>
            ))}
          </div>

          <div className="flex gap-2">
            <select
              value={selectedWeightClass}
              onChange={(e) => setSelectedWeightClass(e.target.value)}
              className="px-4 py-2 rounded-full bg-secondary text-foreground"
            >
              <option value="all">All Weight Classes</option>
              {weightClasses.map((weightClass) => (
                <option key={weightClass} value={weightClass}>
                  {weightClass}
                </option>
              ))}
            </select>

            <select
              value={selectedLocation}
              onChange={(e) => setSelectedLocation(e.target.value)}
              className="px-4 py-2 rounded-full bg-secondary text-foreground"
            >
              <option value="all">All Locations</option>
              {locations.map((location) => (
                <option key={location} value={location}>
                  {location}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="glass rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-secondary/50">
                  <th className="px-6 py-4 text-left">Rank</th>
                  <th className="px-6 py-4 text-left">Athlete</th>
                  <th className="px-6 py-4 text-left">Weight Class</th>
                  <th className="px-6 py-4 text-left">Country</th>
                  <th className="px-6 py-4 text-left">Location</th>
                  <th className="px-6 py-4 text-right">Best {activeCategory.charAt(0).toUpperCase() + activeCategory.slice(1)}</th>
                </tr>
              </thead>
              <tbody>
                {sortedParticipants.map((participant, index) => {
                  const bestLift = activeCategory === 'total'
                    ? participant.totalWeight
                    : participant.attempts?.[activeCategory]?.reduce((max, current) => Math.max(max, current), 0);

                  return (
                    <motion.tr
                      key={participant.id}
                      className="border-t border-border hover:bg-secondary/20"
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3, delay: index * 0.05 }}
                    >
                      <td className="px-6 py-4">
                        <span className="font-medium">{index + 1}</span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <img
                            src={participant.avatar}
                            alt={participant.name}
                            className="w-10 h-10 rounded-full"
                          />
                          <span className="font-medium">{participant.name}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4">{participant.weightClass}</td>
                      <td className="px-6 py-4">{participant.country}</td>
                      <td className="px-6 py-4">{participant.location}</td>
                      <td className="px-6 py-4 text-right font-medium">
                        {bestLift ? `${bestLift}kg` : 'N/A'}
                      </td>
                    </motion.tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </Layout>
  );
};

export default Leaderboard; 