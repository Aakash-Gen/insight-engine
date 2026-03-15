import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sparkles,
  Plus,
  Clock,
  BookMarked,
  Settings,
  LogOut,
  ChevronLeft,
  Search,
  LayoutTemplate,
  Trash2,
  ExternalLink,
  User,
  Activity,
  AlertCircle,
} from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuthStore } from '@/store/useAuthStore';
import { useResearchStore, type ResearchDepth } from '@/store/useResearchStore';
import { ResearchDepthSelector } from '@/components/ResearchDepthSelector';
import { listTemplates, healthCheck, type ResearchTemplate } from '@/lib/api';

type ActiveView = 'new' | 'history' | 'reports' | 'settings';

const Dashboard = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const { savedReports, startResearchWithAPI, loadUserReports, removeReport, isLoading, error } = useResearchStore();
  const [query, setQuery] = useState('');
  const [depth, setDepth] = useState<ResearchDepth>('standard');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [templates, setTemplates] = useState<ResearchTemplate[]>([]);
  const [activeView, setActiveView] = useState<ActiveView>('new');
  const [health, setHealth] = useState<{ status: string; model: string } | null>(null);

  // Load reports and templates on mount
  useEffect(() => {
    if (user?.id) {
      loadUserReports(user.id).catch(() => {
        // silently handled in store; errors show via the error state
      });
    }
    listTemplates().then(setTemplates).catch(() => {});
    healthCheck().then(setHealth).catch(() => {});
  }, [user?.id, loadUserReports]);

  // Show store errors as toasts
  useEffect(() => {
    if (error) {
      toast.error(error);
    }
  }, [error]);

  const handleStartResearch = async () => {
    if (!query.trim() || isLoading) return;
    try {
      const researchId = await startResearchWithAPI(query.trim(), depth, user?.id ?? '');
      navigate(`/research/${researchId}`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to start research';
      toast.error(`Could not start research: ${msg}`);
    }
  };

  const handleDelete = async (researchId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await removeReport(researchId);
      toast.success('Report deleted.');
    } catch {
      toast.error('Failed to delete report.');
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  const getGreeting = () => {
    const h = new Date().getHours();
    if (h < 12) return 'Good morning';
    if (h < 17) return 'Good afternoon';
    return 'Good evening';
  };

  const navItems: { icon: React.ElementType; label: string; view: ActiveView }[] = [
    { icon: Plus, label: 'New Research', view: 'new' },
    { icon: Clock, label: 'History', view: 'history' },
    { icon: BookMarked, label: 'Saved Reports', view: 'reports' },
    { icon: Settings, label: 'Settings', view: 'settings' },
  ];

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
          {navItems.map((item) => (
            <button
              key={item.view}
              onClick={() => setActiveView(item.view)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
                activeView === item.view
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
              {user?.name?.charAt(0).toUpperCase() || 'U'}
            </div>
            {sidebarOpen && (
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-foreground truncate">{user?.name}</div>
                <div className="text-xs text-muted-foreground truncate">{user?.email}</div>
              </div>
            )}
            {sidebarOpen && (
              <button
                onClick={handleLogout}
                className="text-muted-foreground hover:text-foreground transition-colors"
                title="Sign out"
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
          <AnimatePresence mode="wait">

            {/* ── New Research ── */}
            {activeView === 'new' && (
              <motion.div
                key="new"
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.3 }}
              >
                <h1 className="font-display text-3xl font-bold text-foreground mb-2">
                  {getGreeting()}, {user?.name?.split(' ')[0]}.
                </h1>
                <p className="text-muted-foreground mb-10">What shall we research today?</p>

                {/* Research input */}
                <div className="glass-card rounded-xl p-6 mb-10">
                  <textarea
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleStartResearch();
                    }}
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
                    disabled={!query.trim() || isLoading}
                    className="w-full bg-gradient-to-r from-primary to-primary/80 hover:from-primary/90 hover:to-primary/70 text-primary-foreground h-12 text-base glow-primary"
                  >
                    {isLoading ? (
                      <>
                        <span className="w-4 h-4 mr-2 rounded-full border-2 border-primary-foreground/30 border-t-primary-foreground animate-spin" />
                        Starting...
                      </>
                    ) : (
                      <>
                        <Search className="w-4 h-4 mr-2" />
                        Start Research
                      </>
                    )}
                  </Button>
                  <p className="text-xs text-muted-foreground/50 text-center mt-2">
                    Tip: Press ⌘ Enter to start
                  </p>
                </div>

                {/* Templates */}
                {templates.length > 0 && (
                  <div className="mb-10">
                    <div className="flex items-center gap-2 mb-4">
                      <LayoutTemplate className="w-4 h-4 text-muted-foreground" />
                      <h2 className="font-display text-lg font-semibold text-foreground">Start from a Template</h2>
                    </div>
                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
                      {templates.map((t, i) => (
                        <motion.button
                          key={t.id}
                          initial={{ opacity: 0, y: 12 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: i * 0.05 }}
                          onClick={() => {
                            setQuery(t.example_topic);
                            setDepth(t.depth);
                            window.scrollTo({ top: 0, behavior: 'smooth' });
                          }}
                          className="text-left glass-card rounded-lg p-4 hover:border-primary/30 transition-all group"
                        >
                          <div className="text-sm font-medium text-foreground mb-1 group-hover:text-primary transition-colors">
                            {t.title}
                          </div>
                          <div className="text-xs text-muted-foreground mb-3 line-clamp-2">{t.description}</div>
                          <div className="flex items-center gap-2 flex-wrap">
                            {t.tags.map((tag) => (
                              <span key={tag} className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary">
                                {tag}
                              </span>
                            ))}
                            <Badge variant="outline" className="text-xs border-border text-muted-foreground ml-auto">
                              {t.depth}
                            </Badge>
                          </div>
                        </motion.button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Recent reports preview */}
                {savedReports.length > 0 && (
                  <div>
                    <div className="flex items-center justify-between mb-4">
                      <h2 className="font-display text-lg font-semibold text-foreground">Recent Reports</h2>
                      <button
                        onClick={() => setActiveView('reports')}
                        className="text-xs text-primary hover:text-primary/80 transition-colors"
                      >
                        View all →
                      </button>
                    </div>
                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {savedReports.slice(0, 6).map((report, i) => (
                        <motion.div
                          key={report.id}
                          initial={{ opacity: 0, y: 16 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: i * 0.06 }}
                          className="glass-card rounded-lg p-4 hover:border-primary/20 transition-all cursor-pointer group"
                          onClick={() => navigate(`/research/${report.id}`)}
                        >
                          <h3 className="text-sm font-medium text-foreground mb-2 line-clamp-2 group-hover:text-primary transition-colors">
                            {report.title}
                          </h3>
                          <div className="flex items-center gap-2 mb-2">
                            <span className="text-xs text-muted-foreground">
                              {report.date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                            </span>
                            <Badge variant="outline" className="text-xs border-border text-muted-foreground">
                              {report.depth}
                            </Badge>
                          </div>
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-1.5">
                              <div className={`w-2 h-2 rounded-full ${
                                report.confidenceScore >= 70 ? 'bg-green-500'
                                : report.confidenceScore >= 40 ? 'bg-yellow-500'
                                : 'bg-red-500'
                              }`} />
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
                )}
              </motion.div>
            )}

            {/* ── History ── */}
            {activeView === 'history' && (
              <motion.div
                key="history"
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.3 }}
              >
                <h1 className="font-display text-2xl font-bold text-foreground mb-2">History</h1>
                <p className="text-muted-foreground mb-8">All your completed research sessions.</p>

                {savedReports.length === 0 ? (
                  <div className="glass-card rounded-xl p-12 text-center">
                    <Clock className="w-10 h-10 text-muted-foreground/30 mx-auto mb-4" />
                    <p className="text-muted-foreground">No research history yet.</p>
                    <Button
                      variant="outline"
                      className="mt-4 border-border"
                      onClick={() => setActiveView('new')}
                    >
                      Start your first research
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {savedReports.map((report, i) => (
                      <motion.div
                        key={report.id}
                        initial={{ opacity: 0, x: -12 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.04 }}
                        className="glass-card rounded-lg p-4 flex items-center gap-4 hover:border-primary/20 transition-all cursor-pointer group"
                        onClick={() => navigate(`/research/${report.id}`)}
                      >
                        <div className="flex-1 min-w-0">
                          <h3 className="text-sm font-medium text-foreground group-hover:text-primary transition-colors truncate">
                            {report.title}
                          </h3>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-xs text-muted-foreground">
                              {report.date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                            </span>
                            <Badge variant="outline" className="text-xs border-border text-muted-foreground">
                              {report.depth}
                            </Badge>
                          </div>
                        </div>
                        <div className="flex items-center gap-3 shrink-0">
                          <div className="flex items-center gap-1.5">
                            <div className={`w-2 h-2 rounded-full ${
                              report.confidenceScore >= 70 ? 'bg-green-500'
                              : report.confidenceScore >= 40 ? 'bg-yellow-500'
                              : 'bg-red-500'
                            }`} />
                            <span className="text-xs text-muted-foreground">{report.confidenceScore}%</span>
                          </div>
                          <ExternalLink className="w-4 h-4 text-muted-foreground/40 group-hover:text-primary transition-colors" />
                        </div>
                      </motion.div>
                    ))}
                  </div>
                )}
              </motion.div>
            )}

            {/* ── Saved Reports ── */}
            {activeView === 'reports' && (
              <motion.div
                key="reports"
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.3 }}
              >
                <h1 className="font-display text-2xl font-bold text-foreground mb-2">Saved Reports</h1>
                <p className="text-muted-foreground mb-8">{savedReports.length} completed report{savedReports.length !== 1 ? 's' : ''}.</p>

                {savedReports.length === 0 ? (
                  <div className="glass-card rounded-xl p-12 text-center">
                    <BookMarked className="w-10 h-10 text-muted-foreground/30 mx-auto mb-4" />
                    <p className="text-muted-foreground">No saved reports yet.</p>
                    <Button
                      variant="outline"
                      className="mt-4 border-border"
                      onClick={() => setActiveView('new')}
                    >
                      Start a research
                    </Button>
                  </div>
                ) : (
                  <div className="grid md:grid-cols-2 gap-4">
                    {savedReports.map((report, i) => (
                      <motion.div
                        key={report.id}
                        initial={{ opacity: 0, y: 12 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.05 }}
                        className="glass-card rounded-lg p-4 hover:border-primary/20 transition-all group"
                      >
                        <h3
                          className="text-sm font-medium text-foreground mb-2 line-clamp-2 cursor-pointer group-hover:text-primary transition-colors"
                          onClick={() => navigate(`/research/${report.id}`)}
                        >
                          {report.title}
                        </h3>
                        <div className="flex items-center gap-2 mb-3">
                          <span className="text-xs text-muted-foreground">
                            {report.date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                          </span>
                          <Badge variant="outline" className="text-xs border-border text-muted-foreground">
                            {report.depth}
                          </Badge>
                        </div>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-1.5">
                            <div className={`w-2 h-2 rounded-full ${
                              report.confidenceScore >= 70 ? 'bg-green-500'
                              : report.confidenceScore >= 40 ? 'bg-yellow-500'
                              : 'bg-red-500'
                            }`} />
                            <span className="text-xs text-muted-foreground">{report.confidenceScore}% confidence</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => navigate(`/research/${report.id}`)}
                              className="text-xs text-primary hover:text-primary/80 transition-colors"
                            >
                              View
                            </button>
                            <button
                              onClick={(e) => handleDelete(report.id, e)}
                              className="text-muted-foreground/40 hover:text-red-400 transition-colors"
                              title="Delete report"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                )}
              </motion.div>
            )}

            {/* ── Settings ── */}
            {activeView === 'settings' && (
              <motion.div
                key="settings"
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.3 }}
              >
                <h1 className="font-display text-2xl font-bold text-foreground mb-2">Settings</h1>
                <p className="text-muted-foreground mb-8">Account and system information.</p>

                <div className="space-y-4">
                  {/* Account */}
                  <div className="glass-card rounded-xl p-6">
                    <div className="flex items-center gap-3 mb-4">
                      <User className="w-4 h-4 text-primary" />
                      <h2 className="font-display text-sm font-semibold text-foreground">Account</h2>
                    </div>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between py-2 border-b border-border/50">
                        <span className="text-xs text-muted-foreground uppercase tracking-wide">Name</span>
                        <span className="text-sm text-foreground">{user?.name}</span>
                      </div>
                      <div className="flex items-center justify-between py-2 border-b border-border/50">
                        <span className="text-xs text-muted-foreground uppercase tracking-wide">Email</span>
                        <span className="text-sm text-foreground">{user?.email}</span>
                      </div>
                      <div className="flex items-center justify-between py-2">
                        <span className="text-xs text-muted-foreground uppercase tracking-wide">User ID</span>
                        <span className="text-xs text-muted-foreground font-mono truncate max-w-[200px]">{user?.id}</span>
                      </div>
                    </div>
                    <Button
                      variant="outline"
                      className="mt-4 border-border text-muted-foreground hover:text-foreground"
                      onClick={handleLogout}
                    >
                      <LogOut className="w-4 h-4 mr-2" />
                      Sign Out
                    </Button>
                  </div>

                  {/* System status */}
                  <div className="glass-card rounded-xl p-6">
                    <div className="flex items-center gap-3 mb-4">
                      <Activity className="w-4 h-4 text-primary" />
                      <h2 className="font-display text-sm font-semibold text-foreground">System Status</h2>
                    </div>
                    {health ? (
                      <div className="space-y-3">
                        <div className="flex items-center justify-between py-2 border-b border-border/50">
                          <span className="text-xs text-muted-foreground uppercase tracking-wide">Backend</span>
                          <span className={`text-sm flex items-center gap-1.5 ${health.status === 'ok' ? 'text-green-400' : 'text-yellow-400'}`}>
                            <span className={`w-2 h-2 rounded-full ${health.status === 'ok' ? 'bg-green-500' : 'bg-yellow-500'}`} />
                            {health.status === 'ok' ? 'Online' : 'Degraded'}
                          </span>
                        </div>
                        <div className="flex items-center justify-between py-2">
                          <span className="text-xs text-muted-foreground uppercase tracking-wide">Active Model</span>
                          <span className="text-sm text-foreground font-mono">{health.model}</span>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <AlertCircle className="w-4 h-4" />
                        Backend unreachable — check that the server is running.
                      </div>
                    )}
                  </div>

                  {/* Stats */}
                  <div className="glass-card rounded-xl p-6">
                    <div className="flex items-center gap-3 mb-4">
                      <BookMarked className="w-4 h-4 text-primary" />
                      <h2 className="font-display text-sm font-semibold text-foreground">Usage</h2>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="text-center py-3 rounded-lg bg-primary/5">
                        <div className="text-2xl font-bold text-foreground">{savedReports.length}</div>
                        <div className="text-xs text-muted-foreground mt-1">Reports</div>
                      </div>
                      <div className="text-center py-3 rounded-lg bg-primary/5">
                        <div className="text-2xl font-bold text-foreground">
                          {savedReports.length > 0
                            ? Math.round(savedReports.reduce((a, r) => a + r.confidenceScore, 0) / savedReports.length)
                            : 0}%
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">Avg. Confidence</div>
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}

          </AnimatePresence>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
