import React from "react";
import { motion } from "framer-motion";
import Layout from "../components/Layout";

const Terms = () => {
  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-4xl mx-auto"
      >
        <h1 className="text-3xl font-semibold mb-6">Terms of Use</h1>

        <div className="glass p-6 rounded-xl mb-8">
          <p className="text-muted-foreground mb-4">
            Tom's Gym is a hobby project for analyzing your lifting, bowling, and golf. By
            uploading a video or photo you confirm it's yours to share and that you're okay
            with it being processed by our automated analysis. The service is provided as-is,
            with no guarantees of accuracy, uptime, or that your data will be retained forever.
          </p>
          <p className="text-muted-foreground mb-4">
            Please keep it friendly: don't upload content that isn't yours, that's illegal, or
            that you wouldn't want other people to see. Anything you upload may be shown publicly
            on the site — see our <a href="/privacy" className="text-accent hover:underline">Privacy</a> page for details.
            We may remove content or accounts at our discretion.
          </p>
          <p className="text-muted-foreground">
            Questions or requests? Email{" "}
            <a href="mailto:toka778@gmail.com" className="text-accent hover:underline">
              toka778@gmail.com
            </a>.
          </p>
        </div>
      </motion.div>
    </Layout>
  );
};

export default Terms;
