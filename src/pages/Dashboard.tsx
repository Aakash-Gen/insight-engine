import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Sparkles,
  Plus,
  Clock,
  BookMarked,
  Settings,
  LogOut,
  ChevronLeft,
  Search,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuthStore } from '@/store/useAuthStore';
import { useResearchStore, type ResearchDepth } from '@/store/useResearchStore';
import { ResearchDepthSelector } from '@/components/ResearchDepthSelector';
import { ConfidenceGauge } from '@/components/ConfidenceGauge';

const Dashboard = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const { savedReports, startResearch } = useResearchStore();
  const [query, setQuery] = useState('');
  const [depth, setDepth] = useState<ResearchDepth>('standard');
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleStartResearch = () => {
    if (!query.trim()) return;
    startResearch(query, depth);
    navigate(`/research/${Date.now()}`);
  };

  const getGreeting = () => {
    const h = new Date().getHours();
    if (h < 12) return 'Good morning';
    if (h < 17) return 'Good afternoon';
    return 'Good evening';
  };

  return (
    <div className="min-h-screen bg-background flex grain-overlay">
      {/* Sidebar */}
      <motion.aside
        initial={false}
        animate={{ width: sidebarOpen ? 260 : 64 }}
        className="border-r border-border bg-sidebar flex flex-col shrink-0 overflow-hidden"
      >
        <div className="p-4 flex items-center gap-2 border-b border-border h-16">
          <Sparkles className="w-5 h-5 text-primary shrink-0" />
          {sidebarOpen && (
            <span className="font-display text-sm font-bold text-foreground whitespace-nowrap">
              ResearchMind
            </span>
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="ml-auto text-muted-foreground hover:text-foreground transition-colors"
          >
            <ChevronLeft className={`w-4 h-4 transition-transform ${!sidebarOpen ? 'rotate-180' : ''}`} />
          </button>
        </div>

        <nav className="flex-1 p-3 space-y-1">
          {[
            { icon: Plus, label: 'New Research', active: true },
            { icon: Clock, label: 'History' },
            { icon: BookMarked, label: 'Saved Reports' },
            { icon: Settings, label: 'Settings' },
          ].map((item) => (
            <button
              key={item.label}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
                item.active
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:text-foreground hover:bg-surface-hover'
              }`}
            >
              <item.icon className="w-4 h-4 shrink-0" />
              {sidebarOpen && <span className="whitespace-nowrap">{item.label}</span>}
            </button>
          ))}
        </nav>

        <div className="p-3 border-t border-border">
          <div className="flex items-center gap-3 px-3 py-2">
            <div className="w-7 h-7 rounded-full bg-primary/20 flex items-center justify-center text-xs font-medium text-primary shrink-0">
              {user?.name?.charAt(0) || 'A'}
            </div>
            {sidebarOpen && (
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-foreground truncate">{user?.name || 'Alex Chen'}</div>
                <div className="text-xs text-muted-foreground truncate">{user?.email || 'alex@example.com'}</div>
              </div>
            )}
            {sidebarOpen && (
              <button
                onClick={() => { logout(); navigate('/'); }}
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                <LogOut className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </motion.aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto scrollbar-thin">
        <div className="max-w-4xl mx-auto px-6 py-12">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <h1 className="font-display text-3xl font-bold text-foreground mb-2">
              {getGreeting()}, {user?.name?.split(' ')[0] || 'Alex'}.
            </h1>
            <p className="text-muted-foreground mb-10">What shall we research today?</p>

            {/* Research input */}
            <div className="glass-card rounded-xl p-6 mb-12">
              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Enter your research question or topic..."
                className="w-full bg-transparent border-none outline-none text-foreground placeholder:text-muted-foreground/50 resize-none text-lg leading-relaxed mb-4"
                rows={3}
              />
              <div className="mb-4">
                <div className="text-xs font-medium text-muted-foreground mb-3 uppercase tracking-wide">
                  Research Depth
                </div>
                <ResearchDepthSelector value={depth} onChange={setDepth} />
              </div>
              <Button
                onClick={handleStartResearch}
                disabled={!query.trim()}
                className="w-full bg-gradient-to-r from-primary to-primary/80 hover:from-primary/90 hover:to-primary/70 text-primary-foreground h-12 text-base glow-primary"
              >
                <Search className="w-4 h-4 mr-2" />
                Start Research
              </Button>
            </div>

            {/* Recent reports */}
            <div className="mb-6">
              <h2 className="font-display text-lg font-semibold text-foreground mb-4">Recent Reports</h2>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {savedReports.map((report, i) => (
                  <motion.div
                    key={report.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.08 }}
                    className="glass-card rounded-lg p-4 hover:border-primary/20 transition-all cursor-pointer group"
                    onClick={() => navigate(`/research/${report.id}`)}
                  >
                    <h3 className="text-sm font-medium text-foreground mb-2 line-clamp-2 group-hover:text-primary transition-colors">
                      {report.title}
                    </h3>
                    <div className="flex items-center gap-2 mb-3">
                      <span className="text-xs text-muted-foreground">
                        {report.date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                      </span>
                      <Badge variant="outline" className="text-xs border-border text-muted-foreground">
                        {report.depth}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2 flex-wrap mb-3">
                      {report.tags.slice(0, 2).map((tag) => (
                        <span key={tag} className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary">
                          {tag}
                        </span>
                      ))}
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        <div
                          className={`w-2 h-2 rounded-full ${
                            report.confidenceScore >= 70
                              ? 'bg-green-500'
                              : report.confidenceScore >= 40
                              ? 'bg-yellow-500'
                              : 'bg-red-500'
                          }`}
                        />
                        <span className="text-xs text-muted-foreground">{report.confidenceScore}%</span>
                      </div>
                      <span className="text-xs text-primary opacity-0 group-hover:opacity-100 transition-opacity">
                        View →
                      </span>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </motion.div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
