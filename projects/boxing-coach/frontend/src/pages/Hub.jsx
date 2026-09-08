import { Link } from 'react-router-dom';

export default function Hub() {
  return (
    <div className="min-h-screen flex flex-col">
      <div className="max-w-6xl mx-auto px-6 py-20 flex-1 flex flex-col justify-center">
        <p className="text-accent font-medium tracking-wider uppercase mb-4 text-center">BOXING · AI</p>
        <h1 className="font-display text-7xl md:text-8xl tracking-wider text-center leading-none">
          무엇을 <span className="text-accent">시작</span>할까요?
        </h1>
        <p className="text-zinc-400 text-center mt-6 max-w-xl mx-auto">
          내 자세를 분석받는 코칭 모드와, 보스를 막아내며 점수를 쌓는 게임 모드 중에서 고르세요.
        </p>

        <div className="grid md:grid-cols-2 gap-6 mt-16">
          <Link to="/coach" className="group rounded-3xl bg-canvas border border-white/5 p-10 hover:border-accent/60 hover:-translate-y-1 transition">
            <div className="flex items-start justify-between">
              <span className="font-display text-accent text-5xl">01</span>
              <span className="text-[10px] tracking-widest uppercase text-zinc-500">RTMPose · Backend</span>
            </div>
            <h2 className="font-display text-4xl tracking-wider mt-8">복싱 코치</h2>
            <p className="text-zinc-400 mt-3">
              Bivol · Canelo · Ryan Garcia · 임관우 — 네 명 중 한 명을 골라 실시간으로
              자세 점수와 펀치를 코칭받습니다.
            </p>
            <ul className="mt-6 space-y-1.5 text-sm text-zinc-500">
              <li>· 자세 DNA (측면/정면) 기준 점수</li>
              <li>· 펀치 자동 감지 + 카운트</li>
              <li>· 스타일 분석으로 닮은 코치 추천</li>
            </ul>
            <p className="mt-8 text-accent text-sm group-hover:underline">코칭 시작 →</p>
          </Link>

          <Link to="/game" className="group rounded-3xl bg-canvas border border-white/5 p-10 hover:border-accent/60 hover:-translate-y-1 transition">
            <div className="flex items-start justify-between">
              <span className="font-display text-accent text-5xl">02</span>
              <span className="text-[10px] tracking-widest uppercase text-zinc-500">TF.js · 브라우저</span>
            </div>
            <h2 className="font-display text-4xl tracking-wider mt-8">복싱 디펜스 게임</h2>
            <p className="text-zinc-400 mt-3">
              날아오는 펀치를 가드·슬립·위빙으로 막아내고, 보스를 쓰러뜨리세요. 카메라 앞에서
              실제 동작으로 플레이합니다.
            </p>
            <ul className="mt-6 space-y-1.5 text-sm text-zinc-500">
              <li>· 페이크/콤보 보스 패턴</li>
              <li>· 카운터·콤보 보너스</li>
              <li>· 난이도 3단계</li>
            </ul>
            <p className="mt-8 text-accent text-sm group-hover:underline">게임 시작 →</p>
          </Link>
        </div>
      </div>
      <footer className="border-t border-white/5 py-6 text-center text-xs text-zinc-500">
        © Boxing · Coach + Game 통합 빌드
      </footer>
    </div>
  );
}
