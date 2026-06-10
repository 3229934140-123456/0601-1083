import os
from pathlib import Path
from tabulate import tabulate

from ..utils import (
    is_video, is_image, is_audio, is_subtitle,
    get_file_info, save_json, load_json, log_operation,
    PROJECT_MANIFEST, PACK_DIR
)
from ..media import get_video_info, get_image_dimensions


def scan_directory(work_dir, recursive=True, include_subdirs=None):
    """扫描目录，生成项目清单"""
    work_dir = os.path.abspath(work_dir)
    
    manifest_path = os.path.join(work_dir, PROJECT_MANIFEST)
    old_manifest = load_json(manifest_path, {})
    
    old_videos = {v['path']: v for v in old_manifest.get('videos', [])}
    old_images = {img['path']: img for img in old_manifest.get('images', [])}
    
    exclude_dirs = {PACK_DIR, 'covers', 'captions', '.git', '__pycache__'}
    
    videos = []
    images = []
    audios = []
    subtitles = []
    other_files = []
    subdirectories = []
    
    if recursive:
        for root, dirs, files in os.walk(work_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for filename in files:
                filepath = os.path.join(root, filename)
                abs_path = os.path.abspath(filepath)
                
                file_info = get_file_info(filepath)
                
                if is_video(filename):
                    video_detail = get_video_info(filepath)
                    file_info.update(video_detail)
                    if abs_path in old_videos:
                        old_tags = old_videos[abs_path].get('tags', [])
                        old_cover = old_videos[abs_path].get('selected_cover')
                        old_metadata = old_videos[abs_path].get('metadata', {})
                        if old_tags:
                            file_info['tags'] = old_tags
                        if old_cover:
                            file_info['selected_cover'] = old_cover
                        if old_metadata:
                            file_info['metadata'] = old_metadata
                    videos.append(file_info)
                elif is_image(filename):
                    img_detail = get_image_dimensions(filepath)
                    file_info.update(img_detail)
                    if abs_path in old_images:
                        old_tags = old_images[abs_path].get('tags', [])
                        if old_tags:
                            file_info['tags'] = old_tags
                    images.append(file_info)
                elif is_audio(filename):
                    audios.append(file_info)
                elif is_subtitle(filename):
                    subtitles.append(file_info)
                else:
                    other_files.append(file_info)
            
            for d in dirs:
                subdirectories.append(os.path.join(root, d))
    else:
        for item in os.listdir(work_dir):
            item_path = os.path.join(work_dir, item)
            abs_path = os.path.abspath(item_path)
            if os.path.isfile(item_path):
                file_info = get_file_info(item_path)
                
                if is_video(item):
                    video_detail = get_video_info(item_path)
                    file_info.update(video_detail)
                    if abs_path in old_videos:
                        old_tags = old_videos[abs_path].get('tags', [])
                        old_cover = old_videos[abs_path].get('selected_cover')
                        old_metadata = old_videos[abs_path].get('metadata', {})
                        if old_tags:
                            file_info['tags'] = old_tags
                        if old_cover:
                            file_info['selected_cover'] = old_cover
                        if old_metadata:
                            file_info['metadata'] = old_metadata
                    videos.append(file_info)
                elif is_image(item):
                    img_detail = get_image_dimensions(item_path)
                    file_info.update(img_detail)
                    if abs_path in old_images:
                        old_tags = old_images[abs_path].get('tags', [])
                        if old_tags:
                            file_info['tags'] = old_tags
                    images.append(file_info)
                elif is_audio(item):
                    audios.append(file_info)
                elif is_subtitle(item):
                    subtitles.append(file_info)
                else:
                    other_files.append(file_info)
            elif os.path.isdir(item_path):
                subdirectories.append(item_path)
    
    manifest = {
        'work_directory': work_dir,
        'project_tags': old_manifest.get('project_tags', []),
        'metadata': old_manifest.get('metadata', {}),
        'summary': {
            'total_files': len(videos) + len(images) + len(audios) + len(subtitles) + len(other_files),
            'videos': len(videos),
            'images': len(images),
            'audios': len(audios),
            'subtitles': len(subtitles),
            'other_files': len(other_files),
            'subdirectories': len(subdirectories),
        },
        'videos': videos,
        'images': images,
        'audios': audios,
        'subtitles': subtitles,
        'other_files': other_files,
        'subdirectories': subdirectories,
        'covers': old_manifest.get('covers', []),
        'captions': old_manifest.get('captions', {}),
    }
    
    save_json(manifest, manifest_path)
    
    log_operation(work_dir, 'scan', {
        'videos_count': len(videos),
        'images_count': len(images),
        'recursive': recursive
    })
    
    return manifest


def print_scan_report(manifest):
    """打印扫描报告"""
    print("\n" + "=" * 60)
    print("  项目扫描报告")
    print("=" * 60)
    print(f"\n目录: {manifest['work_directory']}")
    
    print("\n📊 统计概览")
    print("-" * 40)
    summary = manifest['summary']
    print(f"  视频文件: {summary['videos']}")
    print(f"  图片文件: {summary['images']}")
    print(f"  音频文件: {summary['audios']}")
    print(f"  字幕文件: {summary['subtitles']}")
    print(f"  其他文件: {summary['other_files']}")
    print(f"  子目录数: {summary['subdirectories']}")
    print(f"  文件总计: {summary['total_files']}")
    
    if manifest['videos']:
        print("\n🎬 视频文件列表")
        print("-" * 60)
        table_data = []
        for v in manifest['videos']:
            duration = v.get('duration_formatted', 'N/A')
            resolution = f"{v.get('width', '?')}x{v.get('height', '?')}" if v.get('width') else 'N/A'
            table_data.append([
                v['name'],
                f"{v['size_mb']} MB",
                duration,
                resolution,
                v.get('orientation', 'N/A')
            ])
        print(tabulate(table_data, headers=['文件名', '大小', '时长', '分辨率', '方向'], tablefmt='simple'))
    
    if manifest['images']:
        print("\n🖼️  图片文件列表")
        print("-" * 60)
        table_data = []
        for img in manifest['images']:
            resolution = f"{img.get('width', '?')}x{img.get('height', '?')}" if img.get('width') else 'N/A'
            table_data.append([
                img['name'],
                f"{img['size_mb']} MB",
                resolution,
                img.get('orientation', 'N/A')
            ])
        print(tabulate(table_data, headers=['文件名', '大小', '分辨率', '方向'], tablefmt='simple'))
    
    print(f"\n💾 清单已保存至: project_manifest.json")
