/**
 * Client-side video compression for the upload flow.
 *
 * Phone videos are frequently 50–200 MB at full sensor resolution; re-encoding
 * them down to 720p H.264 before upload shrinks the transfer by an order of
 * magnitude and gets large uploads off flaky mobile connections faster. All of
 * this runs in the browser so the backend never has to touch the original.
 *
 * Two pipelines, tried in order:
 *   1. WebCodecs — demux the source MP4 with mp4box, decode with `VideoDecoder`,
 *      scale each frame onto an `OffscreenCanvas`, re-encode with `VideoEncoder`,
 *      and mux the result with mp4-muxer. Fast, hardware-accelerated, exact.
 *   2. MediaRecorder — play the file in a hidden `<video>`, paint frames onto a
 *      canvas at the target height, capture the canvas stream and record it.
 *      Slower and only as good as the platform recorder, but widely supported.
 *
 * CRITICAL CONTRACT: `compressVideo` must NEVER throw and must never make the
 * file bigger. On any error, an unsupported browser, or a result that isn't at
 * least ~10% smaller than the input, it returns the ORIGINAL file untouched.
 *
 * AUDIO: dropped for v1. The decode→scale→encode path only carries the video
 * track; threading an `AudioEncoder`/AAC pass-through through mp4-muxer is a
 * follow-up. Lifting/bowling/golf clips are analyzed visually, so silent output
 * is acceptable for now. (The MediaRecorder fallback would carry audio, but we
 * deliberately mute it there too for parity.)
 */

export interface CompressOptions {
  /** Target output height in pixels; width is derived to preserve aspect. Default 720. */
  maxHeight?: number;
  /** Target video bitrate in bits/sec passed to the encoder. Default 2_500_000. */
  videoBitrate?: number;
}

const DEFAULT_MAX_HEIGHT = 720;
const DEFAULT_VIDEO_BITRATE = 2_500_000;

/** Require this much shrinkage or we keep the original — re-encoding tiny files isn't worth it. */
const MIN_SHRINK_RATIO = 0.9;

/**
 * H.264 codec strings to probe with `VideoEncoder.isConfigSupported`, cheapest
 * profile first. `avc1.42E01F` is Constrained Baseline @ L3.1 (the most broadly
 * playable); the others step up to Main and High for hardware that prefers them.
 */
const H264_CODEC_CANDIDATES = ["avc1.42E01F", "avc1.4D401F", "avc1.640020"] as const;

/**
 * Conservative capability probe. True only when every primitive the WebCodecs
 * pipeline needs is present. Callers should still treat `compressVideo` as the
 * source of truth — it falls back to the original even when this returns true.
 */
export function canCompressVideo(): boolean {
  return (
    typeof VideoEncoder !== "undefined" &&
    typeof VideoDecoder !== "undefined" &&
    typeof OffscreenCanvas !== "undefined"
  );
}

/**
 * Compress `file` to ~720p H.264 MP4. Returns a NEW `File` (basename + ".mp4",
 * type "video/mp4") on success, or the original `file` unchanged on any failure
 * or insufficient size win. Never throws. `onProgress` reports 0..100.
 */
export async function compressVideo(
  file: File,
  opts?: CompressOptions,
  onProgress?: (pct: number) => void
): Promise<File> {
  const maxHeight = opts?.maxHeight ?? DEFAULT_MAX_HEIGHT;
  const videoBitrate = opts?.videoBitrate ?? DEFAULT_VIDEO_BITRATE;

  const report = (pct: number): void => {
    if (onProgress) {
      // Clamp defensively — a flaky decoder can over- or under-shoot.
      onProgress(Math.max(0, Math.min(100, Math.round(pct))));
    }
  };

  report(0);

  // Primary path: WebCodecs + mp4box demux + mp4-muxer mux.
  if (canCompressVideo()) {
    try {
      const compressed = await compressWithWebCodecs(file, maxHeight, videoBitrate, report);
      if (compressed && isWorthwhile(compressed, file)) {
        report(100);
        return compressed;
      }
    } catch {
      // Swallow — fall through to the MediaRecorder path.
    }
  }

  // Fallback path: HTMLVideoElement playback → canvas → MediaRecorder.
  try {
    const recorded = await compressWithMediaRecorder(file, maxHeight, videoBitrate, report);
    if (recorded && isWorthwhile(recorded, file)) {
      report(100);
      return recorded;
    }
  } catch {
    // Swallow — fall through to returning the original.
  }

  // Final fallback: the untouched original.
  report(100);
  return file;
}

