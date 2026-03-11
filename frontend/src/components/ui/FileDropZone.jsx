import { useState, useRef } from 'react'

export default function FileDropZone({ onFileSelect }) {
    const [isDragging, setIsDragging] = useState(false)
    const [error, setError] = useState('')
    const inputRef = useRef(null)

    const ALLOWED = ['.txt', '.pdf', '.docx']

    const validateFile = (file) => {
        const ext = '.' + file.name.split('.').pop().toLowerCase()
        if (!ALLOWED.includes(ext)) {
            setError(`Unsupported format: ${ext}. Use PDF, TXT, or DOCX.`)
            return false
        }
        if (file.size > 10 * 1024 * 1024) {
            setError('File too large. Maximum 10MB.')
            return false
        }
        setError('')
        return true
    }

    const handleDrop = (e) => {
        e.preventDefault()
        setIsDragging(false)
        const file = e.dataTransfer.files[0]
        if (file && validateFile(file)) {
            onFileSelect(file)
        }
    }

    const handleChange = (e) => {
        const file = e.target.files[0]
        if (file && validateFile(file)) {
            onFileSelect(file)
        }
    }

    const formatIcon = (ext) => {
        switch (ext) {
            case '.pdf': return '📕'
            case '.docx': return '📘'
            case '.txt': return '📄'
            default: return '📁'
        }
    }

    return (
        <div>
            <div
                className={`drop-zone p-12 flex flex-col items-center justify-center cursor-pointer
                    min-h-[260px] relative group ${isDragging ? 'drag-over' : ''} ${error ? 'border-red-500/50' : ''}`}
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                onClick={() => inputRef.current?.click()}
            >
                {/* Hidden Input */}
                <input
                    ref={inputRef}
                    type="file"
                    accept=".txt,.pdf,.docx"
                    className="hidden"
                    onChange={handleChange}
                />

                {/* Upload Icon */}
                <div className={`text-5xl mb-4 transition-transform duration-300 ${isDragging ? 'scale-125 animate-bounce' : 'group-hover:scale-110'
                    }`}>
                    {isDragging ? '✨' : '📄'}
                </div>

                {/* Text */}
                <h3 className="text-lg font-display font-medium text-white/80 mb-1">
                    {isDragging ? 'Drop your script here!' : 'Drag & Drop your script'}
                </h3>
                <p className="text-sm text-white/40 mb-4">or click to browse files</p>

                {/* Format badges */}
                <div className="flex gap-2">
                    {ALLOWED.map(ext => (
                        <span key={ext} className="flex items-center gap-1 text-xs bg-white/5 text-white/40
                                       px-3 py-1 rounded-full border border-white/5">
                            {formatIcon(ext)} {ext.replace('.', '').toUpperCase()}
                        </span>
                    ))}
                </div>

                {/* Drag overlay */}
                {isDragging && (
                    <div className="absolute inset-0 rounded-2xl border-2 border-stage-gold bg-stage-gold/5
                          flex items-center justify-center pointer-events-none">
                        <span className="text-stage-gold font-display font-medium text-lg animate-pulse">
                            Release to upload
                        </span>
                    </div>
                )}
            </div>

            {/* Error */}
            {error && (
                <div className="mt-3 flex items-center gap-2 text-red-400 text-sm animate-fade-in">
                    <span>⚠️</span>
                    <span>{error}</span>
                </div>
            )}
        </div>
    )
}
