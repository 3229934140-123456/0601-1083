import os
from pathlib import Path
from tabulate import tabulate

from ..utils import (
    load_json, save_json, is_video, is_subtitle,
    log_operation, PROJECT_MANIFEST, resolve_project_path
)
from ..media import get_video_info, format_duration

CAPTION_DIR = 'captions'


def generate_caption_draft(work_dir, target_video=None, template_type='basic'):
    """生成字幕时间轴草稿"""
    manifest_path = os.path.join(work_dir, PROJECT_MANIFEST)
    manifest = load_json(manifest_path)
    
    if not manifest or 'videos' not in manifest:
        print(f"错误: 未找到项目清单，请先运行 scan 命令")
        return None
    
    captions_dir = os.path.join(work_dir, CAPTION_DIR)
    Path(captions_dir).mkdir(parents=True, exist_ok=True)
    
    generated = []
    
    if target_video:
        videos_to_process = []
        target_path = resolve_project_path(work_dir, target_video)
        if not target_path:
            print(f"错误: 未找到视频 {target_video}")
            return None
        
        for v in manifest['videos']:
            if os.path.abspath(v['path']) == target_path:
                videos_to_process.append(v)
                break
        if not videos_to_process:
            print(f"错误: 未在项目清单中找到视频 {target_video}")
            return None
    else:
        videos_to_process = manifest['videos']
    
    for video in videos_to_process:
        video_name = Path(video['name']).stem
        srt_path = os.path.join(captions_dir, f"{video_name}.srt")
        vtt_path = os.path.join(captions_dir, f"{video_name}.vtt")
        
        duration = video.get('duration', 60)
        if not duration or duration <= 0:
            duration = 60
        
        subtitles = _generate_template_subtitles(duration, template_type)
        
        _write_srt(subtitles, srt_path)
        _write_vtt(subtitles, vtt_path)
        
        if 'captions' not in manifest:
            manifest['captions'] = {}
        manifest['captions'][video['name']] = {
            'srt': srt_path,
            'vtt': vtt_path,
            'lines_count': len(subtitles),
            'template': template_type
        }
        
        generated.append({
            'video': video['name'],
            'srt': srt_path,
            'vtt': vtt_path,
            'lines': len(subtitles)
        })
        
        print(f"✓ 已生成 {video['name']} 的字幕草稿 ({len(subtitles)} 条)")
    
    save_json(manifest, manifest_path)
    
    log_operation(work_dir, 'caption', {
        'generated_count': len(generated),
        'template_type': template_type,
        'target': target_video or 'all'
    })
    
    return generated


def _generate_template_subtitles(duration, template_type='basic'):
    """生成模板字幕条目"""
    subtitles = []
    
    if template_type == 'basic':
        num_lines = max(3, min(10, int(duration / 10)))
        interval = duration / num_lines
        
        for i in range(num_lines):
            start = i * interval
            end = (i + 1) * interval
            subtitles.append({
                'index': i + 1,
                'start': start,
                'end': end,
                'text': f"[第 {i+1} 条字幕 - 请编辑此处文本]"
            })
    
    elif template_type == 'intro':
        templates = [
            (0, 3, "开场 - 引人入胜的标题"),
            (3, 8, "介绍主题和内容概要"),
            (8, 15, "第一部分：核心内容"),
            (15, 25, "第二部分：深入解析"),
            (25, 35, "第三部分：实例演示"),
            (35, 45, "总结与要点回顾"),
            (45, 50, "结尾引导 - 关注点赞"),
        ]
        for i, (start, end, text) in enumerate(templates):
            if start < duration:
                subtitles.append({
                    'index': i + 1,
                    'start': start,
                    'end': min(end, duration),
                    'text': text
                })
    
    elif template_type == 'story':
        templates = [
            (0, 2, "👋 哈喽大家好！"),
            (2, 6, "今天我们来聊聊..."),
            (6, 15, "首先，第一点是..."),
            (15, 25, "其次，第二点也很重要..."),
            (25, 35, "最后，总结一下..."),
            (35, 40, "记得点赞关注哦！❤️"),
        ]
        for i, (start, end, text) in enumerate(templates):
            if start < duration:
                subtitles.append({
                    'index': i + 1,
                    'start': start,
                    'end': min(end, duration),
                    'text': text
                })
    
    return subtitles


def _write_srt(subtitles, filepath):
    """写入 SRT 格式字幕"""
    with open(filepath, 'w', encoding='utf-8') as f:
        for sub in subtitles:
            f.write(f"{sub['index']}\n")
            f.write(f"{_format_srt_time(sub['start'])} --> {_format_srt_time(sub['end'])}\n")
            f.write(f"{sub['text']}\n\n")


def _write_vtt(subtitles, filepath):
    """写入 VTT 格式字幕"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("WEBVTT\n\n")
        for sub in subtitles:
            f.write(f"{_format_vtt_time(sub['start'])} --> {_format_vtt_time(sub['end'])}\n")
            f.write(f"{sub['text']}\n\n")


def _format_srt_time(seconds):
    """格式化 SRT 时间 HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _format_vtt_time(seconds):
    """格式化 VTT 时间 HH:MM:SS.mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def list_captions(work_dir):
    """列出所有字幕文件"""
    manifest_path = os.path.join(work_dir, PROJECT_MANIFEST)
    manifest = load_json(manifest_path)
    
    captions = manifest.get('captions', {})
    
    if not captions:
        print("\n暂无字幕草稿，使用 caption generate 生成")
        return
    
    print("\n📝 字幕文件列表")
    print("=" * 60)
    
    table_data = []
    for video_name, info in captions.items():
        table_data.append([
            video_name,
            info.get('lines_count', '?'),
            info.get('template', '?'),
            os.path.basename(info.get('srt', ''))
        ])
    
    print(tabulate(table_data, headers=['视频', '字幕条数', '模板类型', 'SRT 文件'], tablefmt='simple'))
    print(f"\n保存目录: {CAPTION_DIR}/")
    
    return captions
