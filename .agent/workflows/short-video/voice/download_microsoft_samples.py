"""
下载微软 Edge TTS 中文语音样本（zh-CN / zh-TW / zh-HK）。
测试文本为中英混合，验证双语能力。

用法:
  uv run python .agent/workflows/short-video/voice/download_microsoft_samples.py
"""
import asyncio
from pathlib import Path

import edge_tts

VOICE_DIR = Path(__file__).parent
OUTPUT_DIR = VOICE_DIR / "samples_microsoft"

# 中英混合测试文本 —— 验证中文为主 + 英文穿插的真实短视频场景
TEXT = (
    "大家好，欢迎来到加拿大新移民生活指南。"
    "今天聊一聊，刚到加拿大该怎么选银行。"
    "比如 TD、RBC、BMO 这几家大银行，"
    "都有 Newcomer Program，可以免费用一到两年。"
    "具体来说，TD 的 All-Inclusive Banking Plan，"
    "第一年月费全免，还送一张 Visa Infinite 信用卡。"
    "所以别着急，看完这期视频你就有答案了。"
)


async def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("📋 正在获取微软 Edge TTS 语音列表...")
    voices = await edge_tts.list_voices()

    # 只保留中文语音 (zh-CN / zh-TW / zh-HK)
    zh_voices = [v for v in voices if v["Locale"].startswith("zh-")]
    print(f"   总语音: {len(voices)}，中文语音: {len(zh_voices)}\n")

    print(f"{'序号':>4}  {'ShortName':<45} {'性别':<6} {'地区'}")
    print(f"{'-'*4}  {'-'*45} {'-'*6} {'-'*10}")
    for i, v in enumerate(zh_voices):
        print(f"{i+1:>4}  {v['ShortName']:<45} {v['Gender']:<6} {v['Locale']}")
    print()

    # 逐个下载
    success = 0
    skip = 0
    fail = 0
    sem = asyncio.Semaphore(3)

    async def download(i, v):
        nonlocal success, skip, fail
        name = v["ShortName"]       # e.g. zh-CN-XiaoxiaoNeural
        locale = v["Locale"]        # e.g. zh-CN
        gender = v["Gender"]        # Male / Female

        # 文件名: zh-CN_XiaoxiaoNeural_Female.mp3
        fname = f"{locale}_{name.split('-', 2)[-1]}_{gender}.mp3"
        output_path = OUTPUT_DIR / fname

        if output_path.exists() and output_path.stat().st_size > 1000:
            skip += 1
            print(f"  [{i+1}/{len(zh_voices)}] ⏭️  已存在: {fname}")
            return

        async with sem:
            print(f"  [{i+1}/{len(zh_voices)}] 🔊 合成: {name}")
            try:
                comm = edge_tts.Communicate(TEXT, name)
                await comm.save(str(output_path))
                kb = output_path.stat().st_size / 1024
                print(f"           ✅ {kb:.0f} KB → {fname}")
                success += 1
            except Exception as e:
                print(f"           ❌ {e}")
                fail += 1

    tasks = [download(i, v) for i, v in enumerate(zh_voices)]
    await asyncio.gather(*tasks)

    print(f"\n{'='*50}")
    print(f"✅ 完成!  成功={success}  跳过={skip}  失败={fail}")
    print(f"📂 {OUTPUT_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
