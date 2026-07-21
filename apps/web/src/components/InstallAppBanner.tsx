import React from 'react';
import { motion } from 'framer-motion';
import { AlertTriangle, ExternalLink, RefreshCw, ShieldCheck } from 'lucide-react';
import { useAuthStore } from '../store/useAuthStore';

export const InstallAppBanner: React.FC = () => {
  const { installGitHubApp, checkAuth, user } = useAuthStore();

  return (
    <div className="glass-panel p-6 rounded-2xl border border-amber-500/30 bg-amber-950/10 mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div className="flex items-start gap-4">
        <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 shrink-0">
          <AlertTriangle className="w-6 h-6" />
        </div>
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <span>Welcome, {user?.name || 'Developer'}! Action Required: Install Rover GitHub App</span>
          </h3>
          <p className="text-xs text-slate-300 mt-1 leading-relaxed max-w-2xl">
            You are signed in via GitHub OAuth. To start scanning repositories and generating AI patches, grant access to your repositories through the Rover GitHub App.
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3 shrink-0">
        <button
          onClick={installGitHubApp}
          className="bg-amber-500 hover:bg-amber-400 text-amber-950 font-bold text-xs px-5 py-2.5 rounded-xl border border-transparent flex items-center gap-2 shadow-md transition-all active:scale-[0.98]"
        >
          <span>Install GitHub App</span>
          <ExternalLink className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={checkAuth}
          className="bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs px-4 py-2.5 rounded-xl border border-slate-700 flex items-center gap-2"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Verify Access</span>
        </button>
      </div>
    </div>
  );
};