/** True when `out` is at least MIN_SHRINK_RATIO smaller than `original`. */
function isWorthwhile(out: File, original: File): boolean {
  return out.size > 0 && out.size <= original.size * MIN_SHRINK_RATIO;
}

/** Strip a file extension so we can append ".mp4". */
function baseName(name: string): string {
  const dot = name.lastIndexOf(".");
  return dot > 0 ? name.slice(0, dot) : name;
}

/** Round to the nearest even integer ≥ 2 — H.264 requires even dimensions. */
function evenDimension(value: number): number {
  const rounded = Math.round(value);
  const even = rounded - (rounded % 2);
  return Math.max(2, even);
}

/**
 * Compute the scaled, even output dimensions for a source frame, clamped so the
 * height never exceeds `maxHeight` (and never upscales a smaller source).
 */
function targetDimensions(
  srcWidth: number,
  srcHeight: number,
  maxHeight: number
): { width: number; height: number } {
  const outHeight = Math.min(maxHeight, srcHeight);
  const scale = outHeight / srcHeight;
  return {
    width: evenDimension(srcWidth * scale),
    height: evenDimension(outHeight),
  };
}

// ---------------------------------------------------------------------------
// mp4box runtime typing
//
// The published `mp4box` types (v2.x) are heavily alias-minified and not usable
// against the documented runtime surface, so we declare the narrow slice we use
// ourselves. These mirror the long-stable mp4box.js JS API.
// ---------------------------------------------------------------------------

interface Mp4BoxBufferCtor {
  /** ArrayBuffer subclass tagged with a `fileStart` offset for `appendBuffer`. */
  fromArrayBuffer(buffer: ArrayBuffer, fileStart: number): ArrayBuffer & { fileStart: number };
}

interface Mp4VideoTrackInfo {
  id: number;
  /** Codec string, e.g. "avc1.42E01E". */
  codec: string;
  video?: { width: number; height: number };
  track_width?: number;
  track_height?: number;
  nb_samples: number;
  timescale: number;
}

interface Mp4FileInfo {
  videoTracks: Mp4VideoTrackInfo[];
}

interface Mp4Sample {
  /** Raw encoded sample bytes (one frame). */
  data: Uint8Array;
  /** Composition (presentation) timestamp in track timescale units. */
  cts: number;
  /** Decode timestamp in track timescale units. */
  dts: number;
  /** Sample duration in track timescale units. */
  duration: number;
  /** Track timescale (units per second). */
  timescale: number;
  /** Keyframe flag. */
  is_sync: boolean;
}

/** A `DataStream`-like writer, used to serialize the avcC box for the decoder description. */
interface Mp4DataStream {
  buffer: ArrayBuffer;
}

interface Mp4StsdEntry {
  /** Present on avc1/avc2/avc3 entries; serializes the AVC decoder config. */
  avcC?: { write(stream: Mp4DataStream): void };
  /** Present on hvc1/hev1 entries (HEVC). */
  hvcC?: { write(stream: Mp4DataStream): void };
}

interface Mp4Trak {
  mdia: { minf: { stbl: { stsd: { entries: Mp4StsdEntry[] } } } };
}

interface Mp4File {
  onReady: ((info: Mp4FileInfo) => void) | null;
  onError: ((module: string, msg: string) => void) | null;
  onSamples: ((trackId: number, user: unknown, samples: Mp4Sample[]) => void) | null;
  appendBuffer(buffer: ArrayBuffer & { fileStart: number }): number;
  start(): void;
  stop(): void;
  flush(): void;
  setExtractionOptions(trackId: number, user: unknown, options: { nbSamples: number }): void;
  getTrackById(id: number): Mp4Trak | undefined;
}

/** mp4box's DataStream constructor flag for big-endian writes (avcC is big-endian). */
const MP4BOX_BIG_ENDIAN = 1;

interface Mp4BoxModule {
  createFile(): Mp4File;
  MP4BoxBuffer: Mp4BoxBufferCtor;
  DataStream: new (
    buffer?: ArrayBuffer,
    byteOffset?: number,
    endianness?: number
  ) => Mp4DataStream;
}

