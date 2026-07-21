import React, { useEffect, useState, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Bot, RefreshCw, AlertCircle } from 'lucide-react';
import { LandingCanvas } from '../components/LandingCanvas';
import { useAuthStore } from '../store/useAuthStore';

export const AuthCallback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { checkAuth } = useAuthStore();
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const processedRef = useRef<boolean>(false);

  useEffect(() => {
    const processCallback = async () => {
      if (processedRef.current) return;
      processedRef.current = true;

      const code = searchParams.get('code');
      const installationId = searchParams.get('installation_id');
      const setupAction = searchParams.get('setup_action');

      // Case 1: GitHub App Setup Callback
      if (installationId || setupAction === 'install') {
        try {
          const res = await fetch('/api/v1/auth/github/setup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ installation_id: installationId })
          });
          if (res.ok) {
            await checkAuth();
            navigate('/onboarding?step=sync', { replace: true });
            return;
          }
        } catch (err) {
          console.error('Setup callback error:', err);
        }
      }

      // Case 2: GitHub OAuth Code Callback
      if (code) {
        try {
          const res = await fetch('/api/v1/auth/github/callback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code })
          });
          const data = await res.json();
          if (res.ok && data.authenticated) {
            if (data.token) {
              localStorage.setItem('rover_jwt_token', data.token);
            }
            await checkAuth();
            if (data.status === 'no_app_installed') {
              navigate('/onboarding', { replace: true });
            } else {
              navigate('/', { replace: true });
            }
            return;
          } else {
            setErrorMsg(data.detail || data.message || 'GitHub Authentication failed.');
            return;
          }
        } catch (err: any) {
          setErrorMsg('Failed to exchange authorization code with backend.');
          return;
        }
      }


      // Default fallback: re-verify auth state
      await checkAuth();
      navigate('/onboarding', { replace: true });
    };

    processCallback();
  }, [searchParams, navigate, checkAuth]);

  if (errorMsg) {
    return (
      <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center p-6 relative overflow-hidden select-none">
        <div className="fixed inset-0 pointer-events-none opacity-40">
          <LandingCanvas />
        </div>
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="relative z-10 glass-panel p-8 rounded-3xl border border-rose-500/30 bg-rose-950/20 max-w-md w-full text-center space-y-4 shadow-2xl"
        >
          <div className="w-12 h-12 rounded-2xl bg-rose-500/20 text-rose-400 mx-auto flex items-center justify-center">
            <AlertCircle className="w-6 h-6" />
          </div>
          <h2 className="text-xl font-bold text-white">Authentication Failed</h2>
          <p className="text-xs text-slate-300 leading-relaxed">{errorMsg}</p>
          <button
            onClick={() => navigate('/')}
            className="w-full bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs py-3 rounded-xl border border-slate-700 transition-all"
          >
            Return to Home
          </button>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center relative overflow-hidden select-none">
      <div className="fixed inset-0 pointer-events-none opacity-40">
        <LandingCanvas />
      </div>
      <div className="relative z-10 flex flex-col items-center gap-4">
        <div className="w-14 h-14 rounded-2xl bg-slate-800/80 flex items-center justify-center shadow-2xl shadow-black/30 ring-1 ring-white/10 animate-pulse">
          <Bot className="w-7 h-7 text-white" />
        </div>
        <div className="flex items-center gap-2 text-xs font-bold text-slate-400">
          <RefreshCw className="w-4 h-4 animate-spin" />
          <span>Verifying GitHub Authentication & Establishing Secure Session...</span>
        </div>
      </div>
    </div>
  );
};
