import os
import json
from datetime import datetime
from pathlib import Path

VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.webm', '.m4v'}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.aac', '.flac', '.m4a'}
SUBTITLE_EXTENSIONS = {'.srt', '.vtt', '.ass', '.ssa'}

PROJECT_MANIFEST = 'project_manifest.json'
TAGS_FILE = 'tags.txt'
TODO_FILE = 'todo_list.md'
OPERATION_LOG = 'operation_log.json'
PACK_DIR = 'publish_pack'


def is_video(filename):
    """判断是否为视频文件"""
    return Path(filename).suffix.lower() in VIDEO_EXTENSIONS


def is_image(filename):
    """判断是否为图片文件"""
    return Path(filename).suffix.lower() in IMAGE_EXTENSIONS


def is_audio(filename):
    """判断是否为音频文件"""
    return Path(filename).suffix.lower() in AUDIO_EXTENSIONS


def is_subtitle(filename):
    """判断是否为字幕文件"""
    return Path(filename).suffix.lower() in SUBTITLE_EXTENSIONS


def get_file_info(file_path):
    """获取文件基本信息"""
    path = Path(file_path)
    stat = path.stat()
    return {
        'name': path.name,
        'path': str(path.absolute()),
        'size': stat.st_size,
        'size_mb': round(stat.st_size / (1024 * 1024), 2),
        'extension': path.suffix.lower(),
        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
        'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
    }


def save_json(data, file_path):
    """保存 JSON 文件"""
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(file_path, default=None):
    """加载 JSON 文件"""
    if not os.path.exists(file_path):
        return default if default is not None else {}
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def log_operation(work_dir, operation, details=None):
    """记录操作日志"""
    log_path = os.path.join(work_dir, OPERATION_LOG)
    log_data = load_json(log_path, [])
    
    entry = {
        'timestamp': datetime.now().isoformat(),
        'operation': operation,
        'details': details or {}
    }
    log_data.append(entry)
    save_json(log_data, log_path)
    return entry


def resolve_project_path(work_dir, target_path):
    """
    解析项目内的路径
    优先按绝对路径查找，然后按相对 work_dir 查找，最后按相对当前目录查找
    当指定了 work_dir 时，相对路径优先相对于 work_dir 解析
    """
    if not target_path:
        return None
    
    path_obj = Path(target_path)
    
    if path_obj.is_absolute():
        if path_obj.exists():
            return str(path_obj.absolute())
    
    if work_dir:
        relative_to_work = os.path.join(work_dir, target_path)
        if os.path.exists(relative_to_work):
            return str(Path(relative_to_work).absolute())
    
    if os.path.exists(target_path):
        return str(Path(target_path).absolute())
    
    return None


def ensure_absolute_path(work_dir, target_path):
    """确保路径是绝对路径，如果项目内存在则返回项目内的绝对路径"""
    resolved = resolve_project_path(work_dir, target_path)
    if resolved:
        return resolved
    if target_path and not Path(target_path).is_absolute():
        return str(Path(os.path.join(work_dir, target_path)).absolute())
    return target_path


CHECK_REPORT = 'check_report.json'
TODO_STATE_FILE = 'todo_state.json'
PUBLISH_PLAN_DIR = 'publish_plans'

