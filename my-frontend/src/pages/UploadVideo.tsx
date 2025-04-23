import React, { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Upload, Dumbbell } from "lucide-react";
import axios from "axios";
import Layout from "../components/Layout";
import { API_URL } from "../config";
import { useToast } from "../components/ui/use-toast";

interface UserProfile {
  best_lifts: {
    type: string;
    best_weight: number;
    competition_name: string;
    competition_id: number;
  }[];
}

const UploadVideo: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [liftType, setLiftType] = useState<string>("Squat");
  const [weight, setWeight] = useState<string>("");
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);

  // Default weights for each lift type
  const defaultWeights = {
    "Squat": "60",
    "Bench": "40",
    "Deadlift": "80"
  };

  const getWeightForLiftType = (type: string) => {
    if (userProfile?.best_lifts) {
      const bestLift = userProfile.best_lifts.find(lift => lift.type === type);
      if (bestLift) {
        return bestLift.best_weight.toString();
      }
    }
    return defaultWeights[type as keyof typeof defaultWeights] || "0";
  };

  useEffect(() => {
    const fetchUserProfile = async () => {
      try {
        const userId = localStorage.getItem('userId');
        if (!userId) {
          // Set default weight if no user profile
          setWeight(getWeightForLiftType(liftType));
          return;
        }

        const response = await axios.get(`${API_URL}/users/${userId}`);
        setUserProfile(response.data);

        // Set initial weight based on best lift or default
        const bestLift = response.data.best_lifts?.find(
          (lift: any) => lift.type === liftType
        );
        setWeight(bestLift ? bestLift.best_weight.toString() : getWeightForLiftType(liftType));
      } catch (err) {
        console.error("Error fetching user profile:", err);
        // Set default weight if error fetching profile
        setWeight(getWeightForLiftType(liftType));
      }
    };

    fetchUserProfile();
  }, []);

  // Update weight when lift type changes
  useEffect(() => {
    setWeight(getWeightForLiftType(liftType));
  }, [liftType, userProfile]);

  const handleLiftTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newLiftType = e.target.value;
    setLiftType(newLiftType);
    setWeight(getWeightForLiftType(newLiftType));
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || !weight || !liftType) {
      setError("Please fill in all fields");
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('video', selectedFile);
      formData.append('lift_type', liftType);
      
      // Ensure weight is a valid number and convert to string
      const weightValue = parseFloat(weight);
      if (isNaN(weightValue)) {
        setError("Please enter a valid weight");
        return;
      }
      formData.append('weight', weightValue.toString());
      
      // Ensure user_id is a string
      const userId = localStorage.getItem('userId');
      if (!userId) {
        setError("User ID not found. Please log in again.");
        return;
      }
      formData.append('user_id', userId);
      
      // For direct uploads, use a default competition_id
      // For challenge uploads, use the provided id
      const competitionId = id || '1'; // Using '1' as default for direct uploads
      formData.append('competition_id', competitionId);

      console.log("Sending form data:", {
        lift_type: liftType,
        weight: weightValue.toString(),
        user_id: userId,
        competition_id: competitionId
      });

      const response = await axios.post(`${API_URL}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      console.log("Upload response:", response.data);

      if (response.data.url) {
        // Store attempt_id in localStorage if needed for later reference
        if (response.data.attempt_id) {
          console.log("Attempt created with ID:", response.data.attempt_id);
          // Optionally store the last uploaded attempt ID
          localStorage.setItem('last_attempt_id', response.data.attempt_id);
          
          toast({
            title: "Upload Successful!",
            description: "Your lift has been submitted and linked to your profile. You can view it in your profile page.",
            duration: 5000,
          });
        } else {
          console.warn("No attempt_id received in the response");
          toast({
            title: "Upload Successful",
            description: "Video was uploaded but may not be fully linked to your profile. Please contact support if you don't see it in your profile.",
            duration: 5000,
          });
        }
        
        // Navigate back to appropriate page
        if (id) {
          navigate(`/challenges/${id}`);
        } else {
          navigate('/random-video');
        }
      } else {
        console.error("No URL in the response:", response.data);
        setError("Upload completed but no video URL was returned");
      }
    } catch (err: any) {
      console.error("Upload error:", err);
      
      if (err.response) {
        console.error("Response error data:", err.response.data);
        console.error("Response status:", err.response.status);
        console.error("Response headers:", err.response.headers);
        
        // More descriptive error message
        let errorMsg = "Upload failed";
        if (err.response.data && err.response.data.error) {
          errorMsg = `${errorMsg}: ${err.response.data.error}`;
        } else if (err.response.status) {
          errorMsg = `${errorMsg} with status ${err.response.status}`;
        }
        setError(errorMsg);
      } else if (err.request) {
        console.error("Request error - no response received:", err.request);
        setError("No response received from server. Please check your connection.");
      } else {
        console.error("Error setting up request:", err.message);
        setError(`Error: ${err.message}`);
      }
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8"
      >
        <div className="max-w-2xl mx-auto">
          {id ? (
            <Link
              to={`/challenges/${id}`}
              className="inline-flex items-center text-muted-foreground hover:text-foreground mb-8"
            >
              <ArrowLeft className="mr-2" size={16} />
              Back to Challenge
            </Link>
          ) : (
            <Link
              to="/random-video"
              className="inline-flex items-center text-muted-foreground hover:text-foreground mb-8"
            >
              <ArrowLeft className="mr-2" size={16} />
              Back to Videos
            </Link>
          )}

          <div className="bg-card rounded-lg shadow-lg overflow-hidden">
            <div className="p-6 sm:p-8">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-blue-500/10 rounded-lg">
                  <Upload className="w-6 h-6 text-blue-500" />
                </div>
                <h1 className="text-2xl font-bold">Upload Your Lift</h1>
              </div>

              <form onSubmit={handleSubmit} className="space-y-6">
                <div>
                  <label className="block text-sm font-medium mb-2">Lift Type</label>
                  <select
                    value={liftType}
                    onChange={handleLiftTypeChange}
                    className="w-full px-3 py-2 bg-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="Squat">Squat</option>
                    <option value="Bench">Bench Press</option>
                    <option value="Deadlift">Deadlift</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Weight (kg)</label>
                  <input
                    type="number"
                    value={weight}
                    onChange={(e) => setWeight(e.target.value)}
                    placeholder="Enter weight in kg"
                    className="w-full px-3 py-2 bg-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Video</label>
                  <div className="border-2 border-dashed border-input rounded-lg p-8 text-center">
                    <input
                      type="file"
                      accept="video/*"
                      onChange={handleFileSelect}
                      className="hidden"
                      id="video-upload"
                    />
                    <label
                      htmlFor="video-upload"
                      className="cursor-pointer flex flex-col items-center"
                    >
                      <Dumbbell className="w-8 h-8 text-muted-foreground mb-2" />
                      <span className="text-muted-foreground">
                        {selectedFile ? selectedFile.name : "Click to select a video file"}
                      </span>
                    </label>
                  </div>
                </div>

                {error && (
                  <div className="text-red-500 text-sm">{error}</div>
                )}

                <button
                  type="submit"
                  disabled={isUploading || !selectedFile}
                  className="w-full bg-primary text-primary-foreground py-2 px-4 rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isUploading ? "Uploading..." : "Upload Video"}
                </button>
              </form>
            </div>
          </div>
        </div>
      </motion.div>
    </Layout>
  );
};

export default UploadVideo; 