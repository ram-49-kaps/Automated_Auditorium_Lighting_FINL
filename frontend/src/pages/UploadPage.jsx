import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadScript, validateScript } from '../utils/api'
import Header from '../components/layout/Header'
import FileDropZone from '../components/ui/FileDropZone'
import { FileText, File, Loader2, Rocket, ArrowLeft, AlertTriangle, Cpu, Layers, ChevronDown, Lock, Clapperboard, CalendarDays } from 'lucide-react'

// Available LLM models
const LLM_MODELS = [
    { value: 'rule_based', label: 'Rule-Based (No LLM)', provider: 'Local', active: true },
    { value: 'Qwen/Qwen2.5-7B-Instruct', label: 'Qwen 2.5 7B', provider: 'HuggingFace', active: true },
    { value: 'meta-llama/Llama-3.1-8B-Instruct', label: 'Llama 3.1 8B', provider: 'HuggingFace', active: true },
    { value: 'gpt-4o-mini', label: 'GPT-4o Mini', provider: 'OpenAI', active: true },
]

// Script type options
const SCRIPT_TYPES = [
    { value: 'theatrical_script', label: 'Drama / Act / Play', icon: 'Clapperboard', desc: 'Scenes, dialogue, stage directions' },
    { value: 'event_schedule', label: 'Event / Assembly', icon: 'CalendarDays', desc: 'Timed segments, speaker slots, programs' },
]

