import React from "react";
import { motion } from "framer-motion";
import Layout from "../components/Layout";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";

const About = () => {
  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-4xl mx-auto"
      >
        <h1 className="text-3xl font-semibold mb-6">About Tom's Gym</h1>
        
        <div className="glass p-6 rounded-xl mb-8">
          <h2 className="text-2xl font-semibold mb-4">Our Mission</h2>
          <p className="text-muted-foreground mb-4">
            At Tom's Gym, we're dedicated to making competitive lifting accessible to everyone, 
            everywhere. Our platform enables lifters of all levels to participate in competitions 
            without geographical limitations, connecting the global lifting community through 
            technology.
          </p>
          <p className="text-muted-foreground">
            We believe that competition drives improvement, and that everyone deserves the chance 
            to test their strength against others and against themselves. Through our online 
            competition platform, we're breaking down barriers and creating opportunities for 
            lifters worldwide.
          </p>
        </div>
        
        <div className="glass p-6 rounded-xl mb-8">
          <h2 className="text-2xl font-semibold mb-4">How It Works</h2>
          <div className="space-y-6">
            <div className="flex items-start space-x-4">
              <div className="w-14 h-14 bg-secondary rounded-full flex items-center justify-center text-2xl shrink-0">
                1
              </div>
              <div>
                <h3 className="text-xl font-medium mb-2">Registration</h3>
                <p className="text-muted-foreground">
                  Browse through our available competitions and register for those that match your
                  lifting style, weight class, and schedule. Each competition has specific rules and
                  requirements, so make sure to read them carefully.
                </p>
              </div>
            </div>
            
            <div className="flex items-start space-x-4">
              <div className="w-14 h-14 bg-secondary rounded-full flex items-center justify-center text-2xl shrink-0">
                2
              </div>
              <div>
                <h3 className="text-xl font-medium mb-2">Recording Your Lifts</h3>
                <p className="text-muted-foreground">
                  When the competition period begins, record your lifts according to the competition
                  guidelines. Our platform supports multiple camera angles to ensure proper form
                  verification and makes the submission process seamless.
                </p>
              </div>
            </div>
            
            <div className="flex items-start space-x-4">
              <div className="w-14 h-14 bg-secondary rounded-full flex items-center justify-center text-2xl shrink-0">
                3
              </div>
              <div>
                <h3 className="text-xl font-medium mb-2">Judging and Results</h3>
                <p className="text-muted-foreground">
                  Our certified judges review all submitted lifts to ensure they meet competition
                  standards. Results are updated in real-time, allowing you to track your standing
                  against other competitors throughout the event.
                </p>
              </div>
            </div>
          </div>
        </div>
        
        <div className="glass p-6 rounded-xl">
          <h2 className="text-2xl font-semibold mb-4">Our Team</h2>
          <p className="text-muted-foreground mb-6">
            Tom's Gym was founded by a group of passionate lifters who wanted to make competitive
            lifting more accessible. Our team includes certified coaches, former competitive lifters,
            and technology experts all working together to create the best possible platform for
            the lifting community.
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                name: "Tom Oka",
                role: "Founder & CEO",
                bio: "Experienced software engineer and powerlifting enthusiast with a vision to revolutionize online competitions.",
                avatar: "https://images.unsplash.com/photo-1581092795360-fd1ca04f0952",
                initials: "TO"
              },
              {
                name: "Rob Kim",
                role: "Head of Technology",
                bio: "Technical leader with a passion for building scalable platforms that connect athletes worldwide.",
                avatar: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e",
                initials: "RK"
              },
              {
                name: "Jess Hum",
                role: "Chief Strategy Officer",
                bio: "Former competitive lifter focused on building an inclusive and supportive community of athletes.",
                avatar: "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158",
                initials: "JH"
              }
            ].map((member) => (
              <div key={member.name} className="flex flex-col items-center text-center p-4 glass rounded-lg">
                <Avatar className="w-24 h-24 mb-4">
                  <AvatarImage src={member.avatar} alt={member.name} />
                  <AvatarFallback>{member.initials}</AvatarFallback>
                </Avatar>
                <h3 className="font-medium text-lg">{member.name}</h3>
                <p className="text-sm text-accent mb-2">{member.role}</p>
                <p className="text-sm text-muted-foreground">{member.bio}</p>
              </div>
            ))}
          </div>
        </div>
      </motion.div>
    </Layout>
  );
};

export default About;
