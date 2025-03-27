import React from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { Calendar, MapPin, Users, Trophy } from "lucide-react";
import { Challenge } from "../lib/types";

interface ChallengeCardProps {
  challenge: Challenge;
  index: number;
}

const ChallengeCard: React.FC<ChallengeCardProps> = ({ challenge, index }) => {
  const cardVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { delay: index * 0.1 } }
  };

  return (
    <motion.div
      variants={cardVariants}
      initial="hidden"
      animate="visible"
      className="bg-card rounded-lg overflow-hidden shadow-lg hover:shadow-xl transition-shadow"
    >
      <Link to={`/challenges/${challenge.id}`}>
        <div className="relative h-48">
          <img
            src={challenge.image}
            alt={challenge.title}
            className="w-full h-full object-cover"
          />
          <div className="absolute top-2 right-2">
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
              challenge.status === 'upcoming' ? 'bg-blue-500 text-white' :
              challenge.status === 'ongoing' ? 'bg-green-500 text-white' :
              'bg-gray-500 text-white'
            }`}>
              {challenge.status.charAt(0).toUpperCase() + challenge.status.slice(1)}
            </span>
          </div>
        </div>
        <div className="p-4">
          <h3 className="text-xl font-semibold mb-2">{challenge.title}</h3>
          <div className="space-y-2 text-muted-foreground">
            <div className="flex items-center gap-2">
              <Calendar size={16} />
              <span>{new Date(challenge.date).toLocaleDateString()}</span>
            </div>
            <div className="flex items-center gap-2">
              <MapPin size={16} />
              <span>{challenge.location}</span>
            </div>
            <div className="flex items-center gap-2">
              <Users size={16} />
              <span>{challenge.participants} participants</span>
            </div>
            <div className="flex items-center gap-2">
              <Trophy size={16} />
              <span>${challenge.prizePool.total.toLocaleString()} prize pool</span>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {challenge.categories.map((category, i) => (
              <span
                key={i}
                className="px-2 py-1 bg-secondary text-secondary-foreground rounded-full text-xs"
              >
                {category}
              </span>
            ))}
          </div>
        </div>
      </Link>
    </motion.div>
  );
};

export default ChallengeCard;
