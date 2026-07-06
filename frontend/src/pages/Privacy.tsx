import React from "react";
import { motion } from "framer-motion";
import Layout from "../components/Layout";

const Privacy = () => {
  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-4xl mx-auto"
      >
        <h1 className="text-3xl font-semibold mb-6">Privacy</h1>

        <div className="glass p-6 rounded-xl mb-8">
          <h2 className="text-2xl font-semibold mb-4">What we store</h2>
          <p className="text-muted-foreground mb-4">
            When you use Tom's Gym we store the email address you provide and the videos and
            photos you upload (lifting videos, bowling videos, and golf scorecard photos),
            along with the analysis results we generate from them. That's it — we don't sell
            your data or run third-party ad tracking.
          </p>
          <p className="text-muted-foreground">
            <strong>Uploads are publicly viewable.</strong> Videos, photos, and results you
            submit can appear on public pages such as leaderboards, profiles, and challenge
            listings, and are reachable by anyone with the link. Please don't upload anything
            you want to keep private.
          </p>
        </div>

        <div className="glass p-6 rounded-xl">
          <h2 className="text-2xl font-semibold mb-4">Deleting your data</h2>
          <p className="text-muted-foreground">
            Want your uploads or account removed? Email{" "}
            <a href="mailto:toka778@gmail.com" className="text-accent hover:underline">
              toka778@gmail.com
            </a>{" "}
            and we'll delete your data. Include the email address you uploaded with so we can
            find it.
          </p>
        </div>
      </motion.div>
    </Layout>
  );
};

export default Privacy;
