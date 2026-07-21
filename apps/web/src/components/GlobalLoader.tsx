import React from 'react';
import { motion } from 'framer-motion';
import { Bot, Loader2 } from 'lucide-react';

interface GlobalLoaderProps {
  text?: string;
}

export const GlobalLoader: React.FC<GlobalLoaderProps> = ({ text = "Loading..." }) => {
  return (
    <div className="w-full h-[60vh] flex flex-col items-center justify-center gap-6">
      <div className="relative">
        <motion.div 
          animate={{ rotate: 360 }}
          transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
          className="absolute inset-0 rounded-full border-t-2 border-r-2 border-cyan-500/30 -m-3"
        />
        <motion.div 
          animate={{ rotate: -360 }}
          transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
          className="absolute inset-0 rounded-full border-b-2 border-l-2 border-purple-500/30 -m-1"
        />
        
        <div className="w-16 h-16 rounded-2xl bg-slate-900/80 border border-slate-700/50 flex items-center justify-center shadow-[0_0_30px_rgba(6,182,212,0.15)] relative overflow-hidden backdrop-blur-sm z-10">
          <motion.div
            animate={{ scale: [0.95, 1.05, 0.95], opacity: [0.7, 1, 0.7] }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          >
            <Bot className="w-8 h-8 text-cyan-400" />
          </motion.div>
        </div>
      </div>
      
      <div className="flex flex-col items-center gap-2">
        <div className="flex items-center gap-2 text-slate-300 font-semibold tracking-wide text-sm">
          <Loader2 className="w-4 h-4 animate-spin text-cyan-500" />
          {text}
        </div>
        <div className="text-[10px] text-slate-500 font-mono tracking-widest uppercase">
          Fetching from secure enclave
        </div>
      </div>
    </div>
  );
};
