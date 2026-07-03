import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Bug, Lightbulb, Inbox } from "lucide-react";
import Layout from "../components/Layout";
import {
  fetchTickets,
  updateTicketStatus,
  Ticket,
  TicketStatus,
} from "../lib/api";

type StatusFilter = TicketStatus | "all";

const FILTERS: { value: StatusFilter; label: string }[] = [
  { value: "open", label: "Open" },
  { value: "in_progress", label: "In progress" },
  { value: "closed", label: "Closed" },
  { value: "all", label: "All" },
];

const STATUS_OPTIONS: { value: TicketStatus; label: string }[] = [
  { value: "open", label: "Open" },
  { value: "in_progress", label: "In progress" },
  { value: "closed", label: "Closed" },
];

const formatDate = (iso: string): string => {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
};

const TicketList: React.FC = () => {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [filter, setFilter] = useState<StatusFilter>("open");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);
    fetchTickets(filter === "all" ? {} : { status: filter })
      .then((data) => {
        if (!cancelled) setTickets(data);
      })
      .catch(() => {
        if (!cancelled) setError("Failed to load tickets. Please try again.");
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [filter]);

  const toggleExpanded = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleStatusChange = async (id: string, status: TicketStatus) => {
    const previous = tickets;
    // Optimistically update, then drop the row if it no longer matches the filter.
    setTickets((prev) =>
      prev
        .map((t) => (t.id === id ? { ...t, status } : t))
        .filter((t) => filter === "all" || t.status === filter),
    );
    try {
      await updateTicketStatus(id, status);
    } catch {
      setTickets(previous);
      setError("Failed to update ticket status.");
    }
  };

  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8"
      >
        <div className="max-w-3xl mx-auto">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold">Tickets</h1>
              <p className="text-muted-foreground text-sm">
                Bug reports and feature requests.
              </p>
            </div>
            <Link
              to="/feedback"
              className="h-9 px-4 rounded-lg bg-primary text-primary-foreground text-sm inline-flex items-center"
            >
              New ticket
            </Link>
          </div>

          <div className="flex gap-2 mb-6 flex-wrap">
            {FILTERS.map((f) => (
              <button
                key={f.value}
                onClick={() => setFilter(f.value)}
                className={`px-3 py-1.5 rounded-full text-sm transition-colors ${
                  filter === f.value
                    ? "bg-primary text-primary-foreground"
                    : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          {error && (
            <div className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg px-3 py-2 mb-4">
              {error}
            </div>
          )}

          {isLoading ? (
            <div className="flex items-center justify-center h-40">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary" />
            </div>
          ) : tickets.length === 0 ? (
            <div className="bg-card rounded-lg shadow-lg p-12 text-center">
              <Inbox className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
              <h2 className="text-xl font-semibold mb-2">No tickets here</h2>
              <p className="text-muted-foreground mb-6">
                Nothing to show for this filter yet.
              </p>
              <Link
                to="/feedback"
                className="inline-flex items-center bg-primary text-primary-foreground py-2 px-6 rounded-lg hover:bg-primary/90"
              >
                File a ticket
              </Link>
            </div>
          ) : (
            <div className="bg-card rounded-lg shadow-lg overflow-hidden divide-y divide-border">
              {tickets.map((ticket) => {
                const isBug = ticket.type === "bug";
                const isExpanded = expanded.has(ticket.id);
                return (
                  <div key={ticket.id} className="p-4">
                    <div className="flex items-start gap-3">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium shrink-0 ${
                          isBug
                            ? "bg-red-500/10 text-red-500"
                            : "bg-emerald-500/10 text-emerald-500"
                        }`}
                      >
                        {isBug ? (
                          <Bug className="w-3 h-3" />
                        ) : (
                          <Lightbulb className="w-3 h-3" />
                        )}
                        {isBug ? "Bug" : "Feature"}
                      </span>
                      <div className="flex-1 min-w-0">
                        <button
                          onClick={() => toggleExpanded(ticket.id)}
                          className="text-left w-full"
                        >
                          <div className="font-medium truncate">
                            {ticket.title || "(no title)"}
                          </div>
                          <p
                            className={`text-sm text-muted-foreground ${
                              isExpanded ? "whitespace-pre-wrap" : "truncate"
                            }`}
                          >
                            {ticket.description}
                          </p>
                        </button>
                        <div className="text-xs text-muted-foreground mt-1">
                          {formatDate(ticket.created_at)}
                          {ticket.contact_email ? ` · ${ticket.contact_email}` : ""}
                          {isExpanded && ticket.page_url ? ` · ${ticket.page_url}` : ""}
                        </div>
                      </div>
                      <select
                        value={ticket.status}
                        onChange={(e) =>
                          handleStatusChange(
                            ticket.id,
                            e.target.value as TicketStatus,
                          )
                        }
                        className="shrink-0 text-sm bg-background border border-input rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-primary"
                      >
                        {STATUS_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          <div className="mt-8">
            <Link
              to="/"
              className="inline-flex items-center text-muted-foreground hover:text-foreground text-sm"
            >
              <ArrowLeft className="mr-2" size={16} />
              Back to Home
            </Link>
          </div>
        </div>
      </motion.div>
    </Layout>
  );
};

export default TicketList;
