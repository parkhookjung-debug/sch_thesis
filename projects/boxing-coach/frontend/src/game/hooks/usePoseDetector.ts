import { useEffect, useRef, useState } from 'react';
import * as tf from '@tensorflow/tfjs';
import '@tensorflow/tfjs-backend-webgl';
import * as poseDetection from '@tensorflow-models/pose-detection';
import type { Keypoint } from '../pose/keypoints';

export type DetectorStatus = 'idle' | 'loading-camera' | 'loading-model' | 'ready' | 'error';

export type PoseFrame = {
  keypoints: Keypoint[];   // mirrored coordinates (matches what user sees on screen)
  width: number;           // video frame width
  height: number;          // video frame height
  timestamp: number;       // ms (performance.now)
};

type Options = {
  onFrame: (frame: PoseFrame | null) => void;
  // when true the loop pauses (e.g. menu screens). Pose detection still runs,
  // but the consumer can ignore the data.
};

// Loads MoveNet (single-pose lightning) and runs a continuous detection loop
// against the supplied <video> element. Mirrors x coordinates so the consumer
// can treat them as screen-space coordinates of a mirrored preview.
export function usePoseDetector(videoRef: React.RefObject<HTMLVideoElement | null>, opts: Options) {
  const [status, setStatus] = useState<DetectorStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  const detectorRef = useRef<poseDetection.PoseDetector | null>(null);
  const rafRef = useRef<number | null>(null);
  const onFrameRef = useRef(opts.onFrame);
  onFrameRef.current = opts.onFrame;

  useEffect(() => {
    let cancelled = false;
    let stream: MediaStream | null = null;

    async function init() {
      try {
        setStatus('loading-camera');
        stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
          audio: false,
        });
        if (cancelled) return;
        const v = videoRef.current;
        if (!v) throw new Error('video element missing');
        v.srcObject = stream;
        await v.play();

        setStatus('loading-model');
        await tf.setBackend('webgl');
        await tf.ready();
        detectorRef.current = await poseDetection.createDetector(
          poseDetection.SupportedModels.MoveNet,
          {
            modelType: poseDetection.movenet.modelType.SINGLEPOSE_LIGHTNING,
            enableSmoothing: true,
          }
        );
        if (cancelled) return;
        setStatus('ready');

        const loop = async () => {
          if (cancelled) return;
          const det = detectorRef.current;
          const video = videoRef.current;
          if (det && video && video.readyState >= 2) {
            try {
              const poses = await det.estimatePoses(video, { flipHorizontal: false });
              const w = video.videoWidth;
              const h = video.videoHeight;
              if (poses.length > 0) {
                // Mirror x so coordinates match the on-screen mirrored preview.
                const kps: Keypoint[] = poses[0].keypoints.map((k) => ({
                  x: w - k.x,
                  y: k.y,
                  score: k.score ?? 0,
                  name: k.name,
                }));
                onFrameRef.current({ keypoints: kps, width: w, height: h, timestamp: performance.now() });
              } else {
                onFrameRef.current(null);
              }
            } catch (e) {
              console.warn('pose estimate failed', e);
            }
          }
          rafRef.current = requestAnimationFrame(loop);
        };
        rafRef.current = requestAnimationFrame(loop);
      } catch (e) {
        console.error(e);
        setError(e instanceof Error ? e.message : String(e));
        setStatus('error');
      }
    }

    init();

    return () => {
      cancelled = true;
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      detectorRef.current?.dispose();
      detectorRef.current = null;
      stream?.getTracks().forEach((t) => t.stop());
    };
  }, [videoRef]);

  return { status, error };
}
