import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { GitPullRequest, ExternalLink, CheckCircle2, GitMerge } from 'lucide-react';
import { GlobalLoader } from '../components/GlobalLoader';

export const PullRequests: React.FC = () => {
  const [prs, setPrs] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const token = localStorage.getItem('rover_jwt_token');
    fetch('/api/v1/pull-requests', {
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    })
      .then(res => res.json())
      .then(data => setPrs(data.pull_requests || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);


  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-black text-foreground tracking-tight flex items-center gap-3">
          <GitPullRequest className="w-8 h-8 text-primary" />
          <span>Autonomous Pull Requests</span>
        </h1>
        <p className="text-xs text-muted-foreground mt-1">Review, test, and merge auto-remediated pull requests opened by Rover AI agents.</p>
      </div>

      {loading ? (
        <GlobalLoader text="Loading pull requests..." />
      ) : prs.length === 0 ? (
        <div className="glass-panel p-12 rounded-3xl border border-border bg-card text-center max-w-xl mx-auto my-8 space-y-4">
          <GitPullRequest className="w-10 h-10 text-muted-foreground mx-auto" />
          <h3 className="text-base font-bold text-foreground">No Pull Requests Opened Yet</h3>
          <p className="text-xs text-muted-foreground">Trigger an AI Auto-Fix from Bug Explorer to generate a remediated Pull Request on GitHub.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {prs.map((pr, idx) => (
            <motion.div
              key={pr.id || idx}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.22, delay: idx * 0.06 }}
              className="glass-panel glass-panel-hover p-5 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-4 group relative overflow-hidden"
            >
              <div className="flex items-start gap-4">
                <div className={`w-12 h-12 flex items-center justify-center rounded-xl shrink-0 shadow-lg ${
                  pr.isMerged ? 'bg-purple-500/10 border border-purple-500/20 text-purple-400 shadow-[0_0_15px_rgba(168,85,247,0.15)]' : 'bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.15)]'
                }`}>
                  {pr.isMerged ? <GitMerge className="w-5 h-5" /> : <GitPullRequest className="w-5 h-5" />}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-primary font-bold">#{pr.id}</span>
                    <h3 className="text-sm font-bold text-foreground group-hover:text-primary transition-colors">{pr.title}</h3>
                  </div>
                  <p className="text-xs font-mono text-muted-foreground mt-1">{pr.repo} &bull; branch: <strong className="text-foreground">{pr.branch}</strong></p>
                </div>
              </div>

              <div className="flex items-center gap-4 shrink-0">
                <span className={`px-4 py-1.5 rounded-full text-[11px] font-black uppercase tracking-widest flex items-center gap-1.5 ${
                  pr.isMerged ? 'bg-purple-500/20 text-purple-500 border border-purple-500/30' : 'bg-green-500/10 text-green-500 border border-green-500/20 shadow-sm'
                }`}>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>{pr.status}</span>
                </span>
                <a
                  href={pr.url}
                  target="_blank"
                  rel="noreferrer"
                  className="bg-muted hover:bg-muted/80 text-foreground border border-border font-semibold text-xs px-4 py-2.5 rounded-xl flex items-center gap-1.5 transition-colors shadow-sm"
                >
                  <span>View on GitHub</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
};
