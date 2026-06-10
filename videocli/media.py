import os
import subprocess
import json
from pathlib import Path
from PIL import Image


def get_image_dimensions(image_path):
    """获取图片尺寸"""
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            return {
                'width': width,
                'height': height,
                'aspect_ratio': round(width / height, 4),
                'orientation': 'portrait' if height > width else ('landscape' if width > height else 'square'),
                'mode': img.mode,
                'format': img.format,
            }
    except Exception as e:
        return {'error': str(e)}


def get_video_info(video_path):
    """获取视频信息，优先使用 ffprobe，失败则返回基本信息"""
    info = {'path': video_path}
    
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json',
             '-show_format', '-show_streams', video_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            format_info = data.get('format', {})
            video_stream = None
            audio_stream = None
            
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video' and video_stream is None:
                    video_stream = stream
                elif stream.get('codec_type') == 'audio' and audio_stream is None:
                    audio_stream = stream
            
            duration = float(format_info.get('duration', 0))
            info['duration'] = round(duration, 2)
            info['duration_formatted'] = format_duration(duration)
            info['bit_rate'] = format_info.get('bit_rate')
            info['size'] = int(format_info.get('size', 0))
            
            if video_stream:
                info['width'] = video_stream.get('width')
                info['height'] = video_stream.get('height')
                info['codec'] = video_stream.get('codec_name')
                info['fps'] = _parse_fps(video_stream.get('r_frame_rate', '0/1'))
                if info['width'] and info['height']:
                    info['aspect_ratio'] = round(info['width'] / info['height'], 4)
                    info['orientation'] = 'portrait' if info['height'] > info['width'] else (
                        'landscape' if info['width'] > info['height'] else 'square'
                    )
            
            if audio_stream:
                info['audio_codec'] = audio_stream.get('codec_name')
                info['audio_sample_rate'] = audio_stream.get('sample_rate')
                info['audio_channels'] = audio_stream.get('channels')
            
            info['has_ffprobe'] = True
            return info
    except (subprocess.SubprocessError, FileNotFoundError, json.JSONDecodeError):
        pass
    
    info['has_ffprobe'] = False
    info['note'] = 'ffprobe not available, limited info'
    return info


def _parse_fps(fps_str):
    """解析帧率字符串，如 '30/1' 或 '2997/100'"""
    try:
        if '/' in fps_str:
            num, den = fps_str.split('/')
            if den == '0':
                return 0
            return round(float(num) / float(den), 2)
        return float(fps_str)
    except (ValueError, ZeroDivisionError):
        return 0


def format_duration(seconds):
    """将秒数格式化为 时:分:秒"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def extract_video_thumbnails(video_path, output_dir, num_thumbs=5):
    """从视频中提取候选封面（需要 ffprobe 和 ffmpeg）"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    thumbnails = []
    
    try:
        info = get_video_info(video_path)
        duration = info.get('duration', 0)
        
        if duration <= 0:
            return thumbnails
        
        interval = duration / (num_thumbs + 1)
        video_name = Path(video_path).stem
        
        for i in range(1, num_thumbs + 1):
            timestamp = interval * i
            output_file = os.path.join(output_dir, f"{video_name}_cover_{i:02d}.jpg")
            
            result = subprocess.run(
                ['ffmpeg', '-y', '-ss', str(timestamp), '-i', video_path,
                 '-vframes', '1', '-q:v', '2', output_file],
                capture_output=True,
                timeout=30
            )
            
            if result.returncode == 0 and os.path.exists(output_file):
                thumbnails.append({
                    'file': output_file,
                    'timestamp': round(timestamp, 2),
                    'time_formatted': format_duration(timestamp),
                    'index': i
                })
    
    except Exception as e:
        print(f"Warning: Failed to extract thumbnails: {e}")
    
    return thumbnails
