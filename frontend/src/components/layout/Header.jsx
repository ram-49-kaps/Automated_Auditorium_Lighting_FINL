import { Link, useLocation } from 'react-router-dom'

export default function Header() {
    const location = useLocation()
    const isLanding = location.pathname === '/'

    return (
        <header className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${isLanding ? 'bg-transparent' : 'bg-stage-bg/80 backdrop-blur-md border-b border-white/5'
            }`}>
            <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
                <Link to="/" className="flex items-center gap-3 group">
                    <div className="relative w-10 h-10 bg-black/40 border border-[#00d4ff]/30 flex items-center justify-center
                          shadow-[0_0_15px_rgba(0,212,255,0.15)] transition-all duration-300 overflow-hidden group-hover:border-[#00d4ff]/60">
                        {/* Glow Effect */}
                        <div className="absolute inset-0 bg-gradient-to-br from-[#00d4ff]/10 to-blue-600/20 opacity-50 group-hover:opacity-100 transition-opacity" />

                        {/* The 'L' SVG */}
                        <svg viewBox="0 0 24 36" className="w-5 h-5 relative z-10" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ filter: 'drop-shadow(0 0 8px rgba(0, 212, 255, 0.5))' }}>
                            <path d="M 3 0 A 3 3 0 0 1 6 3 V 30 H 21 A 3 3 0 0 1 21 36 H 3 A 3 3 0 0 1 0 33 V 3 A 3 3 0 0 1 3 0 Z" fill="url(#l-header-grad)" />
                            <defs>
                                <linearGradient id="l-header-grad" x1="1" y1="0" x2="24" y2="36" gradientUnits="userSpaceOnUse">
                                    <stop offset="0%" stopColor="#ffffff" />
                                    <stop offset="55%" stopColor="#00d4ff" />
                                    <stop offset="100%" stopColor="#2563eb" />
                                </linearGradient>
                            </defs>
                        </svg>
                    </div>
                    <div>
                        <h1 className="text-sm font-mono font-bold tracking-widest text-[#00d4ff] uppercase">
                            LUMINA
                        </h1>
                        <p className="text-[9px] text-white/40 tracking-[0.3em] font-mono uppercase">INTELLIGENCE</p>
                    </div>
                </Link>

                {/* Nav */}
                {!isLanding && (
                    <nav className="flex items-center gap-1">
                        <NavPill to="/" label="Home" active={location.pathname === '/'} />
                        <NavPill
                            to="/upload"
                            label="Upload"
                            active={location.pathname === '/upload'}
                            disabled={location.pathname.startsWith('/processing') || location.pathname.startsWith('/results')}
                        />
                        <NavPill
                            to="/processing"
                            label="Processing"
                            active={location.pathname.startsWith('/processing')}
                            disabled={location.pathname === '/upload' || location.pathname.startsWith('/results')}
                        />
                        <NavPill
                            to="/results"
                            label="Results"
                            active={location.pathname.startsWith('/results')}
                            disabled={location.pathname === '/upload' || location.pathname.startsWith('/processing')}
                        />
                    </nav>
                )}
            </div>
        </header>
    )
}

function NavPill({ to, label, active, disabled }) {
    if (disabled) {
        return (
            <span
                className={`px-4 py-1.5 rounded-full text-xs font-medium transition-all duration-200 text-white/20 cursor-not-allowed`}
            >
                {label}
            </span>
        )
    }

    return (
        <Link
            to={to}
            className={`px-4 py-1.5 font-mono text-[10px] uppercase tracking-widest transition-all duration-200 border
        ${active
                    ? 'bg-[#00d4ff]/10 text-[#00d4ff] border-[#00d4ff]/30 shadow-[0_0_10px_rgba(0,212,255,0.1)]'
                    : 'text-white/40 border-transparent hover:text-white hover:bg-white/5'
                }`}
        >
            {label}
        </Link>
    )
}
