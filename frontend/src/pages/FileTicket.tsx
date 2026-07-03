import React, { useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Bug, Lightbulb, CheckCircle2 } from "lucide-react";
import Layout from "../components/Layout";
import { createTicket, TicketType } from "../lib/api";

const FileTicket: React.FC = () => {
  const [type, setType] = useState<TicketType>("bug");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState<{ ticketId: string } | null>(null);

  const resetForm = () => {
    setType("bug");
    setTitle("");
    setDescription("");
    setEmail("");
    setError(null);
    setSubmitted(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError("Please add a short title.");
      return;
    }
    if (!description.trim()) {
      setError("Please describe the issue or request.");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const userId = localStorage.getItem("userId");
      const pageUrl = document.referrer;
      const { ticket_id } = await createTicket({
        type,
        title: title.trim(),
        description: description.trim(),
        ...(pageUrl ? { page_url: pageUrl } : {}),
        ...(email.trim() ? { email: email.trim() } : {}),
        ...(userId ? { user_id: userId } : {}),
      });
      setSubmitted({ ticketId: ticket_id });
    } catch (err) {
      const axiosErr = err as {
        response?: { data?: { error?: string }; status?: number };
      };
      let msg = "Something went wrong submitting your ticket";
      if (axiosErr.response?.data?.error) {
        msg = `${msg}: ${axiosErr.response.data.error}`;
      } else if (axiosErr.response?.status) {
        msg = `${msg} (status ${axiosErr.response.status})`;
      }
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const typeOptions: { value: TicketType; label: string; icon: React.ReactNode; hint: string }[] = [
    { value: "bug", label: "Report a bug", icon: <Bug className="w-5 h-5" />, hint: "Something is broken or not working right." },
    { value: "feature", label: "Request a feature", icon: <Lightbulb className="w-5 h-5" />, hint: "An idea to make Tom's Gym better." },
  ];

  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8"
      >
        <div className="max-w-2xl mx-auto">
          <Link
            to="/"
            className="inline-flex items-center text-muted-foreground hover:text-foreground mb-8"
          >
            <ArrowLeft className="mr-2" size={16} />
            Back to Home
          </Link>

          <div className="bg-card rounded-lg shadow-lg overflow-hidden">
            <div className="p-6 sm:p-8">
              {submitted ? (
                <div className="text-center py-8">
                  <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-4" />
                  <h1 className="text-2xl font-bold mb-2">Thanks for the feedback!</h1>
                  <p className="text-muted-foreground mb-1">
                    Your ticket has been filed.
                  </p>
                  <p className="text-xs text-muted-foreground mb-6">
                    Reference: <span className="font-mono">{submitted.ticketId}</span>
                  </p>
                  <div className="flex flex-col gap-3">
                    <button
                      onClick={resetForm}
                      className="w-full bg-primary text-primary-foreground py-2 px-4 rounded-lg hover:bg-primary/90"
                    >
                      File another
                    </button>
                    <Link
                      to="/feedback/list"
                      className="w-full bg-secondary text-secondary-foreground py-2 px-4 rounded-lg hover:bg-secondary/90 text-center"
                    >
                      View all tickets
                    </Link>
                  </div>
                </div>
              ) : (
                <>
                  <h1 className="text-2xl font-bold mb-1">Send us feedback</h1>
                  <p className="text-muted-foreground mb-6">
                    Found a bug or have an idea? Let us know — no account needed.
                  </p>

                  <form onSubmit={handleSubmit} className="space-y-6">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {typeOptions.map((opt) => (
                        <button
                          key={opt.value}
                          type="button"
                          onClick={() => setType(opt.value)}
                          className={`flex flex-col items-start gap-1 p-4 rounded-lg border text-left transition-colors ${
                            type === opt.value
                              ? "border-primary bg-primary/5 ring-2 ring-primary"
                              : "border-input hover:bg-secondary/50"
                          }`}
                        >
                          <div className="flex items-center gap-2 font-medium">
                            {opt.icon}
                            {opt.label}
                          </div>
                          <span className="text-xs text-muted-foreground">{opt.hint}</span>
                        </button>
                      ))}
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-2">
                        Title <span className="text-destructive">*</span>
                      </label>
                      <input
                        type="text"
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                        maxLength={200}
                        required
                        placeholder={
                          type === "bug"
                            ? "e.g. Video won't upload on my phone"
                            : "e.g. Add a dark mode toggle"
                        }
                        className="w-full px-3 py-2 bg-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-2">
                        Description <span className="text-destructive">*</span>
                      </label>
                      <textarea
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        maxLength={5000}
                        rows={6}
                        required
                        placeholder="What happened, and what did you expect?"
                        className="w-full px-3 py-2 bg-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-primary resize-y"
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        {description.length}/5000
                      </p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-2">
                        Email <span className="text-muted-foreground font-normal">(optional)</span>
                      </label>
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="So we can follow up with you"
                        className="w-full px-3 py-2 bg-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                    </div>

                    {error && (
                      <div className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg px-3 py-2">
                        {error}
                      </div>
                    )}

                    <button
                      type="submit"
                      disabled={isSubmitting || !title.trim() || !description.trim()}
                      className="w-full bg-primary text-primary-foreground py-2.5 px-4 rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isSubmitting ? "Submitting…" : "Submit ticket"}
                    </button>
                  </form>
                </>
              )}
            </div>
          </div>
        </div>
      </motion.div>
    </Layout>
  );
};

export default FileTicket;
