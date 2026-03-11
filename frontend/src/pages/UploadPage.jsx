import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadScript, validateScript } from '../utils/api'
import Header from '../components/layout/Header'
import FileDropZone from '../components/ui/FileDropZone'
import { FileText, File, Loader2, Rocket, ArrowLeft, AlertTriangle } from 'lucide-react'

export default function UploadPage() {
    const navigate = useNavigate()
    const [file, setFile] = useState(null)
    const [preview, setPreview] = useState(null)
    const [title, setTitle] = useState('')
    const [model, setModel] = useState('Open AI')

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
            const response = await uploadScript(file);
            console.log("Upload success:", response);

            // Navigate to processing page with actual Job ID
            navigate(`/processing/${response.job_id}`);
        } catch (err) {
            console.error("Process failed", err);
            setError("Failed to process file. Please try again.");
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

                    {/* Process Button */}
                    {file && (
                        <div className="text-center animate-fade-in mt-6">
                            {error && (
                                <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 mb-6 flex items-start gap-4 text-left animate-slide-up mx-auto max-w-xl">
                                    <div className="bg-red-500/20 p-2 rounded-lg shrink-0 mt-0.5">
                                        <AlertTriangle className="w-5 h-5 text-red-400" />
                                    </div>
                                    <div>
                                        <h4 className="text-red-400 font-medium text-sm mb-1">File Rejected By System</h4>
                                        <p className="text-red-400/80 text-xs leading-relaxed">{error}</p>
                                    </div>
                                </div>
                            )}
                            <button
                                onClick={handleProcess}
                                disabled={isUploading}
                                className={`group relative px-6 py-3 bg-[#00d4ff]/10 hover:bg-[#00d4ff]/20 border border-[#00d4ff]/50 
                                text-[#00d4ff] font-mono text-xs uppercase tracking-[0.2em] transition-all duration-300
                                shadow-[0_0_15px_rgba(0,212,255,0.1)] hover:shadow-[0_0_25px_rgba(0,212,255,0.2)] flex items-center justify-center gap-3 overflow-hidden mx-auto ${isUploading ? 'opacity-50 cursor-not-allowed border-gray-500/50 text-gray-400 bg-gray-500/10' : ''}`}
                            >
                                {!isUploading && <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700 ease-in-out" />}
                                <span className="relative z-10 font-bold flex items-center gap-2">
                                    {isUploading ? (
                                        <><div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" /> EXECUTING...</>
                                    ) : (
                                        <>ENGAGE PIPELINE</>
                                    )}
                                </span>
                            </button>
                            <p className="text-xs text-white/30 mt-3">
                                This will run the full AI pipeline (Phase 1—6)
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
            </main>
        </div>
    )
}