/**
 * Extract the codec-private decoder configuration (avcC / hvcC box bytes) the
 * `VideoDecoder` needs in its `description`. mp4box gives us the parsed box; we
 * re-serialize it and strip the 8-byte box header (size + fourcc) to get the raw
 * config record.
 */
function extractDecoderDescription(
  mp4box: Mp4BoxModule,
  trak: Mp4Trak
): Uint8Array | undefined {
  const entry = trak.mdia.minf.stbl.stsd.entries[0];
  const configBox = entry?.avcC ?? entry?.hvcC;
  if (!configBox) {
    return undefined;
  }
  const stream = new mp4box.DataStream(undefined, 0, MP4BOX_BIG_ENDIAN);
  configBox.write(stream);
  // Box layout: [4 bytes size][4 bytes fourcc][config record...]. Skip the header.
  return new Uint8Array(stream.buffer, 8);
}

/**
 * Demux `file` into an ordered list of encoded video samples plus the track's
 * codec string and decoder description, using mp4box.
 */
async function demuxVideo(
  file: File
): Promise<{
  samples: Mp4Sample[];
  codec: string;
  description: Uint8Array | undefined;
  width: number;
  height: number;
}> {
  const mp4box = (await import("mp4box")) as unknown as Mp4BoxModule;
  const mp4file = mp4box.createFile();

  const samples: Mp4Sample[] = [];

  const result = await new Promise<{
    track: Mp4VideoTrackInfo;
    description: Uint8Array | undefined;
  }>((resolve, reject) => {
    let expected = 0;
    let videoTrack: Mp4VideoTrackInfo | undefined;
    let description: Uint8Array | undefined;

    mp4file.onError = (_module, msg): void => {
      reject(new Error(`mp4box demux error: ${msg}`));
    };

    mp4file.onReady = (info): void => {
      videoTrack = info.videoTracks[0];
      if (!videoTrack) {
        reject(new Error("no video track found"));
        return;
      }
      expected = videoTrack.nb_samples;
      const trak = mp4file.getTrackById(videoTrack.id);
      if (trak) {
        description = extractDecoderDescription(mp4box, trak);
      }
      mp4file.setExtractionOptions(videoTrack.id, null, { nbSamples: expected || 1_000_000 });
      mp4file.start();
    };

    mp4file.onSamples = (_trackId, _user, batch): void => {
      for (const s of batch) {
        samples.push(s);
      }
      if (videoTrack && expected > 0 && samples.length >= expected) {
        resolve({ track: videoTrack, description });
      }
    };

    // Feed the whole file in one shot, then flush to force sample emission.
    void file
      .arrayBuffer()
      .then((buf) => {
        const mp4Buffer = mp4box.MP4BoxBuffer.fromArrayBuffer(buf, 0);
        mp4file.appendBuffer(mp4Buffer);
        mp4file.flush();
        // If the file had no readable video samples, onSamples never resolves;
        // resolve here when nothing was queued so the caller can fall back.
        if (samples.length === 0) {
          reject(new Error("no video samples extracted"));
        } else if (!videoTrack) {
          reject(new Error("no video track found"));
        } else {
          // All samples already arrived synchronously via flush().
          const trak = mp4file.getTrackById(videoTrack.id);
          resolve({
            track: videoTrack,
            description: description ?? (trak ? extractDecoderDescription(mp4box, trak) : undefined),
          });
        }
      })
      .catch(reject);
  });

  const track = result.track;
  const width = track.video?.width ?? track.track_width ?? 0;
  const height = track.video?.height ?? track.track_height ?? 0;
  if (!width || !height || samples.length === 0) {
    throw new Error("incomplete demux result");
  }

  return { samples, codec: track.codec, description: result.description, width, height };
}

/** Find the first H.264 codec string the encoder will accept at the given size/bitrate. */
async function pickSupportedH264Codec(
  width: number,
  height: number,
  bitrate: number,
  framerate: number
): Promise<string | undefined> {
  for (const codec of H264_CODEC_CANDIDATES) {
    try {
      const support = await VideoEncoder.isConfigSupported({
        codec,
        width,
        height,
        bitrate,
        framerate,
      });
      if (support.supported) {
        return codec;
      }
    } catch {
      // Try the next candidate.
    }
  }
  return undefined;
}