export default function UploadPage() {
    const navigate = useNavigate()
    const [file, setFile] = useState(null)
    const [preview, setPreview] = useState(null)
    const [title, setTitle] = useState('')

    // Pipeline configuration state
    const [pipelineMode, setPipelineMode] = useState('multi_stage')
    const [llmModel, setLlmModel] = useState('Qwen/Qwen2.5-7B-Instruct')
    const [scriptType, setScriptType] = useState('theatrical_script')

    const handleFileSelect = (selectedFile) => {
        setFile(selectedFile)

        // Auto-generate title from filename
        const name = selectedFile.name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ')
        setTitle(name)

        // Read preview for .txt files
        if (selectedFile.name.endsWith('.txt')) {
            const reader = new FileReader()
            reader.onload = (e) => {
                const text = e.target.result
                const lines = text.split('\n').slice(0, 6).join('\n')
                setPreview(lines)
            }
            reader.readAsText(selectedFile)
        } else {
            setPreview(`[${selectedFile.name.split('.').pop().toUpperCase()} file content — will be extracted during processing]`)
        }
    }

    const formatSize = (bytes) => {
        if (bytes < 1024) return bytes + ' B'
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    }

    const getFormatInfo = (filename) => {
        const ext = filename.split('.').pop().toLowerCase()
        const map = {
            txt: { icon: <FileText className="w-6 h-6 text-gray-400" />, label: 'Plain Text', color: 'text-gray-400 bg-gray-400/10 border-gray-400/20' },
            pdf: { icon: <FileText className="w-6 h-6 text-red-500" />, label: 'PDF Document', color: 'text-red-400 bg-red-400/10 border-red-400/20' },
            docx: { icon: <FileText className="w-6 h-6 text-blue-500" />, label: 'Word Document', color: 'text-blue-400 bg-blue-400/10 border-blue-400/20' },
        }
        return map[ext] || { icon: <File className="w-6 h-6 text-white/40" />, label: 'Unknown', color: 'text-white/40 bg-white/5 border-white/10' }
    }

    const [isUploading, setIsUploading] = useState(false)
    const [error, setError] = useState(null)

    const handleProcess = async () => {
        if (!file) return;

        setIsUploading(true);
        setError(null);

        try {
            // First, validate the script
            const validationResult = await validateScript(file);

            if (!validationResult.valid) {
                setError(validationResult.reason);
                setIsUploading(false);
                return; // Stop the process completely
            }

            // Proceed to upload & backend pipeline if valid
            const response = await uploadScript(file, pipelineMode, llmModel, scriptType);
            console.log("Upload success:", response);

            // Navigate to processing page with actual Job ID
            navigate(`/processing/${response.job_id}`);
        } catch (err) {
            console.error("Process failed", err);
            setError(err.message || "Failed to process file. Please try again.");
            setIsUploading(false);
        }
    }

    return (
        <div className="min-h-screen bg-stage-bg">
            <Header />

            <main className="pt-24 pb-16 px-6">
                <div className="max-w-2xl mx-auto page-enter">

                    {/* Page Title */}
                    <div className="text-center mb-10">
                        <span className="inline-flex items-center gap-2 px-3 py-1 bg-[#00d4ff]/10 border border-[#00d4ff]/30 text-[#00d4ff] text-[10px] font-mono uppercase tracking-[0.2em] rounded shadow-[0_0_10px_rgba(0,212,255,0.1)] mb-4">
                            [ PHASE 01 // DATA INGESTION ]
                        </span>
                        <h1 className="text-3xl md:text-5xl font-display font-black text-white mt-2 mb-3 uppercase tracking-tight">
                            INITIALIZE <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00d4ff] to-blue-600">WORKSPACE</span>
                        </h1>
                        <p className="text-white/40 font-mono text-xs uppercase tracking-widest">
                            Upload manuscript to authorize semantic routing
                        </p>
                    </div>

                    {/* Drop Zone */}
                    <div className="glass-card p-8 mb-6">
                        <FileDropZone onFileSelect={handleFileSelect} />
                    </div>

                    {/* File Preview */}
                    {file && (
                        <div className="glass-card p-6 mb-6 animate-slide-up">
                            {/* File Info */}
                            <div className="flex items-center justify-between mb-4">
                                <div className="flex items-center gap-3">
                                    <span className="flex items-center justify-center w-10 h-10 bg-black/20 rounded-lg">{getFormatInfo(file.name).icon}</span>
                                    <div>
                                        <h3 className="text-sm font-medium text-white/90">{file.name}</h3>
                                        <p className="text-xs text-white/40">{formatSize(file.size)}</p>
                                    </div>
                                </div>
                                <span className={`text-xs px-3 py-1 rounded-full border ${getFormatInfo(file.name).color}`}>
                                    {getFormatInfo(file.name).label} ✓
                                </span>
                            </div>

                            {/* Divider */}
                            <div className="border-t border-white/5 my-4" />

                            {/* Preview */}
                            {preview && (
                                <div className="mb-4">
                                    <span className="text-xs text-white/30 font-mono uppercase tracking-wider mb-2 block">
                                        Preview
                                    </span>
                                    <pre className="text-xs text-white/50 font-mono bg-black/20 rounded-lg p-4
                                  max-h-36 overflow-y-auto leading-relaxed whitespace-pre-wrap">
                                        {preview}
                                    </pre>
                                </div>
                            )}

                            {/* Script Title Input */}
                            <div>
                                <label className="text-xs text-white/30 font-mono uppercase tracking-wider mb-2 block">
                                    Script Title
                                </label>
                                <input
                                    type="text"
                                    value={title}
                                    onChange={(e) => setTitle(e.target.value)}
                                    className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5
                             text-sm text-white/80 font-body placeholder-white/20
                             focus:outline-none focus:border-stage-gold/50 focus:ring-1 focus:ring-stage-gold/20
                             transition-all duration-200"
                                    placeholder="Enter script title..."
                                />
                            </div>
                        </div>
                    )}

                    {/* ========================================================= */}
                    {/* PIPELINE MODE SELECTOR */}
                    {/* ========================================================= */}
                    {file && (
                        <div className="mb-6 animate-slide-up">
                            <span className="text-xs text-white/30 font-mono uppercase tracking-wider mb-3 block">
                                Pipeline Architecture
                            </span>
                            <div className="grid grid-cols-2 gap-3">
                                {/* Multi-Stage Card */}
                                <button
                                    onClick={() => setPipelineMode('multi_stage')}
                                    className={`relative p-4 rounded-xl border text-left transition-all duration-300 group
                                        ${pipelineMode === 'multi_stage'
                                            ? 'bg-[#00d4ff]/10 border-[#00d4ff]/50 shadow-[0_0_20px_rgba(0,212,255,0.15)]'
                                            : 'bg-white/[0.02] border-white/10 hover:border-white/20 hover:bg-white/[0.04]'
                                        }`}
                                >
                                    <div className="flex items-center gap-2 mb-2">
                                        <Layers className={`w-4 h-4 ${pipelineMode === 'multi_stage' ? 'text-[#00d4ff]' : 'text-white/40'}`} />
                                        <span className={`text-xs font-mono font-bold uppercase tracking-wider ${pipelineMode === 'multi_stage' ? 'text-[#00d4ff]' : 'text-white/60'}`}>
                                            Multi-Stage
                                        </span>
                                    </div>
                                    <p className="text-[10px] text-white/40 leading-relaxed">
                                        Chunked LLM processing with RAG, narrative memory, & sliding window context
                                    </p>
                                    {pipelineMode === 'multi_stage' && (
                                        <div className="absolute top-2 right-2 w-2 h-2 rounded-full bg-[#00d4ff] shadow-[0_0_6px_rgba(0,212,255,0.8)]" />
                                    )}
                                </button>

                                {/* Single-Pass Card */}
                                <button
                                    onClick={() => setPipelineMode('single_pass')}
                                    className={`relative p-4 rounded-xl border text-left transition-all duration-300 group
                                        ${pipelineMode === 'single_pass'
                                            ? 'bg-purple-500/10 border-purple-400/50 shadow-[0_0_20px_rgba(168,85,247,0.15)]'
                                            : 'bg-white/[0.02] border-white/10 hover:border-white/20 hover:bg-white/[0.04]'
                                        }`}
                                >
                                    <div className="flex items-center gap-2 mb-2">
                                        <Cpu className={`w-4 h-4 ${pipelineMode === 'single_pass' ? 'text-purple-400' : 'text-white/40'}`} />
                                        <span className={`text-xs font-mono font-bold uppercase tracking-wider ${pipelineMode === 'single_pass' ? 'text-purple-400' : 'text-white/60'}`}>
                                            Single-Pass
                                        </span>
                                    </div>
                                    <p className="text-[10px] text-white/40 leading-relaxed">
                                        Full script in one LLM call — eliminates drift, deterministic lighting
                                    </p>
                                    {pipelineMode === 'single_pass' && (
                                        <div className="absolute top-2 right-2 w-2 h-2 rounded-full bg-purple-400 shadow-[0_0_6px_rgba(168,85,247,0.8)]" />
                                    )}
                                    <span className="inline-block mt-2 text-[8px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300/80 border border-purple-500/30">
                                        experimental
                                    </span>
                                </button>
                            </div>
                        </div>
                    )}

                    {/* ========================================================= */}
                    {/* SCRIPT TYPE SELECTOR */}
                    {/* ========================================================= */}
                    {file && (
                        <div className="mb-6 animate-slide-up">
                            <span className="text-xs text-white/30 font-mono uppercase tracking-wider mb-3 block">
                                Script Type
                            </span>
                            <div className="grid grid-cols-2 gap-3">
                                {SCRIPT_TYPES.map((type) => (
                                    <button
                                        key={type.value}
                                        onClick={() => setScriptType(type.value)}
                                        className={`relative p-4 rounded-xl border text-left transition-all duration-300 group
                                            ${scriptType === type.value
                                                ? 'bg-stage-gold/10 border-stage-gold/50 shadow-[0_0_20px_rgba(255,186,8,0.15)]'
                                                : 'bg-white/[0.02] border-white/10 hover:border-white/20 hover:bg-white/[0.04]'
                                            }`}
                                    >
                                        <div className="flex items-center gap-2 mb-2">
                                            {type.value === 'theatrical_script'
                                                ? <Clapperboard className={`w-4 h-4 ${scriptType === type.value ? 'text-stage-gold' : 'text-white/40'}`} />
                                                : <CalendarDays className={`w-4 h-4 ${scriptType === type.value ? 'text-stage-gold' : 'text-white/40'}`} />
                                            }
                                            <span className={`text-xs font-mono font-bold uppercase tracking-wider ${scriptType === type.value ? 'text-stage-gold' : 'text-white/60'}`}>
                                                {type.label}
                                            </span>
                                        </div>
                                        <p className="text-[10px] text-white/40 leading-relaxed">
                                            {type.desc}
                                        </p>
                                        {scriptType === type.value && (
                                            <div className="absolute top-2 right-2 w-2 h-2 rounded-full bg-stage-gold shadow-[0_0_6px_rgba(255,186,8,0.8)]" />
                                        )}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* ========================================================= */}
                    {/* LLM MODEL SELECTOR */}
                    {/* ========================================================= */}
                    {file && (
                        <div className="mb-6 animate-slide-up">
                            <span className="text-xs text-white/30 font-mono uppercase tracking-wider mb-3 block">
                                LLM Model
                            </span>
                            <div className="relative">
                                <select
                                    value={llmModel}
                                    onChange={(e) => setLlmModel(e.target.value)}
                                    className="w-full appearance-none bg-white/[0.03] border rounded-xl px-4 py-3 pr-10 text-sm font-mono transition-all duration-200 cursor-pointer focus:outline-none focus:ring-1 border-white/10 text-white/80 hover:border-white/20 focus:border-[#00d4ff]/50 focus:ring-[#00d4ff]/20"
                                >
                                    {LLM_MODELS.map((model) => (
                                        <option
                                            key={model.value}
                                            value={model.value}
                                            className="bg-[#0a0a14] text-white"
                                        >
                                            {model.label} ({model.provider}){!model.active ? ' — Coming Soon' : ''}
                                        </option>
                                    ))}
                                </select>
                                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none text-white/40" />
                            </div>

                            {/* Ollama badge */}
                            {llmModel === 'ollama/local' && (
                                <div className="mt-2 flex items-center gap-2 px-3 py-1.5 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                                    <Lock className="w-3 h-3 text-amber-400" />
                                    <span className="text-[10px] text-amber-400/80 font-mono">
                                        Ollama integration is not yet available. Select a HuggingFace model to proceed.
                                    </span>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Process Button */}
                    {file && (
                        <div className="text-center animate-fade-in mt-6">
                            {error && (
                                <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 mb-6 flex items-start gap-4 text-left animate-slide-up mx-auto max-w-xl">
                                    <div className="bg-red-500/20 p-2 rounded-lg shrink-0 mt-0.5">
                                        <AlertTriangle className="w-5 h-5 text-red-400" />
                                    </div>
                                    <div>
                                        <h4 className="text-red-400 font-medium text-sm mb-1">Pipeline Error</h4>
                                        <p className="text-red-400/80 text-xs leading-relaxed">{error}</p>
                                    </div>
                                </div>
                            )}

                            <button
                                onClick={handleProcess}
                                disabled={isUploading || llmModel === 'ollama/local'}
                                className={`group relative px-6 py-3 border 
                                text-xs font-mono uppercase tracking-[0.2em] transition-all duration-300
                                flex items-center justify-center gap-3 overflow-hidden mx-auto
                                ${isUploading || llmModel === 'ollama/local'
                                        ? 'opacity-50 cursor-not-allowed border-gray-500/50 text-gray-400 bg-gray-500/10'
                                        : pipelineMode === 'single_pass'
                                            ? 'bg-purple-500/10 hover:bg-purple-500/20 border-purple-400/50 text-purple-400 shadow-[0_0_15px_rgba(168,85,247,0.1)] hover:shadow-[0_0_25px_rgba(168,85,247,0.2)]'
                                            : 'bg-[#00d4ff]/10 hover:bg-[#00d4ff]/20 border-[#00d4ff]/50 text-[#00d4ff] shadow-[0_0_15px_rgba(0,212,255,0.1)] hover:shadow-[0_0_25px_rgba(0,212,255,0.2)]'
                                    }`}
                            >
                                {!isUploading && <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700 ease-in-out" />}
                                <span className="relative z-10 font-bold flex items-center gap-2">
                                    {isUploading ? (
                                        <><div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" /> EXECUTING...</>
                                    ) : (
                                        <>ENGAGE {pipelineMode === 'single_pass' ? 'FULL-CONTEXT' : ''} PIPELINE</>
                                    )}
                                </span>
                            </button>
                            <p className="text-xs text-white/30 mt-3">
                                {pipelineMode === 'single_pass'
                                    ? 'Single-pass experimental pipeline — full script sent in one LLM call'
                                    : 'Multi-stage pipeline (Phase 1—6) with RAG knowledge layer'
                                }
                            </p>
                        </div>
                    )}

                    {/* Back Link */}
                    <div className="text-center mt-8">
                        <button
                            onClick={() => navigate('/')}
                            className="text-xs text-white/30 hover:text-white/60 transition-colors flex items-center justify-center gap-2 mx-auto"
                        >
                            <ArrowLeft className="w-4 h-4" /> Back to Home
                        </button>
                    </div>
                </div>
            </main >
        </div >
    )
}
