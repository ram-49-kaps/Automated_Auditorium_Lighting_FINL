import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import UploadPage from './pages/UploadPage'
import ProcessingPage from './pages/ProcessingPage'
import ResultsPage from './pages/ResultsPage'

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/processing" element={<ProcessingPage />} />
        <Route path="/processing/:jobId" element={<ProcessingPage />} />
        <Route path="/results" element={<ResultsPage />} />
        <Route path="/results/:jobId" element={<ResultsPage />} />
      </Routes>
    </Router>
  )
}

export default App