/**
 * WebCodecs pipeline: demux → decode → scale-on-canvas → encode → mux.
 * Returns the compressed File, or throws so the caller can fall back.
 */
async function compressWithWebCodecs(
  file: File,
  maxHeight: number,
  videoBitrate: number,
  report: (pct: number) => void
): Promise<File> {
  const {
    samples,
    codec: sourceCodec,
    description,
    width: srcWidth,
    height: srcHeight,
  } = await demuxVideo(file);
  report(10);

  const { width: outWidth, height: outHeight } = targetDimensions(srcWidth, srcHeight, maxHeight);

  // Derive a framerate from the source so mp4-muxer rounds timestamps sanely.
  const totalDurationUnits = samples.reduce((sum, s) => sum + s.duration, 0);
  const timescale = samples[0]?.timescale || 30_000;
  const durationSeconds = totalDurationUnits / timescale;
  const framerate =
    durationSeconds > 0 ? Math.max(1, Math.round(samples.length / durationSeconds)) : 30;

  const codec = await pickSupportedH264Codec(outWidth, outHeight, videoBitrate, framerate);
  if (!codec) {
    throw new Error("no supported H.264 encoder config");
  }

  // mp4-muxer is dynamically imported so it (and mp4box) stay out of the main bundle.
  const { Muxer, ArrayBufferTarget } = await import("mp4-muxer");
  const muxer = new Muxer({
    target: new ArrayBufferTarget(),
    video: { codec: "avc", width: outWidth, height: outHeight, frameRate: framerate },
    fastStart: "in-memory",
    firstTimestampBehavior: "offset",
  });

  const canvas = new OffscreenCanvas(outWidth, outHeight);
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    throw new Error("OffscreenCanvas 2D context unavailable");
  }

  let encodeError: unknown = null;
  const encoder = new VideoEncoder({
    output: (chunk, meta) => {
      muxer.addVideoChunk(chunk, meta);
    },
    error: (err) => {
      encodeError = err;
    },
  });
  encoder.configure({
    codec,
    width: outWidth,
    height: outHeight,
    bitrate: videoBitrate,
    framerate,
  });

  // Decoder emits VideoFrames; we scale each onto the canvas and re-encode it,
  // then immediately close it (VideoFrames hold scarce GPU/decoder buffers).
  let decoded = 0;
  const total = samples.length;
  let decodeError: unknown = null;

  const decoder = new VideoDecoder({
    output: (frame) => {
      try {
        ctx.drawImage(frame, 0, 0, outWidth, outHeight);
        const keyFrame = decoded % framerate === 0; // force periodic keyframes
        const encFrame = new VideoFrame(canvas, {
          timestamp: frame.timestamp,
          duration: frame.duration ?? undefined,
        });
        encoder.encode(encFrame, { keyFrame });
        encFrame.close();
      } catch (err) {
        decodeError = err;
      } finally {
        frame.close();
        decoded += 1;
        // Decode is the dominant cost; map it across 10→90% of the bar.
        report(10 + Math.round((decoded / total) * 80));
      }
    },
    error: (err) => {
      decodeError = err;
    },
  });

  decoder.configure({
    // mp4box reports the source codec string (e.g. "avc1.42E01E" / "hev1...");
    // the decoder needs it verbatim alongside the avcC/hvcC description bytes.
    codec: sourceCodec,
    description,
  });

  // Feed encoded samples in decode order. timestamp/duration in microseconds.
  for (const s of samples) {
    if (decodeError || encodeError) {
      break;
    }
    const tsMicros = Math.round((s.cts / s.timescale) * 1_000_000);
    const durMicros = Math.round((s.duration / s.timescale) * 1_000_000);
    const chunk = new EncodedVideoChunk({
      type: s.is_sync ? "key" : "delta",
      timestamp: tsMicros,
      duration: durMicros,
      data: s.data,
    });
    decoder.decode(chunk);
  }

  await decoder.flush();
  await encoder.flush();
  decoder.close();
  encoder.close();

  if (decodeError) {
    throw decodeError instanceof Error ? decodeError : new Error(String(decodeError));
  }
  if (encodeError) {
    throw encodeError instanceof Error ? encodeError : new Error(String(encodeError));
  }

  muxer.finalize();
  const target = muxer.target as ArrayBufferTarget;
  report(95);

  const blob = new Blob([target.buffer], { type: "video/mp4" });
  return new File([blob], `${baseName(file.name)}.mp4`, { type: "video/mp4" });
}

