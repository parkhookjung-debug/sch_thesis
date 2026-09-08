import { Link } from 'react-router-dom';

export default function Landing() {
  return (
    <div className="max-w-6xl mx-auto px-6 py-20">
      <section className="grid md:grid-cols-2 gap-12 items-center">
        <div>
          <p className="text-accent font-medium tracking-wide uppercase mb-3">AI Boxing Coach</p>
          <h1 className="font-display text-6xl md:text-7xl leading-none tracking-wide">
            카메라만 켜면<br/>
            <span className="text-accent">실시간</span> 으로 코칭합니다.
          </h1>
          <p className="mt-6 text-zinc-300 text-lg leading-relaxed">
            Bivol · Canelo · Ryan Garcia · 임관우 — 네 명의 스타일 중<br/>
            하나를 골라 웹캠 앞에서 바로 펀치를 던지세요.<br/>
            펀치 카운트와 자세 점수가 실시간으로 표시됩니다.
          </p>
          <div className="mt-10 flex flex-wrap gap-3">
            <Link to="/coach/coaches" className="btn-primary">실시간 코칭 시작</Link>
            <Link to="/coach/upload" className="btn-secondary">영상으로 스타일 분석 (선택)</Link>
          </div>
          <p className="mt-6 text-xs text-zinc-500">
            카메라 권한 필요 · RTMPose(COCO 17) 백엔드 추론 · ~10fps WebSocket
          </p>
        </div>

        <div className="rounded-3xl bg-canvas border border-white/5 p-8">
          <h3 className="font-display text-2xl tracking-wider mb-6">실시간 분석 흐름</h3>
          <ol className="space-y-4 text-sm text-zinc-300">
            {[
              ['01', '4명 중 코치를 한 명 선택합니다'],
              ['02', '브라우저에서 카메라 권한을 허용합니다'],
              ['03', '프레임이 백엔드로 스트리밍됩니다 (~10fps)'],
              ['04', 'RTMPose 가 17개 키포인트를 매 프레임 추출합니다'],
              ['05', '선택한 코치의 DNA 기준으로 자세 점수 · 펀치를 실시간 표시합니다'],
            ].map(([num, txt]) => (
              <li key={num} className="flex gap-4 items-start">
                <span className="font-display text-accent text-xl">{num}</span>
                <span>{txt}</span>
              </li>
            ))}
          </ol>
          <div className="mt-6 pt-5 border-t border-white/5 text-xs text-zinc-500 leading-relaxed">
            본인 영상이 있다면 <Link to="/coach/upload" className="text-accent hover:underline">먼저 스타일 분석</Link> 으로
            가장 닮은 코치를 자동 추천받을 수도 있습니다 (선택).
          </div>
        </div>
      </section>
    </div>
  );
}
