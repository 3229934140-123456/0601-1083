import os
from pathlib import Path
from tabulate import tabulate

from ..utils import (
    load_json, save_json, is_video, log_operation, PROJECT_MANIFEST,
    resolve_project_path
)
from ..media import extract_video_thumbnails, get_image_dimensions


COVER_DIR = 'covers'


def extract_covers(work_dir, num_thumbs=5, target_video=None):
    """提取视频候选封面"""
    manifest_path = os.path.join(work_dir, PROJECT_MANIFEST)
    manifest = load_json(manifest_path)
    
    if not manifest or 'videos' not in manifest:
        print(f"错误: 未找到项目清单，请先运行 scan 命令")
        return None
    
    covers_dir = os.path.join(work_dir, COVER_DIR)
    Path(covers_dir).mkdir(parents=True, exist_ok=True)
    
    all_covers = []
    
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
        video_path = video['path']
        video_name = Path(video_path).stem
        video_cover_dir = os.path.join(covers_dir, video_name)
        
        print(f"\n处理视频: {video['name']}")
        
        thumbs = extract_video_thumbnails(video_path, video_cover_dir, num_thumbs)
        
        if thumbs:
            for thumb in thumbs:
                img_info = get_image_dimensions(thumb['file'])
                thumb.update(img_info)
                thumb['video'] = video['name']
                all_covers.append(thumb)
            print(f"  ✓ 提取了 {len(thumbs)} 张候选封面")
        else:
            print(f"  ⚠  未能提取封面（需要安装 ffmpeg/ffprobe）")
    
    manifest['covers'] = all_covers
    save_json(manifest, manifest_path)
    
    log_operation(work_dir, 'cover', {
        'count': len(all_covers),
        'num_thumbs': num_thumbs,
        'target': target_video or 'all'
    })
    
    return all_covers


def list_covers(work_dir):
    """列出所有候选封面"""
    manifest_path = os.path.join(work_dir, PROJECT_MANIFEST)
    manifest = load_json(manifest_path)
    
    covers = manifest.get('covers', [])
    
    if not covers:
        print("\n暂无候选封面，使用 cover extract 提取封面")
        return
    
    print("\n🖼️  候选封面列表")
    print("=" * 70)
    
    table_data = []
    for i, cover in enumerate(covers, 1):
        resolution = f"{cover.get('width', '?')}x{cover.get('height', '?')}"
        table_data.append([
            i,
            cover['video'],
            os.path.basename(cover['file']),
            cover.get('time_formatted', 'N/A'),
            resolution
        ])
    
    print(tabulate(table_data, headers=['#', '视频', '文件名', '时间点', '分辨率'], tablefmt='simple'))
    print(f"\n共 {len(covers)} 张候选封面")
    print(f"保存目录: {COVER_DIR}/")
    
    return covers


def select_cover(work_dir, cover_index, video_name=None):
    """选择封面作为主封面"""
    manifest_path = os.path.join(work_dir, PROJECT_MANIFEST)
    manifest = load_json(manifest_path)
    
    covers = manifest.get('covers', [])
    if not covers:
        print("错误: 没有候选封面")
        return None
    
    idx = cover_index - 1
    if idx < 0 or idx >= len(covers):
        print(f"错误: 索引超出范围 (1-{len(covers)})")
        return None
    
    selected = covers[idx]
    
    for video in manifest.get('videos', []):
        if video['name'] == selected['video']:
            video['selected_cover'] = selected['file']
            print(f"✓ 已为 {video['name']} 设置封面: {os.path.basename(selected['file'])}")
            break
    
    save_json(manifest, manifest_path)
    
    log_operation(work_dir, 'select_cover', {
        'cover_index': cover_index,
        'cover_file': selected['file']
    })
    
    return selected
