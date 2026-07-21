import React from 'react';
import { motion } from 'framer-motion';
import { Bot, Shield, Cpu, Sparkles, ArrowRight, Lock, CheckCircle2, Terminal } from 'lucide-react';
import { LandingCanvas } from '../components/LandingCanvas';
import { Playground } from '../components/Playground';
import { useAuthStore } from '../store/useAuthStore';
import { toast } from 'sonner';

export const LandingPage: React.FC = () => {
  const { loginWithGitHub, status, errorMessage } = useAuthStore();

  React.useEffect(() => {
    if (status === 'error' && errorMessage) {
      toast.error(errorMessage);
    }
  }, [status, errorMessage]);


  return (
    <div className="min-h-screen bg-transparent text-foreground font-sans relative overflow-hidden select-none flex flex-col justify-between">
      {/* 3D Neural Canvas Background */}
      <div className="absolute inset-0 pointer-events-none z-0 opacity-100">
        <LandingCanvas />
      </div>

      {/* Top Navbar */}
      <header className="relative z-20 border-b border-border bg-background/50 backdrop-blur-xl px-8 py-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-white/5 flex items-center justify-center shadow-lg ring-1 ring-white/20 backdrop-blur-md">
            <Bot className="w-5 h-5 text-indigo-300" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-lg tracking-tight text-foreground drop-shadow-md">Rover</span>
              <span className="bg-sky-500/10 text-sky-500 dark:text-sky-400 border border-sky-500/20 text-[10px] font-bold px-2 py-0.5 rounded-full shadow-sm">v2.0 Enterprise</span>
            </div>
            <p className="text-[11px] text-muted-foreground font-medium tracking-wide">Autonomous AI Developer Platform</p>
          </div>
        </div>

        <button
          onClick={loginWithGitHub}
          disabled={status === 'authenticating'}
          className="bg-primary hover:opacity-90 text-primary-foreground font-bold text-xs px-5 py-2.5 rounded-xl border border-transparent flex items-center gap-2 shadow-lg transition-all duration-300 hover:scale-105 active:scale-[0.98]"
        >
          <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24">
            <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
          </svg>
          <span>{status === 'authenticating' ? 'Connecting...' : 'Sign in with GitHub'}</span>
        </button>
      </header>

      {/* Main Hero Section */}
      <main className="relative z-10 max-w-5xl mx-auto px-6 py-20 text-center space-y-8 my-auto flex flex-col items-center">
        {/* Animated Warm Glow Orb Behind Text */}
        <motion.div
          animate={{ scale: [1, 1.05, 1], opacity: [0.15, 0.25, 0.15] }}
          transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[500px] bg-gradient-to-tr from-amber-900/20 via-orange-900/10 to-transparent blur-[100px] rounded-full pointer-events-none z-[-1]"
        />

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary/10 border border-primary/20 text-primary text-xs font-semibold shadow-md backdrop-blur-md"
        >
          <Sparkles className="w-4 h-4 text-primary" />
          <span>Next-Generation Autonomous GitHub Engineering Agent</span>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="text-4xl md:text-6xl font-extrabold tracking-tight leading-tight text-foreground"
        >
          Automate Security, AST Scans & <br />
          <span className="bg-gradient-to-r from-blue-600 via-purple-600 to-rose-600 dark:from-cyan-400 dark:via-primary dark:to-purple-500 bg-clip-text text-transparent">
            Autonomous Pull Requests
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.2 }}
          className="text-sm md:text-base text-muted-foreground max-w-2xl mx-auto leading-relaxed"
        >
          Rover continuously scans your private and public GitHub repositories, builds AST symbol graphs, patches zero-day vulnerabilities, and opens verified Pull Requests autonomously.
        </motion.p>

        {/* Primary Call to Action */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.3 }}
          className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          <button
            onClick={loginWithGitHub}
            disabled={status === 'authenticating'}
            className="w-full sm:w-auto bg-foreground hover:opacity-90 text-background font-bold text-sm px-8 py-4 rounded-2xl border border-transparent flex items-center justify-center gap-3 shadow-lg shadow-primary/20 transition-all duration-150 active:scale-[0.98]"
          >
            <svg className="w-5 h-5 fill-current" viewBox="0 0 24 24">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
            </svg>
            <span>Sign in with GitHub OAuth</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </motion.div>

        {/* Interactive Playground Section */}
        <div className="w-full mt-12 z-20 relative">
          <Playground />
        </div>

        {/* Feature Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-12 text-left relative z-20 w-full">
          <div className="relative p-6 rounded-2xl space-y-3 bg-gradient-to-br from-blue-500/10 via-indigo-500/5 to-transparent border border-blue-500/20 hover:border-blue-500/40 hover:shadow-2xl hover:shadow-blue-500/20 hover:-translate-y-2 transition-all duration-300 backdrop-blur-xl group overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-blue-500/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
            <div className="w-10 h-10 rounded-xl bg-blue-500/20 border border-blue-500/30 flex items-center justify-center text-blue-500 dark:text-blue-400 relative z-10 group-hover:scale-110 transition-transform">
              <Shield className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-bold text-foreground relative z-10">Zero-Day Detection</h3>
            <p className="text-xs text-muted-foreground leading-relaxed relative z-10">Scans AST syntax trees to identify unsanitized input vectors, command injections, and exposed secrets.</p>
          </div>

          <div className="relative p-6 rounded-2xl space-y-3 bg-gradient-to-br from-purple-500/10 via-rose-500/5 to-transparent border border-purple-500/20 hover:border-purple-500/40 hover:shadow-2xl hover:shadow-purple-500/20 hover:-translate-y-2 transition-all duration-300 backdrop-blur-xl group overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-purple-500/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
            <div className="w-10 h-10 rounded-xl bg-purple-500/20 border border-purple-500/30 flex items-center justify-center text-purple-500 dark:text-purple-400 relative z-10 group-hover:scale-110 transition-transform">
              <Cpu className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-bold text-foreground relative z-10">Autonomous Agent Fixes</h3>
            <p className="text-xs text-muted-foreground leading-relaxed relative z-10">Generates context-aware remediated code patches and opens fully tested GitHub Pull Requests.</p>
          </div>

          <div className="relative p-6 rounded-2xl space-y-3 bg-gradient-to-br from-emerald-500/10 via-cyan-500/5 to-transparent border border-emerald-500/20 hover:border-emerald-500/40 hover:shadow-2xl hover:shadow-emerald-500/20 hover:-translate-y-2 transition-all duration-300 backdrop-blur-xl group overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
            <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-500 dark:text-emerald-400 relative z-10 group-hover:scale-110 transition-transform">
              <Lock className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-bold text-foreground relative z-10">Enterprise Multi-Tenancy</h3>
            <p className="text-xs text-muted-foreground leading-relaxed relative z-10">Strict data isolation enforced by GitHub App installation tokens and backend authorization rules.</p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-20 border-t border-border bg-background px-8 py-4 text-center text-xs text-muted-foreground">
        Rover Platform v2.0 &bull; Autonomous GitHub AI Developer &bull; All data isolated per tenant session
      </footer>
    </div>
  );
};
