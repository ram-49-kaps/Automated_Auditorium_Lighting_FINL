import { useState } from 'react'
import { Activity, BarChart3, Layers, Gauge, Shield, ChevronDown, ChevronUp, CheckCircle2, AlertTriangle, XCircle, Zap, Search, Loader2, Check } from 'lucide-react'
import { applyResolution } from '../../utils/api'

export default function EvaluationMetrics({ metrics, loading, activeTab = 'overview', jobId, onResolutionApplied }) {
    const [expandedScene, setExpandedScene] = useState(null)
    const [activeCheckPill, setActiveCheckPill] = useState(null)
    const [applyingFix, setApplyingFix] = useState(false)
    const [aiSuccessMessage, setAiSuccessMessage] = useState(null)

    if (loading) {
        return (
            <div className="space-y-4">
                <h2 className="text-xs font-mono text-white/40 uppercase tracking-widest">
                    Evaluation Metrics
                </h2>
                <div className="flex items-center justify-center py-12">
                    <div className="w-6 h-6 border-2 border-emerald-400/30 border-t-emerald-400 rounded-full animate-spin" />
                    <span className="ml-3 text-sm text-white/40">Computing metrics...</span>
                </div>
            </div>
        )
    }

    if (!metrics) return null

    const {
        coverage = 0,
        parameter_diversity = 0,
        drift_score = 0,
        intensity_range = [0, 0],
        transition_types = [],
        determinism = 0,
        total_scenes = 0,
        knowledge_rules = 0,
        rag_documents = 0,
        scene_details = [],
        overall_verdict = 'WARN',
        pipeline_status = 'Pending',
        pass_count = 0,
        total_conflicts = 0
    } = metrics

    const pct = (v) => `${(v * 100).toFixed(0)}%`

    // Emotion color map
    const emotionColor = {
        joy: '#f59e0b', fear: '#a855f7', anger: '#ef4444', sadness: '#3b82f6',
        surprise: '#22d3ee', disgust: '#22c55e', neutral: '#9ca3af',
        nostalgia: '#fcd34d', mystery: '#818cf8', romantic: '#f472b6',
        anticipation: '#fb923c', hope: '#fde047', triumph: '#eab308',
        tension: '#ea580c', despair: '#64748b', serenity: '#2dd4bf',
        confusion: '#a78bfa', awe: '#38bdf8', jealousy: '#84cc16',
    }

    // Overall verdict badge mapping
    const verdictMap = {
        'PASS': { icon: <CheckCircle2 className="w-8 h-8 text-emerald-400" />, color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20' },
        'WARN': { icon: <AlertTriangle className="w-8 h-8 text-amber-400" />, color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/20' },
        'FAIL': { icon: <XCircle className="w-8 h-8 text-red-400" />, color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/20' }
    }
    const currentVerdict = verdictMap[overall_verdict] || verdictMap['WARN']

    // Helper for rendering the 8-check pills
    const renderCheckPill = (label, evalData) => {
        if (!evalData) return null;
        let colors = ""
        const status = evalData.status;

        // Base Status Colors
        if (status === 'PASS') colors = "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
        else if (status === 'WARN') colors = "bg-amber-500/10 text-amber-400 border-amber-500/20"
        else if (status === 'FAIL') colors = "bg-red-500/10 text-red-400 border-red-500/20"
        else colors = "bg-white/5 text-white/30 border-white/10" // SKIP

        // Selection Highlight
        const isActive = activeCheckPill === label;
        if (isActive) {
            colors += " ring-2 ring-white/50 bg-white/10 shadow-[0_0_15px_rgba(255,255,255,0.15)]";
        }

        return (
            <button
                key={label}
                onClick={(e) => {
                    e.stopPropagation();
                    setActiveCheckPill(isActive ? null : label);
                }}
                title={status}
                className={`px-2 py-1 rounded text-[10px] uppercase font-mono border flex-1 text-center truncate hover:brightness-125 transition-all ${colors}`}
            >
                [{label}]
            </button>
        )
    }

    const handleApplyFix = async (sceneId, rule) => {
        setApplyingFix(true);
        setAiSuccessMessage(null);
        try {
            const response = await applyResolution(jobId, sceneId, rule);
            setAiSuccessMessage(response.message || "Resolution applied successfully!");

            if (onResolutionApplied) {
                await onResolutionApplied(); // Trigger a re-fetch of results
            }

            // Clear success message after 4 seconds
            setTimeout(() => {
                setAiSuccessMessage(null);
            }, 4000);

        } catch (err) {
            console.error("Failed to apply fix:", err);
            alert("Failed to apply the AI resolution.");
        } finally {
            setApplyingFix(false);
        }
    }

    if (activeTab === 'overview') {
        return (
            <div className="space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h2 className="text-xs font-mono text-white/40 uppercase tracking-widest">
                            Phase 7 — Verdict Summary
                        </h2>
                        <p className="text-[11px] text-white/25 mt-1">
                            {total_scenes} scenes • {knowledge_rules} rules applied
                        </p>
                    </div>
                </div>

                {/* Hero Verdict Badge */}
                <div className={`p-6 rounded-2xl border flex items-center gap-6 ${currentVerdict.bg} ${currentVerdict.border}`}>
                    <div className="flex-shrink-0 animate-pulse-glow">
                        {currentVerdict.icon}
                    </div>
                    <div>
                        <div className="flex items-center gap-3">
                            <h3 className={`text-2xl font-display font-bold ${currentVerdict.color}`}>
                                VERDICT: {overall_verdict}
                            </h3>
                            <span className={`px-2 py-0.5 rounded text-[10px] font-mono border uppercase tracking-widest ${currentVerdict.bg} ${currentVerdict.border} ${currentVerdict.color}`}>
                                {pipeline_status}
                            </span>
                        </div>
                        <p className="text-white/60 text-sm mt-1">
                            System evaluation passed {pass_count} out of {total_scenes} scenes successfully.
                        </p>
                    </div>
                </div>

                {/* Primary Stats */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                    <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-4 text-center">
                        <div className="text-[10px] text-white/30 font-mono mb-1 uppercase tracking-widest">Avg Coherence</div>
                        <div className="text-2xl font-display font-bold text-white">{(coverage * 100).toFixed(0)}%</div>
                    </div>
                    <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-4 text-center">
                        <div className="text-[10px] text-white/30 font-mono mb-1 uppercase tracking-widest">Avg Drift Score</div>
                        <div className={`text-2xl font-display font-bold ${drift_score > 0.3 ? 'text-amber-400' : 'text-emerald-400'}`}>
                            {drift_score.toFixed(2)}
                        </div>
                    </div>
                    <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-4 text-center">
                        <div className="text-[10px] text-white/30 font-mono mb-1 uppercase tracking-widest">Conflicts</div>
                        <div className={`text-2xl font-display font-bold ${total_conflicts > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>{total_conflicts}</div>
                    </div>
                    <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-4 text-center">
                        <div className="text-[10px] text-white/30 font-mono mb-1 uppercase tracking-widest">Transitions</div>
                        <div className="text-2xl font-display font-bold text-white">{transition_types.length}</div>
                    </div>
                </div>
            </div>
        )
    }

    if (activeTab === 'timeline') {
        return (
            <div className="space-y-6">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xs font-mono text-white/40 uppercase tracking-widest">
                        Scene Timeline (8-Check System)
                    </h2>
                    <div className="flex gap-2 items-center">
                        <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">PASS</span>
                        <span className="text-[10px] text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">WARN</span>
                        <span className="text-[10px] text-red-400 bg-red-500/10 px-2 py-0.5 rounded border border-red-500/20">FAIL</span>
                        <span className="text-[10px] text-white/30 bg-white/5 px-2 py-0.5 rounded border border-white/10">SKIP</span>
                    </div>
                </div>

                <div className="space-y-3">
                    {scene_details.map((scene, i) => (
                        <div
                            key={scene.scene_id}
                            onClick={() => {
                                setExpandedScene(expandedScene === scene.scene_id ? null : scene.scene_id);
                                if (expandedScene !== scene.scene_id) setActiveCheckPill(null); // Reset pill when closing/switching scenes
                            }}
                            className={`relative glass-card p-4 flex flex-col gap-3 group cursor-pointer transition-colors hover:bg-white/[0.04] ${expandedScene === scene.scene_id ? 'border-emerald-500/30 bg-white/[0.04]' : ''}`}
                        >

                            {/* Scene Header */}
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="w-6 h-6 rounded-full bg-white/5 flex items-center justify-center font-mono text-[10px] text-white/40">
                                        {i + 1}
                                    </div>
                                    <span className="font-mono text-sm font-semibold">{scene.scene_id}</span>
                                    <span
                                        className="px-2 py-0.5 rounded text-[10px] capitalize font-semibold"
                                        style={{ backgroundColor: `${emotionColor[scene.emotion] || '#9ca3af'}22`, color: emotionColor[scene.emotion] || '#9ca3af' }}
                                    >
                                        {scene.emotion}
                                    </span>
                                    <span className="text-[11px] text-white/40 ml-2">Int: {scene.avg_intensity}%</span>
                                </div>

                                <div className={`px-2 py-1 rounded text-[10px] font-mono border font-bold ${verdictMap[scene.verdict]?.bg} ${verdictMap[scene.verdict]?.border} ${verdictMap[scene.verdict]?.color}`}>
                                    {scene.verdict}
                                </div>
                            </div>

                            {/* The 8 Check System Row */}
                            {scene.checks && (
                                <div className="flex gap-2 w-full mt-2">
                                    {renderCheckPill("SCH", scene.checks.SCH)}
                                    {renderCheckPill("HRD", scene.checks.HRD)}
                                    {renderCheckPill("CFT", scene.checks.CFT)}
                                    {renderCheckPill("STB", scene.checks.STB)}
                                    {renderCheckPill("DRF", scene.checks.DRF)}
                                    {renderCheckPill("CNF", scene.checks.CNF)}
                                    {renderCheckPill("NAR", scene.checks.NAR)}
                                    {renderCheckPill("COH", scene.checks.COH)}
                                </div>
                            )}

                            {/* Detailed Breakdown Tray */}
                            {expandedScene === scene.scene_id && (
                                <div className="mt-2 pt-4 border-t border-white/10 animate-fade-in-up cursor-default" onClick={e => e.stopPropagation()}>

                                    {/* Active Check Inspect Panel */}
                                    {activeCheckPill ? (
                                        <div className="bg-black/40 border border-white/10 rounded-xl p-4 mb-4">
                                            <div className="flex justify-between items-start mb-2">
                                                <h4 className="text-[11px] font-mono text-white/50 uppercase tracking-widest flex items-center gap-2">
                                                    <Search className="w-3 h-3" /> Diagnostics: [{activeCheckPill}]
                                                </h4>
                                                <button onClick={() => setActiveCheckPill(null)} className="text-white/30 hover:text-white/60 text-xs">Close</button>
                                            </div>

                                            {scene.checks && scene.checks[activeCheckPill] && (
                                                <div className="space-y-3 text-sm leading-relaxed mt-4">
                                                    <div>
                                                        <span className="text-white/40 block text-xs mb-0.5">Rule Strategy</span>
                                                        <p className="text-white/90 font-medium">{scene.checks[activeCheckPill].definition}</p>
                                                    </div>

                                                    <div className="border-l-2 border-white/20 pl-3">
                                                        <span className="text-white/40 block text-xs mb-0.5 mt-1">Computation Data</span>
                                                        <p className="text-white/70">{scene.checks[activeCheckPill].reasoning}</p>
                                                    </div>

                                                    {scene.checks[activeCheckPill].resolution && (
                                                        <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg mt-4">
                                                            <span className="text-amber-400 block text-xs mb-1 font-bold tracking-wide">💡 AI RESOLUTION PREDICTION</span>
                                                            <p className="text-amber-100/80 text-[13px]">{scene.checks[activeCheckPill].resolution}</p>

                                                            {aiSuccessMessage ? (
                                                                <div className="mt-3 bg-emerald-500/20 text-emerald-300 text-xs px-4 py-2.5 rounded-md border border-emerald-500/30 flex items-center gap-2 animate-fade-in">
                                                                    <Check className="w-4 h-4" />
                                                                    <span className="font-semibold">{aiSuccessMessage}</span>
                                                                </div>
                                                            ) : (
                                                                <button
                                                                    onClick={(e) => {
                                                                        e.stopPropagation();
                                                                        handleApplyFix(scene.scene_id, activeCheckPill);
                                                                    }}
                                                                    disabled={applyingFix}
                                                                    className="mt-3 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 text-xs px-4 py-1.5 rounded-md transition-colors border border-amber-500/30 flex items-center gap-2"
                                                                >
                                                                    {applyingFix ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Applying Fix...</> : <><Zap className="w-3.5 h-3.5" /> Apply AI Resolution</>}
                                                                </button>
                                                            )}
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    ) : (
                                        <>
                                            <h4 className="text-xs font-mono text-white/40 mb-3 uppercase tracking-widest flex items-center justify-between">
                                                <span>Scene {i + 1} Analytics</span>
                                                <span className="text-[9px] text-white/30 bg-white/5 px-2 py-0.5 rounded-full ring-1 ring-white/10">Click any pill above for AI Diagnostics</span>
                                            </h4>

                                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                                <div className="bg-black/20 rounded-lg p-3">
                                                    <div className="text-[10px] text-white/40 font-mono mb-1 uppercase tracking-widest">ML Confidence</div>
                                                    <div className="text-sm font-semibold">{scene.confidence > 0 ? `${(scene.confidence * 100).toFixed(1)}%` : 'Bypassed'}</div>
                                                </div>
                                                <div className="bg-black/20 rounded-lg p-3">
                                                    <div className="text-[10px] text-white/40 font-mono mb-1 uppercase tracking-widest">Active Groups</div>
                                                    <div className="text-sm font-semibold">{scene.num_groups} active</div>
                                                </div>
                                                <div className="bg-black/20 rounded-lg p-3">
                                                    <div className="text-[10px] text-white/40 font-mono mb-1 uppercase tracking-widest">Transition</div>
                                                    <div className="text-sm font-semibold capitalize">{scene.transition_type}</div>
                                                </div>
                                                <div className="bg-black/20 rounded-lg p-3">
                                                    <div className="text-[10px] text-white/40 font-mono mb-1 uppercase tracking-widest">Generated Palettes</div>
                                                    <div className="flex gap-1 flex-wrap mt-1">
                                                        {scene.colors?.length > 0 ? scene.colors.map(c =>
                                                            <span key={c} className="text-[9px] px-1.5 py-0.5 rounded bg-white/10 capitalize border border-white/5">{c.replace('_', ' ')}</span>
                                                        ) : <span className="text-xs text-white/30">Inherited</span>}
                                                    </div>
                                                </div>
                                            </div>
                                        </>
                                    )}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </div>
        )
    }

    return null
}
