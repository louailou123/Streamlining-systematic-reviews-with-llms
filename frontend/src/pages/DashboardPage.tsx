import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { researchApi, type ResearchSummary, type CreateResearchRequest } from '../api/research';
import { useAuthStore } from '../stores/authStore';
import {
  Sparkles, Plus, Search, BookOpen, Clock, CheckCircle2,
  XCircle, PauseCircle, Loader2, Send, LogOut, ChevronRight
} from 'lucide-react';

const DashboardPage: React.FC = () => {
  const [histories, setHistories] = useState<ResearchSummary[]>([]);
  const [topic, setTopic] = useState('');
  const [creating, setCreating] = useState(false);
  const [loading, setLoading] = useState(true);
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();

  useEffect(() => {
    const load = async () => {
      try {
        const data = await researchApi.list();
        setHistories(data.items);
      } catch (err) {
        console.error('Failed to load research histories:', err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim() || creating) return;
    setCreating(true);
    try {
      const research = await researchApi.create({ topic: topic.trim() });
      navigate(`/research/${research.id}`);
    } catch (err) {
      console.error('Failed to create research:', err);
      setCreating(false);
    }
  };

  const statusIcon = (status: string) => {
    switch (status) {
      case 'running': return <Loader2 className="w-4 h-4 text-accent-blue animate-spin" />;
      case 'completed': return <CheckCircle2 className="w-4 h-4 text-accent-green" />;
      case 'failed': return <XCircle className="w-4 h-4 text-accent-rose" />;
      case 'paused': return <PauseCircle className="w-4 h-4 text-accent-amber" />;
      default: return <Clock className="w-4 h-4 text-gray-500" />;
    }
  };

  return (
    <div className="min-h-screen">
      {/* Background gradients */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute top-0 left-1/3 w-[600px] h-[600px] bg-accent-blue/5 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-accent-purple/5 rounded-full blur-3xl" />
      </div>

      {/* Top Bar */}
      <header className="sticky top-0 z-50 border-b border-dark-border bg-dark-bg/80 backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <span className="text-lg font-bold gradient-text">LiRA</span>
          </div>

          <div className="flex items-center gap-4">
            {user && (
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center text-xs font-bold text-white">
                  {(user.full_name || user.email)[0].toUpperCase()}
                </div>
                <span className="text-sm text-gray-400 hidden sm:block">
                  {user.full_name || user.email}
                </span>
              </div>
            )}
            <button onClick={logout} className="btn-ghost text-sm flex items-center gap-1.5 text-gray-500">
              <LogOut className="w-4 h-4" />
              <span className="hidden sm:block">Logout</span>
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-12">
        {/* Hero Section */}
        <div className="text-center mb-12 animate-fade-in">
          <h1 className="text-4xl sm:text-5xl font-bold mb-4">
            <span className="gradient-text">Systematic Reviews,</span>
            <br />
            <span className="text-gray-100">Streamlined by AI</span>
          </h1>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto">
            Enter your research topic and LiRA will search, screen, analyze, and draft
            a literature review — powered by LLMs and multi-database search.
          </p>
        </div>

        {/* New Research Input */}
        <div className="max-w-3xl mx-auto mb-16 animate-slide-up">
          <form onSubmit={handleCreate} className="relative">
            <div className="glass-card p-2 flex items-center gap-2 transition-all duration-300 focus-within:border-accent-blue/50 focus-within:shadow-lg focus-within:shadow-accent-blue/10">
              <div className="flex-1">
                <textarea
                  id="research-topic-input"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="Describe your research topic... e.g. 'The impact of artificial intelligence on drug discovery in precision medicine'"
                  className="w-full bg-transparent px-4 py-3 text-gray-100 placeholder-gray-500/60 resize-none focus:outline-none text-sm leading-relaxed"
                  rows={2}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleCreate(e);
                    }
                  }}
                />
              </div>
              <button
                id="start-research-btn"
                type="submit"
                disabled={!topic.trim() || creating}
                className="self-end mb-1 mr-1 p-3 rounded-lg bg-gradient-to-r from-accent-blue to-accent-purple text-white
                           transition-all duration-300 hover:shadow-lg hover:shadow-accent-blue/25
                           disabled:opacity-30 disabled:cursor-not-allowed"
              >
                {creating ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </div>
            <p className="text-xs text-gray-600 mt-2 text-center">
              Press Enter to start • Shift+Enter for new line
            </p>
          </form>
        </div>

        {/* Research History */}
        <div className="animate-slide-up" style={{ animationDelay: '0.1s' }}>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-100 flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-accent-blue" />
              Research History
            </h2>
            <span className="text-sm text-gray-500">{histories.length} projects</span>
          </div>

          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="glass-card p-5">
                  <div className="skeleton h-5 w-3/4 mb-3" />
                  <div className="skeleton h-4 w-1/3" />
                </div>
              ))}
            </div>
          ) : histories.length === 0 ? (
            <div className="glass-card p-12 text-center">
              <Sparkles className="w-12 h-12 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-500 mb-2">No research projects yet</p>
              <p className="text-sm text-gray-600">Enter a topic above to start your first review</p>
            </div>
          ) : (
            <div className="space-y-3">
              {histories.map((h) => (
                <button
                  key={h.id}
                  onClick={() => navigate(`/research/${h.id}`)}
                  className="w-full glass-card-hover p-5 text-left group"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-2">
                        {statusIcon(h.status)}
                        <h3 className="font-medium text-gray-200 truncate group-hover:text-gray-100 transition-colors">
                          {h.title}
                        </h3>
                      </div>
                      <div className="flex items-center gap-4 text-xs text-gray-500">
                        <span>{new Date(h.created_at).toLocaleDateString()}</span>
                        {h.current_step && <span className="font-mono">{h.current_step}</span>}
                        {h.latest_summary && <span className="truncate max-w-xs">{h.latest_summary}</span>}
                      </div>
                    </div>
                    <ChevronRight className="w-5 h-5 text-gray-600 group-hover:text-accent-blue transition-colors" />
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default DashboardPage;
