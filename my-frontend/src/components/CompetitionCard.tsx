
import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Competition } from "../lib/types";
import { Calendar, Users } from "lucide-react";

interface CompetitionCardProps {
  competition: Competition;
  index: number;
}

const CompetitionCard: React.FC<CompetitionCardProps> = ({ competition, index }) => {
  const formatDate = (dateString: string) => {
    const options: Intl.DateTimeFormatOptions = { year: "numeric", month: "long", day: "numeric" };
    return new Date(dateString).toLocaleDateString(undefined, options);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: index * 0.1, ease: "easeOut" }}
      className="group"
    >
      <Link to={`/competitions/${competition.id}`} className="block h-full">
        <div className="relative h-full overflow-hidden rounded-lg bg-white border border-border/50 shadow-sm transition-all duration-300 hover:shadow-md hover:border-border/80 hover:-translate-y-1">
          <div className="h-52 overflow-hidden">
            <img
              src={competition.image}
              alt={competition.title}
              className="w-full h-full object-cover transition-transform duration-500 ease-out group-hover:scale-105"
            />
            <div className="absolute top-3 right-3">
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                competition.status === "upcoming"
                  ? "bg-blue-100 text-blue-800"
                  : competition.status === "ongoing"
                  ? "bg-green-100 text-green-800"
                  : "bg-gray-100 text-gray-800"
              }`}>
                {competition.status.charAt(0).toUpperCase() + competition.status.slice(1)}
              </span>
            </div>
          </div>
          
          <div className="p-5">
            <h3 className="text-lg font-medium text-gray-900 mb-2 line-clamp-2">
              {competition.title}
            </h3>
            
            <div className="mb-4 space-y-2">
              <div className="flex items-center text-sm text-gray-500">
                <Calendar size={16} className="mr-2 text-gray-400" />
                {formatDate(competition.date)}
              </div>
              <div className="flex items-center text-sm text-gray-500">
                <Users size={16} className="mr-2 text-gray-400" />
                {competition.participants.length} participants
              </div>
            </div>
            
            <div className="flex flex-wrap gap-1 mt-3">
              {competition.categories.map((category) => (
                <span
                  key={category}
                  className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800"
                >
                  {category}
                </span>
              ))}
            </div>
          </div>
          
          <div className="absolute inset-x-0 bottom-0 h-0.5 bg-gradient-to-r from-cyan-500 via-blue-500 to-purple-500 transform scale-x-0 group-hover:scale-x-100 transition-transform duration-300 ease-out origin-left"></div>
        </div>
      </Link>
    </motion.div>
  );
};

export default CompetitionCard;
