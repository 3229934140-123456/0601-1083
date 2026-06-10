import os
from tabulate import tabulate

from ..utils import (
    load_json, save_json, log_operation, PROJECT_MANIFEST,
    resolve_project_path
)


def set_project_metadata(work_dir, title=None, description=None,
                         platforms=None, author=None, notes=None):
    """设置项目元数据"""
    manifest_path = os.path.join(work_dir, PROJECT_MANIFEST)
    manifest = load_json(manifest_path)
    
    if not manifest:
        print(f"错误: 未找到项目清单，请先运行 scan 命令")
        return None
    
    if 'metadata' not in manifest:
        manifest['metadata'] = {}
    
    updates = []
    
    if title is not None:
        manifest['metadata']['title'] = title
        updates.append(f"标题: {title}")
    
    if description is not None:
        manifest['metadata']['description'] = description
        updates.append(f"描述: {description[:50]}..." if len(description) > 50 else f"描述: {description}")
    
    if platforms is not None:
        if isinstance(platforms, str):
            platforms = [p.strip() for p in platforms.split(',') if p.strip()]
        manifest['metadata']['platforms'] = platforms
        updates.append(f"发布平台: {', '.join(platforms)}")
    
    if author is not None:
        manifest['metadata']['author'] = author
        updates.append(f"作者: {author}")
    
    if notes is not None:
        manifest['metadata']['notes'] = notes
        updates.append(f"备注: {notes[:50]}..." if len(notes) > 50 else f"备注: {notes}")
    
    save_json(manifest, manifest_path)
    
    if updates:
        print("✓ 已更新项目元数据:")
        for update in updates:
            print(f"  - {update}")
    else:
        print("提示: 未提供任何元数据字段")
    
    log_operation(work_dir, 'metadata_project', {
        'updated_fields': [u.split(':')[0] for u in updates]
    })
    
    return manifest


def set_video_metadata(work_dir, video_path, title=None, description=None,
                       copy=None, tags=None):
    """设置单个视频的元数据"""
    manifest_path = os.path.join(work_dir, PROJECT_MANIFEST)
    manifest = load_json(manifest_path)
    
    if not manifest:
        print(f"错误: 未找到项目清单，请先运行 scan 命令")
        return None
    
    resolved_path = resolve_project_path(work_dir, video_path)
    if not resolved_path:
        print(f"错误: 未找到视频 {video_path}")
        return None
    
    target_video = None
    for video in manifest.get('videos', []):
        if os.path.abspath(video['path']) == resolved_path:
            target_video = video
            break
    
    if not target_video:
        print(f"错误: 未在项目清单中找到视频 {video_path}")
        return None
    
    if 'metadata' not in target_video:
        target_video['metadata'] = {}
    
    updates = []
    
    if title is not None:
        target_video['metadata']['title'] = title
        updates.append(f"标题: {title}")
    
    if description is not None:
        target_video['metadata']['description'] = description
        updates.append(f"描述: {description[:50]}..." if len(description) > 50 else f"描述: {description}")
    
    if copy is not None:
        target_video['metadata']['copy'] = copy
        updates.append(f"文案: {copy[:50]}..." if len(copy) > 50 else f"文案: {copy}")
    
    if tags is not None:
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',') if t.strip()]
        target_video['metadata']['tags'] = tags
        updates.append(f"自定义标签: {', '.join(tags)}")
    
    save_json(manifest, manifest_path)
    
    if updates:
        print(f"✓ 已更新 {target_video['name']} 的元数据:")
        for update in updates:
            print(f"  - {update}")
    else:
        print("提示: 未提供任何元数据字段")
    
    log_operation(work_dir, 'metadata_video', {
        'video': target_video['name'],
        'updated_fields': [u.split(':')[0] for u in updates]
    })
    
    return manifest


def show_metadata(work_dir, video_path=None):
    """显示项目或视频的元数据"""
    manifest_path = os.path.join(work_dir, PROJECT_MANIFEST)
    manifest = load_json(manifest_path)
    
    if not manifest:
        print(f"错误: 未找到项目清单")
        return
    
    print("\n📋 元数据信息")
    print("=" * 60)
    
    if video_path:
        resolved_path = resolve_project_path(work_dir, video_path)
        if not resolved_path:
            print(f"错误: 未找到视频 {video_path}")
            return
        
        target_video = None
        for video in manifest.get('videos', []):
            if os.path.abspath(video['path']) == resolved_path:
                target_video = video
                break
        
        if not target_video:
            print(f"错误: 未在项目清单中找到视频 {video_path}")
            return
        
        print(f"\n视频: {target_video['name']}")
        print("-" * 40)
        meta = target_video.get('metadata', {})
        if meta:
            table_data = []
            for key in ['title', 'description', 'copy']:
                if key in meta:
                    display_value = str(meta[key])
                    if len(display_value) > 50:
                        display_value = display_value[:47] + '...'
                    table_data.append([key, display_value])
            if 'tags' in meta:
                table_data.append(['tags', ', '.join(meta['tags'])])
            if table_data:
                print(tabulate(table_data, headers=['字段', '值'], tablefmt='simple'))
            else:
                print("  暂无元数据")
        else:
            print("  暂无元数据")
    else:
        print("\n项目元数据")
        print("-" * 40)
        meta = manifest.get('metadata', {})
        if meta:
            table_data = []
            for key in ['title', 'author']:
                if key in meta:
                    table_data.append([key, meta[key]])
            if 'platforms' in meta:
                table_data.append(['platforms', ', '.join(meta['platforms'])])
            for key in ['description', 'notes']:
                if key in meta:
                    display_value = str(meta[key])
                    if len(display_value) > 50:
                        display_value = display_value[:47] + '...'
                    table_data.append([key, display_value])
            print(tabulate(table_data, headers=['字段', '值'], tablefmt='simple'))
        else:
            print("  暂无元数据")
        
        print(f"\n视频元数据 ({len(manifest.get('videos', []))} 个视频):")
        print("-" * 40)
        has_any = False
        for video in manifest.get('videos', []):
            meta = video.get('metadata', {})
            if meta:
                has_any = True
                title = meta.get('title', '(未设置)')
                desc = meta.get('description', '')
                if len(desc) > 30:
                    desc = desc[:27] + '...'
                print(f"  {video['name']}:")
                print(f"    标题: {title}")
                if desc:
                    print(f"    描述: {desc}")
        
        if not has_any:
            print("  暂无视频元数据")
    
    print()
