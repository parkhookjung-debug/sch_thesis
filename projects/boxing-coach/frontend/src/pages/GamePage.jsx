import { Link } from 'react-router-dom';
import { Game } from '../game/components/Game';
import '../game/App.css';

export default function GamePage() {
  return (
    <div className="min-h-screen bg-ink">
      <div className="max-w-7xl mx-auto px-4 py-3">
        <Link to="/" className="text-xs text-zinc-500 hover:text-zinc-200">← 메뉴로</Link>
      </div>
      <Game />
    </div>
  );
}
