import os
import shutil
from pathlib import Path
from datetime import datetime
from tabulate import tabulate

from ..utils import (
    load_json, save_json, log_operation,
    PROJECT_MANIFEST, TAGS_FILE, TODO_FILE, OPERATION_LOG, PACK_DIR
)
from .check_cmd import check_project


def pack_project(work_dir, output_name=None, platforms=None):
    """打包项目为发布目录"""
    manifest_path = os.path.join(work_dir, PROJECT_MANIFEST)
    manifest = load_json(manifest_path)
    
    if not manifest:
        print(f"错误: 未找到项目清单，请先运行 scan 命令")
        return None
    
    if platforms is None:
        platforms = []
    elif isinstance(platforms, str):
        platforms = [p.strip() for p in platforms.split(',') if p.strip()]
    
    if not output_name:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dir_name = os.path.basename(os.path.normpath(work_dir))
        output_name = f"{dir_name}_publish_{timestamp}"
    
    pack_dir = os.path.join(work_dir, PACK_DIR, output_name)
    Path(pack_dir).mkdir(parents=True, exist_ok=True)
    
    print(f"\n📦 正在打包到: {output_name}")
    print("-" * 50)
    
    packed = {
        'pack_name': output_name,
        'created_at': datetime.now().isoformat(),
        'videos': [],
        'covers': [],
        'captions': [],
        'images': [],
    }
    
    videos_dir = os.path.join(pack_dir, '01_videos')
    Path(videos_dir).mkdir(exist_ok=True)
    for video in manifest.get('videos', []):
        src = video['path']
        if os.path.exists(src):
            dst = os.path.join(videos_dir, video['name'])
            shutil.copy2(src, dst)
            packed['videos'].append(video['name'])
            print(f"  ✓ 视频: {video['name']}")
    
    covers_dir = os.path.join(pack_dir, '02_covers')
    Path(covers_dir).mkdir(exist_ok=True)
    for video in manifest.get('videos', []):
        selected_cover = video.get('selected_cover')
        if selected_cover and os.path.exists(selected_cover):
            dst = os.path.join(covers_dir, f"{Path(video['name']).stem}_cover{Path(selected_cover).suffix}")
            shutil.copy2(selected_cover, dst)
            packed['covers'].append(os.path.basename(dst))
    
    covers_all_dir = os.path.join(covers_dir, 'candidates')
    Path(covers_all_dir).mkdir(exist_ok=True)
    for cover in manifest.get('covers', []):
        cover_file = cover.get('file')
        if cover_file and os.path.exists(cover_file):
            dst = os.path.join(covers_all_dir, os.path.basename(cover_file))
            shutil.copy2(cover_file, dst)
    
    print(f"  ✓ 封面: {len(packed['covers'])} 张已选 + {len(manifest.get('covers', []))} 张候选")
    
    captions_dir = os.path.join(pack_dir, '03_captions')
    Path(captions_dir).mkdir(exist_ok=True)
    captions_info = manifest.get('captions', {})
    for video_name, info in captions_info.items():
        for caption_type in ['srt', 'vtt']:
            cap_file = info.get(caption_type)
            if cap_file and os.path.exists(cap_file):
                dst = os.path.join(captions_dir, os.path.basename(cap_file))
                shutil.copy2(cap_file, dst)
                packed['captions'].append(os.path.basename(cap_file))
    print(f"  ✓ 字幕: {len(packed['captions'])} 个文件")
    
    images_dir = os.path.join(pack_dir, '04_images')
    Path(images_dir).mkdir(exist_ok=True)
    for img in manifest.get('images', []):
        src = img['path']
        if os.path.exists(src):
            dst = os.path.join(images_dir, img['name'])
            shutil.copy2(src, dst)
            packed['images'].append(img['name'])
    if packed['images']:
        print(f"  ✓ 图片: {len(packed['images'])} 张")
    
    metadata_dir = os.path.join(pack_dir, '05_metadata')
    Path(metadata_dir).mkdir(exist_ok=True)
    
    shutil.copy2(manifest_path, os.path.join(metadata_dir, 'project_manifest.json'))
    
    tags_src = os.path.join(work_dir, TAGS_FILE)
    if os.path.exists(tags_src):
        shutil.copy2(tags_src, os.path.join(metadata_dir, 'tags.txt'))
    
    _generate_publish_info(pack_dir, manifest, platforms)
    print("  ✓ 发布信息")
    
    todo_list = _generate_todo_list(work_dir, pack_dir, manifest, platforms)
    print("  ✓ 待办列表")
    
    log_src = os.path.join(work_dir, OPERATION_LOG)
    if os.path.exists(log_src):
        shutil.copy2(log_src, os.path.join(metadata_dir, 'operation_log.json'))
        print("  ✓ 操作记录")
    
    packed_info = {
        'pack_name': output_name,
        'created_at': datetime.now().isoformat(),
        'contents': packed,
        'platforms': platforms or [],
    }
    save_json(packed_info, os.path.join(metadata_dir, 'pack_info.json'))
    
    log_operation(work_dir, 'pack', {
        'output_name': output_name,
        'videos_count': len(packed['videos']),
        'covers_count': len(packed['covers'])
    })
    
    print(f"\n✅ 打包完成!")
    print(f"   目录: {pack_dir}")
    print(f"   视频: {len(packed['videos'])} 个")
    print(f"   封面: {len(packed['covers'])} 张已选")
    print(f"   字幕: {len(packed['captions'])} 个文件")
    
    return pack_dir


