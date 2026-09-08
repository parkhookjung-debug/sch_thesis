import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

const COCO_CONN = [
  [5, 6], [5, 7], [7, 9], [6, 8], [8, 10],
  [5, 11], [6, 12], [11, 12],
  [11, 13], [13, 15], [12, 14], [14, 16],
  [0, 5], [0, 6],
];

const PUNCH_COLORS = {
  jab: '#ffdc00',
  cross: '#28a0ff',
  hook: '#ff32c8',
  uppercut: '#32ff64',
};

const TARGET_FPS = 20;             // 백엔드 DML 가속 시 20~30fps 처리 가능
const JPEG_QUALITY = 0.6;
const SEND_MAX_WIDTH = 640;
const KP_VIS_DRAW = 0.55;          // 화면에 그릴 keypoint 임계값 (이전 0.3보다 높임)

export default function Realtime() {
  const { coachId } = useParams();
  const nav = useNavigate();

  const videoRef = useRef(null);
  const previewRef = useRef(null);
  const overlayRef = useRef(null);
  const sendCanvasRef = useRef(null);

  const wsRef = useRef(null);
  const lastResultRef = useRef(null);
  const lastPunchRef = useRef({ type: null, t: 0 });
  const mirrorRef = useRef(true);    // 거울 모드 (셀카 기본 ON)

  const [status, setStatus] = useState('idle');
  const [coach, setCoach] = useState(null);
  const [availableViews, setAvailableViews] = useState(['side']);
  const [counts, setCounts] = useState({ jab: 0, cross: 0, hook: 0, uppercut: 0 });
  const [posture, setPosture] = useState(null);
  const [facingRight, setFacingRight] = useState(true);
  const [viewMode, setViewMode] = useState('ambiguous');
  const [viewLocked, setViewLocked] = useState(false);
  const [warnings, setWarnings] = useState([]);
  const [mirror, setMirror] = useState(true);
  const [error, setError] = useState(null);

  // 1) 카메라 권한 + 스트림
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 720 } },
          audio: false,
        });
        if (cancelled) { stream.getTracks().forEach((t) => t.stop()); return; }
        const video = videoRef.current;
        video.srcObject = stream;
        await video.play();
      } catch (e) {
        setError(`카메라 접근 실패: ${e.message}`);
      }
    })();
    return () => {
      cancelled = true;
      const stream = videoRef.current?.srcObject;
      if (stream) stream.getTracks().forEach((t) => t.stop());
    };
  }, []);

  // 2) WebSocket
  useEffect(() => {
    if (!coachId) return;
    setStatus('connecting');
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const url = `${proto}://${window.location.host}/api/ws/realtime/${coachId}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setStatus('connected');
    ws.onclose = () => setStatus('closed');
    ws.onerror = () => setStatus('failed');
    ws.onmessage = (ev) => {
      let m;
      try { m = JSON.parse(ev.data); } catch { return; }
      if (m.type === 'ready') {
        setCoach(m.coach);
        setAvailableViews(m.available_views || ['side']);
      } else if (m.type === 'error') {
        setError(m.message);
      } else if (m.type === 'frame_result') {
        lastResultRef.current = m;
        setCounts(m.counts);
        if (m.posture) setPosture(m.posture);
        else setPosture(null);
        setFacingRight(m.facing_right);
        setViewMode(m.view_mode);
        setViewLocked(m.view_locked);
        setWarnings(m.warnings || []);
        if (m.punch_events && m.punch_events.length > 0) {
          const last = m.punch_events[m.punch_events.length - 1];
          lastPunchRef.current = { type: last.type, t: performance.now() };
        }
      }
    };

    return () => { try { ws.close(); } catch {} };
  }, [coachId]);

  // mirror state → ref (전송 루프에서 참조)
  useEffect(() => { mirrorRef.current = mirror; }, [mirror]);

  // 3) 프레임 전송 — 거울 모드면 좌우 반전해서 보냄 (서버는 보이는 그대로 분석)
  useEffect(() => {
    let timer = null;
    let frameId = 0;
    const send = sendCanvasRef.current ?? document.createElement('canvas');
    sendCanvasRef.current = send;
    const sctx = send.getContext('2d');

    function tick() {
      const ws = wsRef.current;
      const video = videoRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN || !video || video.readyState < 2) {
        timer = setTimeout(tick, 100);
        return;
      }
      const vw = video.videoWidth, vh = video.videoHeight;
      if (!vw || !vh) { timer = setTimeout(tick, 100); return; }
      const scale = vw > SEND_MAX_WIDTH ? SEND_MAX_WIDTH / vw : 1;
      const dw = Math.round(vw * scale), dh = Math.round(vh * scale);
      if (send.width !== dw) send.width = dw;
      if (send.height !== dh) send.height = dh;
      sctx.save();
      if (mirrorRef.current) {
        sctx.translate(dw, 0); sctx.scale(-1, 1);
      }
      sctx.drawImage(video, 0, 0, dw, dh);
      sctx.restore();
      const dataURL = send.toDataURL('image/jpeg', JPEG_QUALITY);
      ws.send(JSON.stringify({ type: 'frame', frame_id: ++frameId, image: dataURL }));
      timer = setTimeout(tick, 1000 / TARGET_FPS);
    }
    timer = setTimeout(tick, 200);
    return () => { if (timer) clearTimeout(timer); };
  }, []);

  // 4) 오버레이 (preview + skeleton)
  //    preview / overlay canvas 의 intrinsic 사이즈를 백엔드가 받은 사이즈(=send canvas)와 동일하게 강제.
  //    덕분에 keypoint 좌표 보정(sx/sy)이 항상 1:1 이 되어 어긋날 일이 없다.
  useEffect(() => {
    let raf = 0;
    function draw() {
      const video = videoRef.current;
      const preview = previewRef.current;
      const overlay = overlayRef.current;
      if (!video || !preview || !overlay || !video.videoWidth) {
        raf = requestAnimationFrame(draw);
        return;
      }

      // 백엔드가 마지막으로 처리한 프레임 사이즈를 기준 — 없으면 video native 사이즈 사용
      const res = lastResultRef.current;
      const targetW = res?.width || video.videoWidth;
      const targetH = res?.height || video.videoHeight;
      if (preview.width !== targetW)  preview.width = targetW;
      if (preview.height !== targetH) preview.height = targetH;
      if (overlay.width !== targetW)  overlay.width = targetW;
      if (overlay.height !== targetH) overlay.height = targetH;

      // 영상 → preview (mirror 옵션 반영)
      const pctx = preview.getContext('2d');
      pctx.save();
      if (mirrorRef.current) {
        pctx.translate(preview.width, 0); pctx.scale(-1, 1);
      }
      pctx.drawImage(video, 0, 0, preview.width, preview.height);
      pctx.restore();

      // 오버레이
      const octx = overlay.getContext('2d');
      octx.clearRect(0, 0, overlay.width, overlay.height);
      if (res && res.kp && res.kp.length === 17) {
        octx.strokeStyle = 'rgba(180,180,180,0.85)';
        octx.lineWidth = 3;
        for (const [a, b] of COCO_CONN) {
          if (res.sc[a] > KP_VIS_DRAW && res.sc[b] > KP_VIS_DRAW) {
            octx.beginPath();
            octx.moveTo(res.kp[a][0], res.kp[a][1]);
            octx.lineTo(res.kp[b][0], res.kp[b][1]);
            octx.stroke();
          }
        }
        octx.fillStyle = '#ff3d57';
        for (let i = 0; i < 17; i++) {
          if (res.sc[i] > KP_VIS_DRAW) {
            octx.beginPath();
            octx.arc(res.kp[i][0], res.kp[i][1], 5, 0, Math.PI * 2);
            octx.fill();
          }
        }
      }
      // 펀치 플래시
      const { type, t } = lastPunchRef.current;
      if (type) {
        const age = (performance.now() - t) / 1000;
        if (age < 0.7) {
          const alpha = Math.max(0, 1 - age / 0.7);
          octx.globalAlpha = alpha;
          octx.fillStyle = PUNCH_COLORS[type] || '#fff';
          octx.font = 'bold 72px "Bebas Neue", Inter, sans-serif';
          octx.fillText(type.toUpperCase(), overlay.width / 2 - 130, overlay.height * 0.12);
          octx.globalAlpha = 1;
        }
      }
      raf = requestAnimationFrame(draw);
    }
    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, []);

  function sendControl(type, extra = {}) {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ type, ...extra }));
    if (type === 'reset') setCounts({ jab: 0, cross: 0, hook: 0, uppercut: 0 });
  }

  const viewLabel = {
    front: '정면',
    side:  '측면',
    ambiguous: '판정중…',
  }[viewMode] || viewMode;

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      <button onClick={() => nav('/coach/coaches')} className="text-xs text-zinc-500 hover:text-zinc-300">← 코치 변경</button>
      <div className="mt-3 flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="font-display text-5xl tracking-wider">{coach?.name || '실시간 코칭'}</h1>
          <p className="text-accent text-sm mt-1">{coach?.style}</p>
        </div>
        <div className="flex gap-2 items-center">
          <span className={`text-[10px] px-3 py-1.5 rounded-full ${
            viewMode === 'side' ? 'bg-emerald-500/20 text-emerald-300'
              : viewMode === 'front' ? 'bg-sky-500/20 text-sky-300'
              : 'bg-zinc-500/20 text-zinc-300'
          }`}>
            VIEW {viewLabel.toUpperCase()} {viewLocked && '🔒'}
          </span>
          <span className={`text-[10px] px-3 py-1.5 rounded-full ${
            status === 'connected' ? 'bg-emerald-500/20 text-emerald-300'
              : status === 'connecting' ? 'bg-amber-500/20 text-amber-200'
              : 'bg-red-500/20 text-red-300'
          }`}>WS {status.toUpperCase()}</span>
        </div>
      </div>

      {error && (
        <pre className="mt-4 p-3 bg-red-900/20 border border-red-900/40 rounded-lg text-xs text-red-200 whitespace-pre-wrap">{error}</pre>
      )}
      {warnings.length > 0 && (
        <div className="mt-4 p-3 bg-amber-900/20 border border-amber-900/40 rounded-lg text-xs text-amber-200 space-y-1">
          {warnings.map((w, i) => <div key={i}>· {w}</div>)}
        </div>
      )}

      <div className="grid lg:grid-cols-3 gap-6 mt-8">
        <div className="lg:col-span-2 relative rounded-2xl overflow-hidden border border-white/5 bg-black">
          <video ref={videoRef} className="hidden" muted playsInline />
          <canvas ref={previewRef} className="w-full block" />
          <canvas ref={overlayRef} className="absolute inset-0 w-full h-full pointer-events-none" />
        </div>

        <div className="space-y-4">
          <div className="rounded-2xl bg-canvas border border-white/5 p-5">
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs text-zinc-500 uppercase tracking-wider">카메라 모드</p>
              <span className="text-[10px] text-zinc-500">사용 가능: {availableViews.join('/')}</span>
            </div>
            <div className="grid grid-cols-3 gap-1 text-xs">
              <button
                onClick={() => sendControl('set_view', { mode: 'auto' })}
                className={`px-2 py-1.5 rounded ${!viewLocked ? 'bg-accent text-white' : 'bg-white/5 text-zinc-300'}`}>
                자동
              </button>
              <button
                disabled={!availableViews.includes('side')}
                onClick={() => sendControl('set_view', { mode: 'side' })}
                className={`px-2 py-1.5 rounded ${viewLocked && viewMode === 'side' ? 'bg-accent text-white' : 'bg-white/5 text-zinc-300'} disabled:opacity-30`}>
                측면
              </button>
              <button
                disabled={!availableViews.includes('front')}
                onClick={() => sendControl('set_view', { mode: 'front' })}
                className={`px-2 py-1.5 rounded ${viewLocked && viewMode === 'front' ? 'bg-accent text-white' : 'bg-white/5 text-zinc-300'} disabled:opacity-30`}>
                정면
              </button>
            </div>
            <label className="mt-3 flex items-center gap-2 text-xs text-zinc-400 cursor-pointer">
              <input type="checkbox" checked={mirror} onChange={(e) => setMirror(e.target.checked)} className="accent-accent" />
              거울 모드 (셀카처럼 좌우 반전)
            </label>
          </div>

          <div className="rounded-2xl bg-canvas border border-white/5 p-5">
            <p className="text-xs text-zinc-500 uppercase tracking-wider mb-3">펀치 카운트</p>
            <div className="grid grid-cols-2 gap-2 text-sm">
              {Object.entries(counts).map(([k, v]) => (
                <div key={k} className="flex justify-between bg-white/5 rounded-lg px-3 py-2">
                  <span className="text-zinc-400 uppercase">{k}</span>
                  <span className="font-medium" style={{ color: PUNCH_COLORS[k] }}>{v}</span>
                </div>
              ))}
            </div>
            <p className="mt-3 text-xs text-zinc-500">
              총 {Object.values(counts).reduce((a, b) => a + b, 0)} 회 ·&nbsp;
              {facingRight ? '우향(오르토독스)' : '좌향(사우스포)'}
            </p>
          </div>

          {posture && (
            <div className="rounded-2xl bg-canvas border border-white/5 p-5">
              <div className="flex items-baseline justify-between">
                <p className="text-xs text-zinc-500 uppercase tracking-wider">자세 점수</p>
                <p className="font-display text-2xl">
                  <span className="text-accent">{posture.total}</span><span className="text-zinc-500 text-base">/100</span>
                  <span className="ml-2 text-zinc-300">[{posture.grade}]</span>
                </p>
              </div>
              <div className="mt-3 space-y-2">
                {posture.items.map((it) => (
                  <div key={it.label}>
                    <div className="flex justify-between text-xs text-zinc-400">
                      <span>{it.label}</span><span>{it.score}/{it.max}</span>
                    </div>
                    <div className="bar mt-1">
                      <div className="bar-fill" style={{ width: `${(it.score / it.max) * 100}%` }} />
                    </div>
                    <p className="mt-1 text-[11px] text-zinc-500">{it.message}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex gap-2">
            <button onClick={() => sendControl('reset')} className="btn-secondary flex-1 text-sm">카운터 초기화</button>
            <button onClick={() => sendControl('toggle_facing')} className="btn-secondary flex-1 text-sm">방향 전환</button>
          </div>
        </div>
      </div>

      <p className="mt-6 text-xs text-zinc-500">
        팁: 측면 촬영이면 lean_forward·스탠스까지 평가되어 가장 정확합니다. 정면이면 가드·균형·머리 중심으로 평가합니다.
        모드는 처음 1~2초간 자동 감지됩니다.
      </p>
    </div>
  );
}
