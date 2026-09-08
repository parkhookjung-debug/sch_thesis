import { Routes, Route, Link, useLocation, Outlet } from 'react-router-dom';
import Hub from './pages/Hub.jsx';
import GamePage from './pages/GamePage.jsx';
import Landing from './pages/Landing.jsx';
import Upload from './pages/Upload.jsx';
import Recommendation from './pages/Recommendation.jsx';
import CoachSelect from './pages/CoachSelect.jsx';
import CoachingResult from './pages/CoachingResult.jsx';
import Realtime from './pages/Realtime.jsx';

function CoachLayout() {
  const { pathname } = useLocation();
  return (
    <div className="min-h-full flex flex-col">
      <header className="border-b border-white/5 backdrop-blur sticky top-0 z-30 bg-ink/80">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/" className="text-xs text-zinc-500 hover:text-zinc-200">←</Link>
            <Link to="/coach" className="font-display text-3xl tracking-wider text-zinc-100">
              BOXING<span className="text-accent">.</span>COACH
            </Link>
          </div>
          <nav className="flex gap-6 text-sm text-zinc-400">
            <Link to="/coach/coaches" className={pathname.startsWith('/coach/coaches') ? 'text-zinc-100' : 'hover:text-zinc-200'}>
              코치 둘러보기
            </Link>
            <Link to="/coach/upload" className={pathname === '/coach/upload' ? 'text-zinc-100' : 'hover:text-zinc-200'}>
              스타일 분석
            </Link>
          </nav>
        </div>
      </header>
      <main className="flex-1">
        <Outlet />
      </main>
      <footer className="border-t border-white/5 py-6 text-center text-xs text-zinc-500">
        © 복싱 코치 · RTMPose 기반 자세/펀치 분석
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Hub />} />
      <Route path="/game" element={<GamePage />} />
      <Route path="/coach" element={<CoachLayout />}>
        <Route index element={<Landing />} />
        <Route path="upload" element={<Upload />} />
        <Route path="recommendation/:jobId" element={<Recommendation />} />
        <Route path="coaches" element={<CoachSelect />} />
        <Route path="coaching/:coachId" element={<CoachingResult />} />
        <Route path="realtime/:coachId" element={<Realtime />} />
      </Route>
    </Routes>
  );
}
