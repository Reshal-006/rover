import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ShieldCheck, 
  GitBranch, 
  CheckCircle2, 
  ExternalLink, 
  RefreshCw, 
  Sparkles, 
  FolderGit2, 
  Bot, 
  Lock,
  ArrowRight
} from 'lucide-react';
import { LandingCanvas } from '../components/LandingCanvas';
import { useAuthStore } from '../store/useAuthStore';

export const OnboardingWizard: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user, status, checkAuth, installGitHubApp } = useAuthStore();

  const isSyncMode = searchParams.get('step') === 'sync';
  const [currentStep, setCurrentStep] = useState<number>(isSyncMode ? 3 : 2);
  const [syncProgress, setSyncProgress] = useState<number>(0);
  const [syncPhase, setSyncPhase] = useState<string>('Verifying Installation Token...');

  // Handle step 3 sync animation sequence
  useEffect(() => {
    if (currentStep === 3) {
      const phases = [
        { progress: 25, label: 'Connecting to GitHub App Installation...' },
        { progress: 55, label: 'Querying Accessible Organizations & Repositories...' },
        { progress: 85, label: 'Initializing Code Graph Caching Engine...' },
        { progress: 100, label: 'Synchronization Complete! Entering Workspace...' }
      ];

      let phaseIdx = 0;
      const interval = setInterval(() => {
        if (phaseIdx < phases.length) {
          setSyncProgress(phases[phaseIdx].progress);
          setSyncPhase(phases[phaseIdx].label);
          phaseIdx++;
        } else {
          clearInterval(interval);
          setTimeout(() => {
            navigate('/', { replace: true });
          }, 600);
        }
      }, 700);

      return () => clearInterval(interval);
    }
  }, [currentStep, navigate]);

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center p-6 relative overflow-hidden select-none">
      {/* 3D Ambient Network Canvas */}
      <div className="fixed inset-0 pointer-events-none opacity-40">
        <LandingCanvas />
      </div>

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative z-10 max-w-2xl w-full space-y-8"
      >
        {/* Header Branding */}
        <div className="text-center space-y-3">
          <div className="w-14 h-14 rounded-2xl bg-slate-800/80 mx-auto flex items-center justify-center shadow-2xl shadow-black/30 ring-1 ring-white/10">
            <Bot className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-3xl font-black text-white tracking-tight">Setup Your Engineering Workspace</h1>
          <p className="text-xs text-slate-300 max-w-md mx-auto">
            Grant Rover access to your repositories to enable autonomous AST scanning and automated fix pull requests.
          </p>
        </div>

        {/* Step Progress Tracker */}
        <div className="flex items-center justify-between px-4">
          <div className="flex items-center gap-3 text-xs font-bold text-emerald-400">
            <div className="w-7 h-7 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            </div>
            <span>1. GitHub Authenticated</span>
          </div>

          <div className="w-12 h-[2px] bg-slate-800"></div>

          <div className={`flex items-center gap-3 text-xs font-bold ${currentStep >= 2 ? 'text-cyan-400' : 'text-slate-500'}`}>
            <div className={`w-7 h-7 rounded-full flex items-center justify-center font-mono ${currentStep >= 2 ? 'bg-cyan-500/20 border border-cyan-500/40 text-cyan-300' : 'bg-slate-800 text-slate-500'}`}>
              2
            </div>
            <span>Install GitHub App</span>
          </div>

          <div className="w-12 h-[2px] bg-slate-800"></div>

          <div className={`flex items-center gap-3 text-xs font-bold ${currentStep >= 3 ? 'text-cyan-400' : 'text-slate-500'}`}>
            <div className={`w-7 h-7 rounded-full flex items-center justify-center font-mono ${currentStep >= 3 ? 'bg-cyan-500/20 border border-cyan-500/40 text-cyan-300' : 'bg-slate-800 text-slate-500'}`}>
              3
            </div>
            <span>Sync Repositories</span>
          </div>
        </div>

        {/* Main Card Content */}
        <div className="glass-panel p-8 rounded-3xl border border-slate-800/40 bg-zinc-900/80 shadow-2xl relative overflow-hidden">
          <AnimatePresence mode="wait">
            {currentStep === 2 && (
              <motion.div
                key="step-2"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="space-y-6"
              >
                <div className="flex items-start gap-4">
                  <div className="p-3 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 shrink-0">
                    <ShieldCheck className="w-8 h-8" />
                  </div>
                  <div>
                    <h2 className="text-lg font-bold text-white">Step 2: Install Rover GitHub App</h2>
                    <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                      Rover operates as a GitHub App to inspect AST structures, trigger security scans, and open automated remediating pull requests on your authorized repositories.
                    </p>
                  </div>
                </div>

                {/* Permissions Highlight Box */}
                <div className="p-4 rounded-2xl bg-slate-950/70 border border-slate-800/80 space-y-2.5">
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-widest block">Permissions Requested</span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                    <div className="flex items-center gap-2 text-slate-200">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                      <span>Read access to code & AST</span>
                    </div>
                    <div className="flex items-center gap-2 text-slate-200">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                      <span>Read/Write access to Pull Requests</span>
                    </div>
                    <div className="flex items-center gap-2 text-slate-200">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                      <span>Read/Write access to Issues</span>
                    </div>
                    <div className="flex items-center gap-2 text-slate-200">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                      <span>Webhook status events</span>
                    </div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
                  <button
                    onClick={() => {
                      installGitHubApp();
                      setCurrentStep(3);
                    }}
                    className="w-full sm:flex-1 bg-zinc-100 hover:bg-white text-zinc-950 font-bold text-xs py-3.5 px-6 rounded-xl border border-transparent flex items-center justify-center gap-2 shadow-md shadow-black/20 transition-all active:scale-[0.98]"
                  >
                    <span>Install Rover GitHub App</span>
                    <ExternalLink className="w-4 h-4" />
                  </button>

                  <button
                    onClick={() => setCurrentStep(3)}
                    className="w-full sm:w-auto bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs py-3.5 px-5 rounded-xl border border-slate-700 flex items-center justify-center gap-2"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    <span>Already Installed? Refresh</span>
                  </button>
                </div>
              </motion.div>
            )}

            {currentStep === 3 && (
              <motion.div
                key="step-3"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-6 text-center py-4"
              >
                <div className="w-12 h-12 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 mx-auto flex items-center justify-center">
                  <RefreshCw className="w-6 h-6 animate-spin" />
                </div>

                <div className="space-y-1">
                  <h2 className="text-lg font-bold text-white">Synchronizing Codebases...</h2>
                  <p className="text-xs font-mono text-cyan-400">{syncPhase}</p>
                </div>

                {/* Animated Progress Bar */}
                <div className="w-full bg-slate-950 rounded-full h-2.5 overflow-hidden border border-slate-800">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${syncProgress}%` }}
                    transition={{ duration: 0.4 }}
                    className="h-full bg-cyan-500 rounded-full"
                  />
                </div>

                <p className="text-[11px] text-slate-500">
                  Setting up multi-tenant isolated database tables and fetching access scopes.
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  );
};
