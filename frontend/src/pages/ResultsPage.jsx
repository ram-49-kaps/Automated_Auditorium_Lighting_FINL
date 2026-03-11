
import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getResults, launchSimulation, getDownloadUrl, reprocessScript, getMetrics } from '../utils/api'
import Header from '../components/layout/Header'
import EvaluationMetrics from '../components/charts/EvaluationMetrics'
import { Loader2, AlertTriangle, Sparkles, Film, BrainCircuit, Lightbulb, PlaySquare, Rocket, Play, Download, Plus, Smile, Frown, Ghost, Angry, Meh, Zap, Bug, Upload, Clock, Eye, Heart, Hourglass, Sun, Trophy, AlertOctagon, CloudRain, Flower2, HelpCircle, Star, Swords } from 'lucide-react'

export default function ResultsPage() {
    const navigate = useNavigate()
    const { jobId } = useParams()
    const [results, setResults] = useState(null)
    const [metrics, setMetrics] = useState(null)
    const [metricsLoading, setMetricsLoading] = useState(true)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [launching, setLaunching] = useState(false)
    const [reprocessing, setReprocessing] = useState(false)
    const [aiResolving, setAiResolving] = useState(false)
    const [activeTab, setActiveTab] = useState('overview')

    // Fetch Results
    useEffect(() => {
        async function fetchData() {
            try {
                const data = await getResults(jobId);
                setResults(data);
                setLoading(false);
            } catch (err) {
                console.error("Failed to load results:", err);
                setError("Could not load results. They may not be ready yet.");
                setLoading(false);
            }
        }
        if (jobId) fetchData();
    }, [jobId]);

    // Fetch Metrics (after results load)
    useEffect(() => {
        async function fetchMetrics() {
            try {
                const data = await getMetrics(jobId);
                setMetrics(data);
            } catch (err) {
                console.error("Failed to load metrics:", err);
            } finally {
                setMetricsLoading(false);
            }
        }
        if (jobId && results) fetchMetrics();
    }, [jobId, results]);

    const handleLaunch = async () => {
        setLaunching(true);
        try {
            const resp = await launchSimulation(jobId);
            // Open simulation in new tab
            window.open(resp.url, '_blank');
        } catch (err) {
            console.error("Launch failed", err);
            alert("Failed to launch simulation.");
        } finally {
            setLaunching(false);
        }
    }

    const handleReprocess = async () => {
        setReprocessing(true);
        try {
            await reprocessScript(jobId);
            // Wait for pipeline to complete, then reload results
            // Poll every 2s until results are ready
            const poll = setInterval(async () => {
                try {
                    const data = await getResults(jobId);
                    if (data) {
                        clearInterval(poll);
                        setResults(data);
                        setReprocessing(false);
                        // Re-fetch metrics too
                        setMetricsLoading(true);
                        const metricsData = await getMetrics(jobId);
                        setMetrics(metricsData);
                        setMetricsLoading(false);
                    }
                } catch { /* still processing */ }
            }, 2000);
        } catch (err) {
            console.error("Reprocess failed", err);
            alert("Failed to re-process script.");
            setReprocessing(false);
        }
    }

    const handleReevaluate = async () => {
        setAiResolving(true);
        try {
            // Artificial delay to let the cinematic AI animation show for at least 1.5s
            await new Promise(r => setTimeout(r, 1500));
            const data = await getResults(jobId);
            setResults(data);
            const metricsData = await getMetrics(jobId);
            setMetrics(metricsData);
        } catch (err) {
            console.error("Re-evaluate failed", err);
        } finally {
            setAiResolving(false);
        }
    }

    if (!jobId) {
        return (
            <div className="min-h-screen bg-stage-bg text-white">
                <Header />
                <main className="pt-32 pb-16 px-6 flex flex-col items-center justify-center min-h-[80vh]">
                    <div className="glass-card max-w-lg w-full p-10 text-center animate-fade-in-up border border-[#00d4ff]/20 bg-black/40 backdrop-blur-xl shadow-[0_0_30px_rgba(0,212,255,0.05)]">
                        <div className="w-16 h-16 bg-[#00d4ff]/10 border border-[#00d4ff]/30 rounded flex items-center justify-center mx-auto mb-6 shadow-[0_0_15px_rgba(0,212,255,0.2)]">
                            <Upload className="w-8 h-8 text-[#00d4ff]" />
                        </div>
                        <h2 className="text-2xl font-mono font-bold mb-4 uppercase tracking-widest text-white">NO DATA FOUND</h2>
                        <p className="text-white/40 mb-8 leading-relaxed font-mono text-sm uppercase tracking-wide">
                            Telemetry indicates no active workspace results. Return to upload protocol to initialize synthesis.
                        </p>
                        <button onClick={() => navigate('/upload')} className="group relative px-6 py-3 bg-[#00d4ff]/10 hover:bg-[#00d4ff]/20 border border-[#00d4ff]/50 
                                text-[#00d4ff] font-mono text-xs uppercase tracking-[0.2em] transition-all duration-300
                                shadow-[0_0_15px_rgba(0,212,255,0.1)] hover:shadow-[0_0_25px_rgba(0,212,255,0.2)] flex items-center justify-center gap-3 overflow-hidden mx-auto">
                            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700 ease-in-out" />
                            <span className="relative z-10 font-bold flex items-center gap-2">
                                <Plus className="w-4 h-4 flex-shrink-0" /> RETURN TO UPLOAD
                            </span>
                        </button>
                    </div>
                </main>
            </div>
        )
    }

    if (loading) {
        return (
            <div className="min-h-screen bg-stage-bg flex items-center justify-center text-white">
                <Header />
                <div className="text-center pt-24 text-[#00d4ff] flex flex-col items-center">
                    <Loader2 className="w-12 h-12 mb-6 animate-spin drop-shadow-[0_0_15px_rgba(0,212,255,0.5)]" />
                    <p className="font-mono text-sm tracking-[0.2em] uppercase">RETRIEVING TELEMETRY...</p>
                </div>
            </div>
        )
    }

    if (error || !results) {
        return (
            <div className="min-h-screen bg-stage-bg flex items-center justify-center text-white">
                <Header />
                <div className="text-center flex flex-col items-center pt-24">
                    <div className="w-16 h-16 bg-red-500/10 border border-red-500/30 rounded flex items-center justify-center mb-6 shadow-[0_0_15px_rgba(239,68,68,0.2)]">
                        <AlertTriangle className="w-8 h-8 text-red-500 animate-pulse" />
                    </div>
                    <p className="font-mono text-sm tracking-[0.2em] text-red-500 uppercase mb-4">{error || "SYSTEM FAILURE"}</p>
                    <button onClick={() => navigate('/')} className="text-xs font-mono uppercase tracking-[0.2em] text-white/40 hover:text-white transition-colors border-b border-white/20 hover:border-white pb-1">ABORT TO DOSIER</button>
                </div>
            </div>
        )
    }

    // Process data for UI
    const meta = results.metadata || {};
    const lighting = results.lighting_instructions || [];
    const emotions = meta.emotion_distribution || {};

    // Sort emotions for chart
    const emotionList = Object.entries(emotions)
        .sort((a, b) => b[1] - a[1])
        .map(([name, count]) => {
            const total = meta.total_scenes || 1;
            return {
                name,
                count,
                percent: Math.round((count / total) * 100),
                emoji: getEmoji(name),
                color: getColor(name)
            }
        });

    return (
        <div className="min-h-screen bg-stage-bg relative">
            <Header />

            {/* Reprocessing Overlay */}
            {reprocessing && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 backdrop-blur-md transition-all duration-300 animate-fade-in">
                    <style>{`
                        @keyframes indeterminate {
                            0% { transform: translateX(-100%); width: 30%; }
                            50% { width: 50%; }
                            100% { transform: translateX(250%); width: 30%; }
                        }
                        .animate-indeterminate {
                            animation: indeterminate 1.5s infinite cubic-bezier(0.65, 0.815, 0.735, 0.395);
                        }
                    `}</style>
                    <div className="max-w-md w-full p-8 bg-[#00d4ff]/5 border border-[#00d4ff]/30 flex flex-col items-center backdrop-blur-xl shadow-[0_0_30px_rgba(0,212,255,0.15)] rounded">
                        <div className="w-16 h-16 rounded bg-[#00d4ff]/10 flex items-center justify-center mb-6 border border-[#00d4ff]/30 shadow-[0_0_20px_rgba(0,212,255,0.3)]">
                            <Loader2 className="w-8 h-8 text-[#00d4ff] animate-spin" />
                        </div>
                        <h2 className="text-xl font-mono font-bold text-white mb-2 uppercase tracking-widest text-[#00d4ff]">RE-INITIALIZING ENGINE</h2>
                        <p className="text-white/40 text-center mb-8 text-xs font-mono uppercase tracking-wide leading-relaxed">
                            EXECUTING FULL STACK RE-COMPILE. MAINTAIN CONNECTION...
                        </p>

                        <div className="w-full h-1 bg-[#00d4ff]/10 overflow-hidden relative shadow-inner">
                            <div className="h-full bg-[#00d4ff] absolute top-0 left-0 animate-indeterminate shadow-[0_0_15px_rgba(0,212,255,1)]"></div>
                        </div>
                    </div>
                </div>
            )}

            {/* AI Resolution Overlay */}
            {aiResolving && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 backdrop-blur-md transition-all duration-300 animate-fade-in">
                    <div className="max-w-md w-full p-8 bg-purple-500/5 border border-purple-500/30 flex flex-col items-center backdrop-blur-xl shadow-[0_0_30px_rgba(168,85,247,0.15)] rounded">
                        <div className="w-16 h-16 rounded bg-purple-500/10 flex items-center justify-center mb-6 border border-purple-500/30 shadow-[0_0_20px_rgba(168,85,247,0.3)]">
                            <Zap className="w-8 h-8 text-purple-400 animate-pulse" />
                        </div>
                        <h2 className="text-xl font-mono font-bold text-white mb-2 uppercase tracking-widest text-purple-400">APPLYING NEURAL PATCH</h2>
                        <p className="text-white/40 text-center mb-8 text-xs font-mono uppercase tracking-wide leading-relaxed">
                            INJECTING RESOLUTION PROTOCOLS INTO LOCAL ENGINE STATE. RE-EVALUATING METRICS...
                        </p>

                        <div className="w-full h-1 bg-purple-500/10 overflow-hidden relative shadow-inner">
                            <div className="h-full bg-purple-400 absolute top-0 left-0 animate-indeterminate shadow-[0_0_15px_rgba(168,85,247,1)]"></div>
                        </div>
                    </div>
                </div>
            )}

            <main className="pt-24 pb-16 px-6">
                <div className="max-w-4xl mx-auto page-enter animate-fade-in">


                    {/* Header */}
                    <div className="text-center mb-10">
                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded bg-[#00d4ff]/10 border border-[#00d4ff]/30 text-[#00d4ff] text-[10px] uppercase font-mono tracking-[0.2em] shadow-[0_0_10px_rgba(0,212,255,0.1)] mb-4">
                            <span className="w-2 h-2 rounded-full bg-[#00d4ff] shadow-[0_0_8px_#00d4ff]" />
                            ANALYSIS COMPLETE
                        </div>
                        <h1 className="text-3xl md:text-5xl font-display font-black text-transparent bg-clip-text bg-gradient-to-r from-white to-white/50 mb-3 uppercase tracking-tight">
                            {meta.source_file || "SCRIPT.DATA"}
                        </h1>
                        <p className="text-white/40 font-mono text-xs uppercase tracking-widest">
                            JOB_ID // <span className="text-[#00d4ff]">{jobId?.slice(0, 8)}...</span>
                        </p>
                    </div>

                    {/* Tabs */}
                    <div className="flex items-center justify-center gap-2 mb-8 bg-white/[0.02] p-1.5 rounded-2xl mx-auto w-fit border border-white/[0.05]">
                        {['overview', 'timeline', 'cues'].map((tab) => (
                            <button
                                key={tab}
                                onClick={() => setActiveTab(tab)}
                                className={`px-6 py-2 rounded-xl text-sm font-mono capitalize transition-all duration-300 ${activeTab === tab
                                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 shadow-[0_0_15px_rgba(16,185,129,0.1)]'
                                    : 'text-white/40 hover:text-white/80 hover:bg-white/[0.05] border border-transparent'
                                    }`}
                            >
                                {tab === 'overview' && 'Overview'}
                                {tab === 'timeline' && 'Scene Timeline'}
                                {tab === 'cues' && 'Lighting Cues'}
                            </button>
                        ))}
                    </div>

                    {/* Tab Content: OVERVIEW */}
                    {activeTab === 'overview' && (
                        <div className="animate-fade-in-up">
                            {/* Stats Grid */}
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                                {[
                                    { label: 'Scenes', value: meta.total_scenes, icon: <Film className="w-6 h-6 text-emerald-400 mx-auto" /> },
                                    { label: 'Dominant Emotion', value: meta.dominant_emotion, icon: <BrainCircuit className="w-6 h-6 text-purple-400 mx-auto" /> },
                                    { label: 'Lighting Cues', value: lighting.length, icon: <Lightbulb className="w-6 h-6 text-amber-400 mx-auto" /> },
                                    { label: 'Genre', value: meta.genre, icon: <PlaySquare className="w-6 h-6 text-blue-400 mx-auto" /> },
                                ].map((stat, i) => (
                                    <div
                                        key={stat.label}
                                        className="glass-card p-5 text-center flex flex-col items-center"
                                    >
                                        <span className="block mb-2">{stat.icon}</span>
                                        <span className="text-xl font-display font-bold text-white capitalize">{stat.value}</span>
                                        <span className="text-xs text-white/40 block mt-1">{stat.label}</span>
                                    </div>
                                ))}
                            </div>

                            {/* Evaluation Metrics Component */}
                            <div className="glass-card p-6 mb-8">
                                <EvaluationMetrics
                                    metrics={metrics}
                                    loading={metricsLoading}
                                    activeTab="overview"
                                    jobId={jobId}
                                    onResolutionApplied={handleReevaluate}
                                />
                            </div>
                        </div>
                    )}

                    {/* Tab Content: SCENE TIMELINE */}
                    {activeTab === 'timeline' && (
                        <div className="animate-fade-in-up">
                            <div className="glass-card p-6 mb-8">
                                <EvaluationMetrics
                                    metrics={metrics}
                                    loading={metricsLoading}
                                    activeTab="timeline"
                                    jobId={jobId}
                                    onResolutionApplied={handleReevaluate}
                                />
                            </div>
                        </div>
                    )}

                    {/* Tab Content: LIGHTING CUES */}
                    {activeTab === 'cues' && (
                        <div className="animate-fade-in-up">
                            <div className="glass-card p-6 mb-8">
                                <h2 className="text-xs font-mono text-white/40 uppercase tracking-widest mb-5">
                                    Generated Lighting Instructions
                                </h2>
                                <div className="space-y-4">
                                    {lighting.map((cue, idx) => (
                                        <div key={idx} className="bg-white/[0.02] border border-white/[0.05] p-4 rounded-xl">
                                            <div className="flex justify-between items-center mb-3">
                                                <span className="text-emerald-400 font-mono text-sm">{cue.scene_id}</span>
                                                <span className="text-white/40 text-xs">Groups: {cue.groups?.length || 0}</span>
                                            </div>
                                            <div className="text-xs font-mono text-white/60 bg-black/30 p-3 rounded-lg overflow-x-auto">
                                                <pre>{JSON.stringify(cue, null, 2)}</pre>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Actions */}
                    <div className="text-center flex flex-col items-center space-y-4 pt-8">
                        <button
                            onClick={handleLaunch}
                            disabled={launching || (metrics?.pipeline_status === 'Blocked')}
                            className={`group relative px-10 py-4 bg-[#00d4ff]/10 border border-[#00d4ff]/50 
                            text-[#00d4ff] font-mono text-sm uppercase tracking-[0.2em] transition-all duration-300
                            shadow-[0_0_20px_rgba(0,212,255,0.15)] flex items-center justify-center gap-3 overflow-hidden ${launching || (metrics?.pipeline_status === 'Blocked') ? 'opacity-50 cursor-not-allowed border-gray-500/50 text-gray-400 bg-gray-500/10 shadow-none' : 'hover:bg-[#00d4ff]/20 hover:shadow-[0_0_35px_rgba(0,212,255,0.3)]'}`}
                        >
                            {!(launching || (metrics?.pipeline_status === 'Blocked')) && <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700 ease-in-out" />}
                            <span className="relative z-10 font-bold flex items-center gap-2">
                                {launching ? <><div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" /> INITIALIZING...</> : <><Play className="w-5 h-5 fill-current" /> EXECUTE 3D SIMULATION</>}
                            </span>
                        </button>

                        <div className="flex items-center justify-center gap-4 mt-4 flex-wrap">
                            <button
                                onClick={handleReprocess}
                                disabled={reprocessing}
                                className="px-5 py-2.5 bg-black/40 border border-[#00d4ff]/30 text-[#00d4ff] font-mono text-[10px] uppercase tracking-widest hover:bg-[#00d4ff]/10 hover:border-[#00d4ff]/50 transition-colors rounded flex items-center gap-2"
                            >
                                {reprocessing ? <><div className="w-3 h-3 border border-[#00d4ff] border-t-transparent rounded-full animate-spin" /> RE-COMPILING...</> : <><Rocket className="w-4 h-4" /> RE-PROCESS SCRIPT</>}
                            </button>
                            <a
                                href={getDownloadUrl(jobId)}
                                download
                                className="px-5 py-2.5 bg-black/40 border border-[#00d4ff]/30 text-[#00d4ff] font-mono text-[10px] uppercase tracking-widest hover:bg-[#00d4ff]/10 hover:border-[#00d4ff]/50 transition-colors rounded flex items-center gap-2"
                            >
                                <Download className="w-4 h-4" /> EXPORT CUES.JSON
                            </a>
                            <button
                                onClick={() => navigate('/upload')}
                                className="px-5 py-2.5 bg-black/40 border border-[#00d4ff]/30 text-[#00d4ff] font-mono text-[10px] uppercase tracking-widest hover:bg-[#00d4ff]/10 hover:border-[#00d4ff]/50 transition-colors rounded flex items-center gap-2"
                            >
                                <Plus className="w-4 h-4" /> NEW WORKSPACE
                            </button>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    )
}

// Helpers — 19 extended emotions
function getEmoji(emotion) {
    const map = {
        joy: <Smile className="w-4 h-4 text-amber-500" />,
        fear: <Ghost className="w-4 h-4 text-purple-500" />,
        anger: <Angry className="w-4 h-4 text-red-500" />,
        sadness: <Frown className="w-4 h-4 text-blue-500" />,
        surprise: <Zap className="w-4 h-4 text-cyan-400" />,
        disgust: <Bug className="w-4 h-4 text-green-500" />,
        neutral: <Meh className="w-4 h-4 text-gray-400" />,
        nostalgia: <Clock className="w-4 h-4 text-amber-300" />,
        mystery: <Eye className="w-4 h-4 text-indigo-400" />,
        romantic: <Heart className="w-4 h-4 text-pink-400" />,
        anticipation: <Hourglass className="w-4 h-4 text-orange-400" />,
        hope: <Sun className="w-4 h-4 text-yellow-300" />,
        triumph: <Trophy className="w-4 h-4 text-yellow-500" />,
        tension: <AlertOctagon className="w-4 h-4 text-orange-600" />,
        despair: <CloudRain className="w-4 h-4 text-slate-500" />,
        serenity: <Flower2 className="w-4 h-4 text-teal-400" />,
        confusion: <HelpCircle className="w-4 h-4 text-violet-400" />,
        awe: <Star className="w-4 h-4 text-sky-400" />,
        jealousy: <Swords className="w-4 h-4 text-lime-500" />,
    };
    return map[emotion] || <Meh className="w-4 h-4 text-gray-500" />;
}

function getColor(emotion) {
    const map = {
        joy: 'bg-amber-500',
        fear: 'bg-purple-500',
        anger: 'bg-red-500',
        sadness: 'bg-blue-500',
        surprise: 'bg-cyan-400',
        disgust: 'bg-green-500',
        neutral: 'bg-gray-400',
        nostalgia: 'bg-amber-300',
        mystery: 'bg-indigo-400',
        romantic: 'bg-pink-400',
        anticipation: 'bg-orange-400',
        hope: 'bg-yellow-300',
        triumph: 'bg-yellow-500',
        tension: 'bg-orange-600',
        despair: 'bg-slate-500',
        serenity: 'bg-teal-400',
        confusion: 'bg-violet-400',
        awe: 'bg-sky-400',
        jealousy: 'bg-lime-500',
    };
    return map[emotion] || 'bg-gray-500';
}
