"""
比较 Paseo Pvt 2.m4a 和 TTS 样本的音频特征（基频、能量、语速感）。
用 ffmpeg 转 wav → numpy 分析 → 输出最匹配的 TTS 音色。
"""
import subprocess
import struct
import os
import wave
import numpy as np
from pathlib import Path
import tempfile

VOICE_DIR = Path(__file__).parent
SAMPLE_DIRS = [
    VOICE_DIR / "samples_tencent",
    VOICE_DIR / "samples_volcano",
]

def convert_to_wav(input_path: Path, output_path: Path):
    """用 ffmpeg 转成 16kHz mono wav"""
    subprocess.run([
        "ffmpeg", "-y", "-i", str(input_path),
        "-ar", "16000", "-ac", "1", "-f", "wav",
        str(output_path)
    ], capture_output=True, check=True)

def read_wav(wav_path: Path) -> np.ndarray:
    """读取 wav 文件返回 float32 numpy 数组"""
    with wave.open(str(wav_path), 'rb') as wf:
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)
        data = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
        data /= 32768.0  # normalize to [-1, 1]
    return data

def estimate_pitch(data: np.ndarray, sr: int = 16000) -> float:
    """用自相关法估计基频 (F0)"""
    # 取中间 2 秒
    mid = len(data) // 2
    chunk = data[max(0, mid - sr): mid + sr]
    
    # 自相关
    corr = np.correlate(chunk, chunk, mode='full')
    corr = corr[len(corr)//2:]
    
    # 找第一个峰值（跳过 lag=0）
    min_lag = int(sr / 500)  # 500 Hz 上限
    max_lag = int(sr / 50)   # 50 Hz 下限
    
    if max_lag >= len(corr):
        max_lag = len(corr) - 1
    
    segment = corr[min_lag:max_lag]
    if len(segment) == 0:
        return 0.0
    
    peak_idx = np.argmax(segment) + min_lag
    if peak_idx == 0:
        return 0.0
    
    f0 = sr / peak_idx
    return f0

def analyze_audio(data: np.ndarray, sr: int = 16000) -> dict:
    """分析音频特征"""
    # 基频
    f0 = estimate_pitch(data, sr)
    
    # RMS 能量
    rms = np.sqrt(np.mean(data ** 2))
    
    # 过零率 (语速/清晰度相关)
    zcr = np.mean(np.abs(np.diff(np.sign(data)))) / 2
    
    # 频谱质心 (音色亮度)
    fft_data = np.abs(np.fft.rfft(data))
    freqs = np.fft.rfftfreq(len(data), 1/sr)
    spectral_centroid = np.sum(freqs * fft_data) / (np.sum(fft_data) + 1e-10)
    
    # 有效时长（非静音）
    threshold = 0.02
    active = np.abs(data) > threshold
    active_ratio = np.mean(active)
    
    return {
        "f0": round(f0, 1),
        "rms": round(rms, 4),
        "zcr": round(zcr, 4),
        "spectral_centroid": round(spectral_centroid, 1),
        "active_ratio": round(active_ratio, 3),
        "duration": round(len(data) / sr, 2),
    }

def feature_distance(a: dict, b: dict) -> float:
    """计算两组特征的归一化距离"""
    # 权重：基频最重要，频谱质心次之
    weights = {
        "f0": 3.0,
        "spectral_centroid": 2.0,
        "zcr": 1.0,
        "rms": 0.5,
    }
    
    dist = 0.0
    for key, w in weights.items():
        va = a.get(key, 0)
        vb = b.get(key, 0)
        if va == 0 and vb == 0:
            continue
        # 相对差异
        norm = max(abs(va), abs(vb), 1e-10)
        d = abs(va - vb) / norm
        dist += w * d
    
    return dist

def main():
    # 1. 转换目标音频
    target_m4a = VOICE_DIR / "Paseo Pvt 2.m4a"
    target_wav = VOICE_DIR / "_target_temp.wav"
    
    print(f"🎙️ 分析目标音频: {target_m4a.name}")
    convert_to_wav(target_m4a, target_wav)
    target_data = read_wav(target_wav)
    target_features = analyze_audio(target_data)
    
    print(f"   基频 F0: {target_features['f0']} Hz")
    print(f"   能量 RMS: {target_features['rms']}")
    print(f"   过零率 ZCR: {target_features['zcr']}")
    print(f"   频谱质心: {target_features['spectral_centroid']} Hz")
    print(f"   时长: {target_features['duration']}s")
    
    # 判断性别
    if target_features['f0'] > 0:
        gender = "女声" if target_features['f0'] > 180 else "男声"
        print(f"   推测: {gender} (F0={target_features['f0']}Hz)")
    
    print(f"\n{'='*60}")
    print(f"📊 与 TTS 样本逐一对比...")
    print(f"{'='*60}\n")
    
    results = []
    
    for sample_dir in SAMPLE_DIRS:
        if not sample_dir.exists():
            continue
        
        provider = sample_dir.name.replace("samples_", "").upper()
        
        for wav_file in sorted(sample_dir.glob("*.wav")):
            try:
                sample_data = read_wav(wav_file)
                sample_features = analyze_audio(sample_data)
                dist = feature_distance(target_features, sample_features)
                
                results.append({
                    "provider": provider,
                    "name": wav_file.stem,
                    "distance": dist,
                    "f0": sample_features["f0"],
                    "spectral_centroid": sample_features["spectral_centroid"],
                    "features": sample_features,
                })
            except Exception as e:
                print(f"   ⚠️ 跳过 {wav_file.name}: {e}")
    
    # 排序
    results.sort(key=lambda x: x["distance"])
    
    # 输出 Top 10
    print(f"🏆 最匹配的 TTS 音色 (距离越小越近):\n")
    print(f"{'排名':>4} | {'距离':>6} | {'提供商':>8} | {'F0':>6} | {'名称'}")
    print(f"{'-'*4}-+-{'-'*6}-+-{'-'*8}-+-{'-'*6}-+-{'-'*30}")
    
    for i, r in enumerate(results[:15]):
        marker = " ⭐" if i < 3 else ""
        print(f"{i+1:>4} | {r['distance']:>6.3f} | {r['provider']:>8} | {r['f0']:>5.0f}Hz | {r['name']}{marker}")
    
    # 清理
    if target_wav.exists():
        target_wav.unlink()
    
    print(f"\n✅ 目标音频 F0={target_features['f0']}Hz, 频谱质心={target_features['spectral_centroid']}Hz")
    print(f"   最佳匹配: {results[0]['name']} (距离={results[0]['distance']:.3f})")

if __name__ == "__main__":
    main()
