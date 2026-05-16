import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import axios from "axios";
import Layout from "../components/Layout";
import { API_URL } from "../config";

const ShortLinkRedirect: React.FC = () => {
  const { code } = useParams<{ code: string }>();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!code) {
      setError("No short code provided.");
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await axios.get(`${API_URL}/short-link/${code}`);
        if (cancelled) return;
        const target = res.data?.target_url as string | undefined;
        if (!target) {
          setError("Short link is missing a destination.");
          return;
        }
        window.location.replace(target);
      } catch (err) {
        if (cancelled) return;
        const status = axios.isAxiosError(err) ? err.response?.status : null;
        setError(status === 404 ? "This short link does not exist." : "Could not load this short link.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [code]);

  return (
    <Layout>
      <div className="min-h-[50vh] flex items-center justify-center px-4">
        <div className="text-center max-w-md">
          {error ? (
            <>
              <h1 className="text-2xl font-bold mb-2">Link not found</h1>
              <p className="text-muted-foreground mb-6">{error}</p>
              <Link to="/" className="text-blue-500 hover:underline">
                Go home
              </Link>
            </>
          ) : (
            <p className="text-muted-foreground">Redirecting…</p>
          )}
        </div>
      </div>
    </Layout>
  );
};

export default ShortLinkRedirect;
