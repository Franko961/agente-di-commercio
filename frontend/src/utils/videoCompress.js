/**
 * Browser-side video compression using HTMLVideoElement + Canvas + MediaRecorder.
 * Reduces resolution to ~720p max width and re-encodes to WebM with reduced bitrate.
 * No external deps. Returns a new File or the original if compression isn't beneficial.
 */

const MAX_WIDTH = 1280;
const TARGET_BITRATE = 1_200_000; // 1.2 Mbps -> ~9 MB/min

export async function compressVideo(file, onProgress = () => {}) {
  if (!file.type.startsWith("video/")) return file;

  // Quick check: MediaRecorder support
  const hasRecorder = typeof MediaRecorder !== "undefined" &&
    (MediaRecorder.isTypeSupported("video/webm;codecs=vp9") ||
     MediaRecorder.isTypeSupported("video/webm;codecs=vp8"));
  if (!hasRecorder) return file;

  const video = document.createElement("video");
  video.muted = true;
  video.playsInline = true;
  video.crossOrigin = "anonymous";
  video.src = URL.createObjectURL(file);

  await new Promise((resolve, reject) => {
    video.onloadedmetadata = resolve;
    video.onerror = () => reject(new Error("video load error"));
  });

  const duration = video.duration;
  const srcW = video.videoWidth;
  const srcH = video.videoHeight;
  if (!srcW || !srcH) {
    URL.revokeObjectURL(video.src);
    return file;
  }

  // Skip compression if already small enough
  if (srcW <= MAX_WIDTH && file.size < 8 * 1024 * 1024) {
    URL.revokeObjectURL(video.src);
    return file;
  }

  const scale = Math.min(1, MAX_WIDTH / srcW);
  const w = Math.floor((srcW * scale) / 2) * 2;
  const h = Math.floor((srcH * scale) / 2) * 2;

  const canvas = document.createElement("canvas");
  canvas.width = w; canvas.height = h;
  const ctx = canvas.getContext("2d");

  const stream = canvas.captureStream(30);

  // Try to capture audio from the original video too
  let audioStream = null;
  try {
    if (video.captureStream) {
      const fullStream = video.captureStream();
      const audioTracks = fullStream.getAudioTracks();
      if (audioTracks.length) {
        audioStream = new MediaStream([audioTracks[0]]);
        stream.addTrack(audioTracks[0]);
      }
    }
  } catch (e) {
    // Some browsers don't allow this; proceed video-only
  }

  const mime = MediaRecorder.isTypeSupported("video/webm;codecs=vp9,opus")
    ? "video/webm;codecs=vp9,opus"
    : MediaRecorder.isTypeSupported("video/webm;codecs=vp8,opus")
      ? "video/webm;codecs=vp8,opus"
      : "video/webm";

  const recorder = new MediaRecorder(stream, {
    mimeType: mime,
    videoBitsPerSecond: TARGET_BITRATE,
    audioBitsPerSecond: 128_000,
  });

  const chunks = [];
  recorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };

  const recDone = new Promise((resolve) => { recorder.onstop = resolve; });

  recorder.start(250);

  await video.play();

  // Drive frames until the video ends
  await new Promise((resolve) => {
    const drawLoop = () => {
      if (video.paused || video.ended) return resolve();
      ctx.drawImage(video, 0, 0, w, h);
      onProgress(duration ? Math.min(99, Math.round((video.currentTime / duration) * 100)) : 0);
      requestAnimationFrame(drawLoop);
    };
    video.onended = () => resolve();
    drawLoop();
  });

  try { recorder.stop(); } catch (e) {}
  await recDone;

  URL.revokeObjectURL(video.src);

  const blob = new Blob(chunks, { type: "video/webm" });
  // If compression didn't help, keep the original
  if (blob.size >= file.size * 0.95) return file;

  const newName = file.name.replace(/\.[^.]+$/, "") + "-compresso.webm";
  return new File([blob], newName, { type: "video/webm", lastModified: Date.now() });
}

export function formatBytes(bytes) {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}
