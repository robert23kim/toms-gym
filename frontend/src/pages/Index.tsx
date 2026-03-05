import React, { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import useEmblaCarousel from "embla-carousel-react";
import Autoplay from "embla-carousel-autoplay";
import ChallengeCard from "../components/ChallengeCard";
import Layout from "../components/Layout";
import TopLifts from "../components/TopLifts";
import { Challenge } from "../lib/types";
import { getFeaturedChallenges } from "../lib/api";

const heroSlides = [
  {
    heading: "Online Lifting Challenges for Everyone",
    subheading: "Compete from anywhere in the world, showcase your strength, and connect with the global lifting community.",
    cta: "Browse Challenges",
    ctaLink: "/challenges",
    image: "https://images.unsplash.com/photo-1599058917765-a780eda07a3e?q=80&w=1469&auto=format&fit=crop"
  },
  {
    heading: "Test Your Strength Against the Best",
    subheading: "Join competitions featuring athletes from around the globe. Submit your lifts and climb the leaderboard.",
    cta: "View Leaderboards",
    ctaLink: "/challenges",
    image: "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?q=80&w=1470&auto=format&fit=crop"
  },
  {
    heading: "Win Prizes & Recognition",
    subheading: "Compete for cash prizes, exclusive merchandise, and bragging rights in our monthly challenges.",
    cta: "See Prize Pools",
    ctaLink: "/challenges",
    image: "https://images.unsplash.com/photo-1526506118085-60ce8714f8c5?q=80&w=1374&auto=format&fit=crop"
  },
  {
    heading: "All Skill Levels Welcome",
    subheading: "From beginners to elite powerlifters, find challenges tailored to your weight class and experience.",
    cta: "Find Your Challenge",
    ctaLink: "/challenges",
    image: "https://images.unsplash.com/photo-1583454110551-21f2fa2afe61?q=80&w=1470&auto=format&fit=crop"
  },
  {
    heading: "Record. Submit. Compete.",
    subheading: "Film your lifts from home or your local gym. Our judges review every submission.",
    cta: "How It Works",
    ctaLink: "#how-it-works",
    image: "https://images.unsplash.com/photo-1605296867304-46d5465a13f1?q=80&w=1470&auto=format&fit=crop"
  }
];

const Index = () => {
  const [activeFilter, setActiveFilter] = useState<"all" | "upcoming" | "ongoing" | "completed">("all");
  const [featuredChallenges, setFeaturedChallenges] = useState<Challenge[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedIndex, setSelectedIndex] = useState(0);

  const [emblaRef, emblaApi] = useEmblaCarousel({ loop: true }, [
    Autoplay({ delay: 5000, stopOnInteraction: false })
  ]);

  const onSelect = useCallback(() => {
    if (!emblaApi) return;
    setSelectedIndex(emblaApi.selectedScrollSnap());
  }, [emblaApi]);

  useEffect(() => {
    if (!emblaApi) return;
    emblaApi.on('select', onSelect);
    onSelect();
    return () => {
      emblaApi.off('select', onSelect);
    };
  }, [emblaApi, onSelect]);

  const scrollTo = useCallback((index: number) => {
    if (emblaApi) emblaApi.scrollTo(index);
  }, [emblaApi]);

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
        <div className="flex-1">
          <section className="mb-20">
            <motion.div
              className="relative overflow-hidden rounded-2xl glass-dark shadow-lg mb-16"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease: "easeOut" }}
            >
              <div className="overflow-hidden" ref={emblaRef}>
                <div className="flex">
                  {heroSlides.map((slide, index) => (
                    <div key={index} className="flex-[0_0_100%] min-w-0 relative">
                      <div className="absolute inset-0 z-0">
                        <img
                          src={slide.image}
                          alt={`Hero background ${index + 1}`}
                          className="w-full h-full object-cover object-center opacity-70"
                        />
                        <div className="absolute inset-0 bg-gradient-to-r from-black/80 to-black/40"></div>
                      </div>

                      <div className="relative z-10 px-6 py-20 md:py-32 max-w-4xl">
                        <AnimatePresence mode="wait">
                          {selectedIndex === index && (
                            <>
                              <motion.h1
                                key={`heading-${index}`}
                                className="text-4xl md:text-5xl font-bold text-white mb-4"
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -20 }}
                                transition={{ duration: 0.5, delay: 0.1, ease: "easeOut" }}
                              >
                                {slide.heading}
                              </motion.h1>

                              <motion.p
                                key={`subheading-${index}`}
                                className="text-xl text-white/90 mb-8 max-w-2xl"
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -20 }}
                                transition={{ duration: 0.5, delay: 0.2, ease: "easeOut" }}
                              >
                                {slide.subheading}
                              </motion.p>

                              <motion.div
                                key={`cta-${index}`}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -20 }}
                                transition={{ duration: 0.5, delay: 0.3, ease: "easeOut" }}
                              >
                                <Link
                                  to={slide.ctaLink}
                                  className="inline-block px-6 py-3 bg-accent text-white font-medium rounded-md shadow-lg hover:bg-accent/90 transition-all hover-lift"
                                >
                                  {slide.cta}
                                </Link>
                              </motion.div>
                            </>
                          )}
                        </AnimatePresence>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Navigation dots */}
              <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 flex gap-2 z-20">
                {heroSlides.map((_, index) => (
                  <button
                    key={index}
                    onClick={() => scrollTo(index)}
                    className={`w-2.5 h-2.5 rounded-full transition-all ${
                      selectedIndex === index
                        ? 'bg-white scale-125'
                        : 'bg-white/50 hover:bg-white/75'
                    }`}
                    aria-label={`Go to slide ${index + 1}`}
                  />
                ))}
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
              {loading ? (
                <div className="py-8 text-center">
                  <div className="flex justify-center">
                    <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-accent"></div>
                  </div>
                  <p className="mt-4 text-muted-foreground">Loading challenges...</p>
                </div>
              ) : featuredChallenges.length > 0 ? (
                <div className="space-y-6">
                  {featuredChallenges.slice(0, 2).map((challenge, index) => (
                    <div key={challenge.id} className="flex items-center justify-center gap-4">
                      <div className="text-4xl">{index === 0 ? "🏋️‍♂️" : "💪"}</div>
                      <div className="text-left">
                        <h3 className="text-xl font-semibold">{challenge.title}</h3>
                        <p className="text-muted-foreground">
                          {new Date(challenge.date).toLocaleDateString('en-US', { 
                            month: 'long', 
                            day: 'numeric', 
                            year: 'numeric' 
                          })} • Prize Pool: ${challenge.prizePool.total.toLocaleString()}
                        </p>
                      </div>
                    </div>
                  ))}
                  <div className="pt-4">
                    <Link
                      to="/challenges"
                      className="inline-block px-8 py-4 bg-accent text-white font-medium rounded-md shadow-lg hover:bg-accent/90 transition-all hover-lift text-lg"
                    >
                      Sign Up for a Challenge
                    </Link>
                  </div>
                </div>
              ) : (
                <div className="py-8 text-center">
                  <p className="text-muted-foreground">No upcoming challenges found.</p>
                  <div className="pt-4">
                    <Link
                      to="/challenges"
                      className="inline-block px-8 py-4 bg-accent text-white font-medium rounded-md shadow-lg hover:bg-accent/90 transition-all hover-lift text-lg"
                    >
                      View All Challenges
                    </Link>
                  </div>
                </div>
              )}
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