/**
 * MediaRecorder fallback: play the file in a hidden <video>, paint each frame to
 * a canvas downscaled to `maxHeight`, capture the canvas stream and record it.
 * Audio is intentionally not captured (parity with the WebCodecs path).
 */
async function compressWithMediaRecorder(
  file: File,
  maxHeight: number,
  videoBitrate: number,
  report: (pct: number) => void
): Promise<File> {
  if (typeof MediaRecorder === "undefined" || typeof document === "undefined") {
    throw new Error("MediaRecorder unavailable");
  }

  const mimeType = pickRecorderMimeType();
  if (!mimeType) {
    throw new Error("no supported MediaRecorder mimeType");
  }

  const url = URL.createObjectURL(file);
  const video = document.createElement("video");
  video.muted = true;
  video.playsInline = true;
  video.preload = "auto";
  video.src = url;

  try {
    await new Promise<void>((resolve, reject) => {
      video.onloadedmetadata = (): void => resolve();
      video.onerror = (): void => reject(new Error("video metadata load failed"));
    });

    const srcWidth = video.videoWidth;
    const srcHeight = video.videoHeight;
    if (!srcWidth || !srcHeight) {
      throw new Error("video has no dimensions");
    }

    const { width: outWidth, height: outHeight } = targetDimensions(srcWidth, srcHeight, maxHeight);
    const duration = Number.isFinite(video.duration) ? video.duration : 0;

    const canvas = document.createElement("canvas");
    canvas.width = outWidth;
    canvas.height = outHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      throw new Error("canvas 2D context unavailable");
    }

    // captureStream at 30fps; MediaRecorder pulls frames we paint each rAF.
    const stream = canvas.captureStream(30);
    const recorder = new MediaRecorder(stream, {
      mimeType,
      videoBitsPerSecond: videoBitrate,
    });

    const chunks: BlobPart[] = [];
    recorder.ondataavailable = (e: BlobEvent): void => {
      if (e.data.size > 0) {
        chunks.push(e.data);
      }
    };

    const recordingDone = new Promise<void>((resolve, reject) => {
      recorder.onstop = (): void => resolve();
      recorder.onerror = (): void => reject(new Error("MediaRecorder error"));
    });

    recorder.start();

    // Paint frames until the source finishes playing, reporting progress against
    // duration as we go.
    let rafId = 0;
    const paint = (): void => {
      ctx.drawImage(video, 0, 0, outWidth, outHeight);
      if (duration > 0) {
        report(Math.min(95, (video.currentTime / duration) * 95));
      }
      rafId = requestAnimationFrame(paint);
    };

    await video.play();
    paint();

    await new Promise<void>((resolve, reject) => {
      video.onended = (): void => resolve();
      video.onerror = (): void => reject(new Error("video playback error"));
    });

    cancelAnimationFrame(rafId);
    recorder.stop();
    await recordingDone;

    const outType = mimeType.startsWith("video/mp4") ? "video/mp4" : "video/webm";
    const blob = new Blob(chunks, { type: outType });
    // We always name it .mp4 per contract; the bytes may be webm on browsers
    // that only support that container, but the upload flow keys off extension
    // and the backend sniffs content — keep the contract simple here.
    return new File([blob], `${baseName(file.name)}.mp4`, { type: outType });
  } finally {
    URL.revokeObjectURL(url);
    video.removeAttribute("src");
    video.load();
  }
}

/** Prefer an MP4 recorder container, then WebM; undefined if neither works. */
function pickRecorderMimeType(): string | undefined {
  const candidates = [
    "video/mp4;codecs=avc1.42E01F",
    "video/mp4",
    "video/webm;codecs=vp9",
    "video/webm;codecs=vp8",
    "video/webm",
  ];
  for (const type of candidates) {
    if (MediaRecorder.isTypeSupported(type)) {
      return type;
    }
  }
  return undefined;
}
