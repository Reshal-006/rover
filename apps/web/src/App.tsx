import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, useLocation, Navigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { Header } from './components/Header';
import { Dashboard } from './pages/Dashboard';
import { Repositories } from './pages/Repositories';
import { BugExplorer } from './pages/BugExplorer';
import { PullRequests } from './pages/PullRequests';
import { Analytics } from './pages/Analytics';
import { Settings } from './pages/Settings';
import { History } from './pages/History';
import { LandingPage } from './pages/LandingPage';
import { AuthCallback } from './pages/AuthCallback';
import { OnboardingWizard } from './pages/OnboardingWizard';
import { NeuralNetworkCanvas } from './components/NeuralNetworkCanvas';
import { useAuthStore } from './store/useAuthStore';
import { useThemeStore } from './store/useThemeStore';
import { useSettingsStore } from './store/useSettingsStore';
import { Toaster } from 'sonner';
import { Bot, RefreshCw, GitBranch, AlertCircle, Heart } from 'lucide-react';

const LoadingScreen: React.FC = () => (
  <div className="min-h-screen bg-[#030712] flex flex-col items-center justify-center relative overflow-hidden select-none">
    <div className="fixed inset-0 pointer-events-none z-0">
      <NeuralNetworkCanvas />
    </div>
    <div className="relative z-10 flex flex-col items-center gap-4">
      <div className="w-14 h-14 rounded-2xl bg-zinc-900/80 border border-zinc-800/80 flex items-center justify-center shadow-2xl shadow-black/50 animate-pulse">
        <Bot className="w-7 h-7 text-cyan-400" />
      </div>
      <div className="flex items-center gap-2 text-xs font-bold text-slate-400">
        <RefreshCw className="w-4 h-4 animate-spin" />
        <span>Verifying Session & GitHub App Permissions...</span>
      </div>
    </div>
  </div>
);

const ProtectedWorkspace: React.FC = () => {
  const location = useLocation();
  const { status } = useAuthStore();
  const { compact, animations } = useSettingsStore();

  if (status === 'authenticating') {
    return <LoadingScreen />;
  }

  if (status === 'no_app_installed') {
    return <Navigate to="/onboarding" replace />;
  }

  if (status === 'unauthenticated') {
    return <Navigate to="/" replace />;
  }

  return (
    <div className={`flex min-h-screen bg-transparent text-foreground font-sans selection:bg-primary/20 selection:text-primary relative overflow-x-hidden p-3 md:p-6 lg:p-8 ${compact ? 'compact-mode' : ''} ${!animations ? 'disable-animations' : ''}`}>
      {/* Global Background Canvas & Colorful Mesh */}
      <div className="fixed inset-0 pointer-events-none z-0 bg-noise dark:bg-mesh-dark bg-mesh-light transition-colors duration-700">
        <NeuralNetworkCanvas />
        {/* Animated Gradient Orbs */}
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-cyan-500/50 mix-blend-multiply dark:mix-blend-screen filter blur-[100px] animate-blob"></div>
        <div className="absolute top-[20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-purple-500/50 mix-blend-multiply dark:mix-blend-screen filter blur-[120px] animate-blob animation-delay-2000"></div>
        <div className="absolute bottom-[-20%] left-[20%] w-[60%] h-[60%] rounded-full bg-pink-500/50 mix-blend-multiply dark:mix-blend-screen filter blur-[150px] animate-blob animation-delay-4000"></div>
      </div>

      {/* Main Content Area in a Floating Glass Card */}
      <div className="flex-1 flex flex-col min-w-0 relative z-10 bg-transparent rounded-[2rem] shadow-2xl border border-border overflow-hidden">
        <Header />

        <div className="flex-1 relative p-8 md:p-8 max-w-[1600px] w-full mx-auto pb-16 overflow-y-auto">

          {/* Animated Page Content */}
          <div className="relative z-10">
            <AnimatePresence mode="wait">
              <motion.div
                key={location.pathname}
                initial={animations ? { opacity: 0, y: 12, scale: 0.99 } : { opacity: 0 }}
                animate={animations ? { opacity: 1, y: 0, scale: 1 } : { opacity: 1 }}
                exit={animations ? { opacity: 0, y: -12, scale: 0.99 } : { opacity: 0 }}
                transition={{ duration: animations ? 0.22 : 0, ease: [0.16, 1, 0.3, 1] }}
                className="w-full"
              >
                <Routes location={location}>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/repositories" element={<Repositories />} />
                  <Route path="/explorer" element={<BugExplorer />} />
                  <Route path="/pull-requests" element={<PullRequests />} />
                  <Route path="/fixes" element={<BugExplorer />} />
                  <Route path="/analytics" element={<Analytics />} />
                  <Route path="/history" element={<History />} />
                  <Route path="/settings" element={<Settings />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* Bottom Status Bar */}
      <div className="fixed bottom-0 left-0 right-0 h-10 flex items-center justify-center px-6 text-[10px] font-medium text-slate-400 z-50 pointer-events-none">
        <div className="flex items-center gap-1.5 backdrop-blur-md bg-black/20 px-4 py-1.5 rounded-full border border-white/10 shadow-lg pointer-events-auto">
          <span>Made with</span>
          <Heart className="w-3 h-3 text-rose-500 fill-rose-500 animate-bounce" />
          <span className="bg-gradient-to-r from-pink-400 to-rose-400 bg-clip-text text-transparent font-semibold mr-2">with love for developers</span>
          <span className="w-px h-3 bg-white/20"></span>
          <span className="px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 font-mono font-bold tracking-wide">
            Rover v2.4.0
          </span>
        </div>
      </div>

    </div>
  );
};

export const App: React.FC = () => {
  const { status, checkAuth } = useAuthStore();
  useThemeStore(); // initialize theme listener

  useEffect(() => {
    checkAuth();
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        {/* Unconditional Public Callback Route */}
        <Route path="/auth/callback" element={<AuthCallback />} />

        {/* Onboarding Wizard Route */}
        <Route path="/onboarding" element={<OnboardingWizard />} />

        {/* Landing Page for Unauthenticated Root Route */}
        <Route
          path="/"
          element={
            status === 'authenticating' ? (
              <LoadingScreen />
            ) : status === 'unauthenticated' ? (
              <LandingPage />
            ) : (
              <ProtectedWorkspace />
            )
          }
        />

        {/* Protected Workspace catch-all */}
        <Route
          path="/*"
          element={
            status === 'unauthenticated' ? <Navigate to="/" replace /> : <ProtectedWorkspace />
          }
        />
      </Routes>
      <Toaster position="bottom-right" theme="dark" richColors />
    </BrowserRouter>
  );
};

export default App;