def _generate_publish_info(pack_dir, manifest, platforms=None):
    """生成发布信息文件"""
    info_path = os.path.join(pack_dir, '05_metadata', 'publish_info.md')
    
    project_tags = manifest.get('project_tags', [])
    hashtag_str = ' '.join([f'#{tag}' for tag in project_tags])
    
    with open(info_path, 'w', encoding='utf-8') as f:
        f.write("# 发布信息\n\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## 项目信息\n\n")
        f.write(f"- 项目目录: {manifest.get('work_directory', '')}\n")
        f.write(f"- 视频数量: {len(manifest.get('videos', []))}\n")
        f.write(f"- 图片数量: {len(manifest.get('images', []))}\n\n")
        
        f.write("## 话题标签\n\n")
        if hashtag_str:
            f.write(f"{hashtag_str}\n\n")
        else:
            f.write("（暂无标签）\n\n")
        
        f.write("## 视频详情\n\n")
        for i, video in enumerate(manifest.get('videos', []), 1):
            f.write(f"### 视频 {i}: {video['name']}\n\n")
            f.write(f"- 时长: {video.get('duration_formatted', 'N/A')}\n")
            f.write(f"- 分辨率: {video.get('width', '?')}x{video.get('height', '?')}\n")
            f.write(f"- 文件大小: {video.get('size_mb', '?')} MB\n")
            f.write(f"- 标签: {', '.join(video.get('tags', [])) or '无'}\n")
            f.write(f"- 封面: {os.path.basename(video.get('selected_cover', '')) or '未选择'}\n\n")
        
        if platforms:
            from .check_cmd import PLATFORMS
            f.write("## 平台发布提示\n\n")
            for platform_key in platforms:
                platform = PLATFORMS.get(platform_key)
                if platform:
                    f.write(f"### {platform['name']}\n\n")
                    f.write(f"- 推荐时长: {platform['ideal_duration'][0]}-{platform['ideal_duration'][1]} 秒\n")
                    f.write(f"- 最佳比例: {platform['ideal_ratio']}\n")
                    f.write(f"- 最大文件: {platform['max_file_size_mb']} MB\n\n")


def _generate_todo_list(work_dir, pack_dir, manifest, platforms=None):
    """生成待办事项列表"""
    todo_path = os.path.join(pack_dir, '05_metadata', TODO_FILE)
    
    todos = []
    
    if not manifest.get('title'):
        todos.append(('high', '设置视频标题', '为每个视频编写吸引人的标题'))
    
    if not manifest.get('description'):
        todos.append(('high', '编写视频描述', '撰写视频简介和描述文案'))
    
    if not manifest.get('project_tags', []):
        todos.append(('high', '添加话题标签', '添加相关话题标签以增加曝光'))
    
    selected_covers_count = sum(1 for v in manifest.get('videos', []) if v.get('selected_cover'))
    total_videos = len(manifest.get('videos', []))
    if selected_covers_count < total_videos:
        todos.append(('medium', '选择封面图', f'已选 {selected_covers_count}/{total_videos} 个视频选择了封面'))
    
    captions_count = len(manifest.get('captions', {}))
    if captions_count < total_videos:
        todos.append(('medium', '完善字幕', f'已生成 {captions_count}/{total_videos} 个视频字幕草稿'))
    
    todos.append(('low', '检查视频质量', '确认视频画质、音质、画面稳定性'))
    todos.append(('low', '预览最终效果', '完整观看一遍确认无误'))
    
    if platforms:
        todos.append(('medium', '适配各平台', f'根据 {len(platforms)} 个平台要求调整内容'))
    
    with open(todo_path, 'w', encoding='utf-8') as f:
        f.write("# 发布前待办列表\n\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        priority_order = {'high': '🔴 高优先级', 'medium': '🟡 中优先级', 'low': '🟢 低优先级'}
        
        for priority in ['high', 'medium', 'low']:
            priority_todos = [(t, d) for (p, t, d) in todos if p == priority]
            if priority_todos:
                f.write(f"## {priority_order[priority]}\n\n")
                for i, (title, desc) in enumerate(priority_todos, 1):
                    f.write(f"- [ ] {title}\n")
                    f.write(f"  {desc}\n")
                f.write("\n")
        
        f.write("---\n\n")
        f.write("## 操作记录摘要\n\n")
        op_log_path = os.path.join(work_dir, OPERATION_LOG)
        if os.path.exists(op_log_path):
            from ..utils import load_json
            op_log = load_json(op_log_path, [])
            for entry in reversed(op_log[-10:]):
                ts = entry.get('timestamp', '')
                op = entry.get('operation', '')
                f.write(f"- {ts}: {op}\n")
    
    return todos


def list_packs(work_dir):
    """列出所有已打包的发布包"""
    packs_root = os.path.join(work_dir, PACK_DIR)
    
    if not os.path.exists(packs_root):
        print("\n暂无打包记录")
        return []
    
    packs = []
    for item in os.listdir(packs_root):
        item_path = os.path.join(packs_root, item)
        if os.path.isdir(item_path):
            info_path = os.path.join(item_path, '05_metadata', 'pack_info.json')
            if os.path.exists(info_path):
                from ..utils import load_json
                info = load_json(info_path)
                packs.append({
                    'name': item,
                    'path': item_path,
                    'created_at': info.get('created_at', ''),
                    'videos': len(info.get('contents', {}).get('videos', [])),
                })
    
    if not packs:
        print("\n暂无打包记录")
        return []
    
    print("\n📦 发布包列表")
    print("=" * 60)
    
    table_data = []
    for i, pack in enumerate(packs, 1):
        table_data.append([
            i,
            pack['name'],
            pack.get('created_at', '?')[:19].replace('T', ' '),
            pack.get('videos', 0)
        ])
    
    print(tabulate(table_data, headers=['#', '名称', '创建时间', '视频数'], tablefmt='simple'))
    
    return packs
