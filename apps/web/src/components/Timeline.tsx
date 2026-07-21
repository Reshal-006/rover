import React from 'react';
import { motion } from 'framer-motion';
import { FileCheck, ShieldAlert, GitPullRequest, Search, CheckCircle2 } from 'lucide-react';

interface TimelineEvent {
  id: string;
  repo: string;
  title: string;
  description: string;
  date: string;
  type: 'scan' | 'vulnerability' | 'fix' | 'pr';
  status: 'completed' | 'running' | 'failed';
}

interface TimelineProps {
  events: TimelineEvent[];
}

export const Timeline: React.FC<TimelineProps> = ({ events }) => {
  if (!events || events.length === 0) return null;

  return (
    <div className="relative pl-8 md:pl-0 space-y-8">
      {/* Vertical Line */}
      <div className="absolute left-[15px] md:left-1/2 md:-ml-px top-0 bottom-0 w-0.5 bg-gradient-to-b from-indigo-500/50 via-fuchsia-500/50 to-transparent" />

      {events.map((event, idx) => {
        const isLeft = idx % 2 === 0;
        
        let Icon = Search;
        let iconColor = 'text-sky-400';
        let bgGlow = 'bg-sky-500/10 border-sky-500/20';

        if (event.type === 'vulnerability') {
          Icon = ShieldAlert;
          iconColor = 'text-rose-400';
          bgGlow = 'bg-rose-500/10 border-rose-500/20';
        } else if (event.type === 'fix') {
          Icon = FileCheck;
          iconColor = 'text-emerald-400';
          bgGlow = 'bg-emerald-500/10 border-emerald-500/20';
        } else if (event.type === 'pr') {
          Icon = GitPullRequest;
          iconColor = 'text-indigo-400';
          bgGlow = 'bg-indigo-500/10 border-indigo-500/20';
        }

        return (
          <motion.div
            key={event.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: idx * 0.1 }}
            className={`relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group w-full`}
          >
            {/* Timeline Node */}
            <div className="absolute left-[-33px] md:left-1/2 flex items-center justify-center w-10 h-10 rounded-full bg-slate-950 border-2 border-slate-800 transform md:-translate-x-1/2 z-10 shadow-[0_0_15px_rgba(0,0,0,0.5)] group-hover:border-slate-600 transition-colors">
              <div className={`w-8 h-8 rounded-full ${bgGlow} flex items-center justify-center`}>
                 <Icon className={`w-4 h-4 ${iconColor}`} />
              </div>
            </div>

            {/* Content Card */}
            <div className="w-full md:w-5/12 ml-6 md:ml-0">
              <div className="glass-panel p-5 rounded-2xl border border-slate-800/40 bg-slate-900/40 hover:bg-slate-800/60 transition-all hover:-translate-y-1 hover:shadow-xl">
                <div className="flex items-center gap-2 mb-2">
                  <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${bgGlow} ${iconColor}`}>
                    {event.type}
                  </span>
                  <span className="text-xs text-slate-500 font-mono">{event.date}</span>
                </div>
                <h4 className="text-sm font-bold text-slate-100 mb-1 group-hover:text-white transition-colors">{event.title}</h4>
                <p className="text-xs text-slate-400 leading-relaxed line-clamp-2">{event.description}</p>
                <div className="mt-3 pt-3 border-t border-slate-800/50 flex items-center justify-between">
                  <span className="text-[11px] font-medium text-slate-500">{event.repo}</span>
                  {event.status === 'completed' && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />}
                </div>
              </div>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
};
