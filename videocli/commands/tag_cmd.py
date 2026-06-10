import os
from pathlib import Path

from ..utils import (
    load_json, save_json, is_video, is_image,
    log_operation, PROJECT_MANIFEST, TAGS_FILE
)


def add_tags(work_dir, tags, target=None):
    """为项目或特定文件添加标签"""
    manifest_path = os.path.join(work_dir, PROJECT_MANIFEST)
    manifest = load_json(manifest_path)
    
    if not manifest or 'videos' not in manifest:
        print(f"错误: 未找到项目清单，请先运行 scan 命令")
        return None
    
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(',') if t.strip()]
    
    tags = list(set(tags))
    
    if target:
        target_path = os.path.abspath(target)
        for item_type in ['videos', 'images']:
            for item in manifest.get(item_type, []):
                if os.path.abspath(item['path']) == target_path:
                    if 'tags' not in item:
                        item['tags'] = []
                    for tag in tags:
                        if tag not in item['tags']:
                            item['tags'].append(tag)
                    print(f"✓ 已为 {item['name']} 添加标签: {', '.join(tags)}")
    else:
        if 'project_tags' not in manifest:
            manifest['project_tags'] = []
        for tag in tags:
            if tag not in manifest['project_tags']:
                manifest['project_tags'].append(tag)
        print(f"✓ 已添加项目标签: {', '.join(tags)}")
    
    save_json(manifest, manifest_path)
    
    _update_tags_file(work_dir, manifest)
    
    log_operation(work_dir, 'tag', {
        'tags': tags,
        'target': target or 'project'
    })
    
    return manifest


def remove_tags(work_dir, tags, target=None):
    """移除标签"""
    manifest_path = os.path.join(work_dir, PROJECT_MANIFEST)
    manifest = load_json(manifest_path)
    
    if not manifest:
        print(f"错误: 未找到项目清单")
        return None
    
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(',') if t.strip()]
    
    if target:
        target_path = os.path.abspath(target)
        for item_type in ['videos', 'images']:
            for item in manifest.get(item_type, []):
                if os.path.abspath(item['path']) == target_path:
                    if 'tags' in item:
                        item['tags'] = [t for t in item['tags'] if t not in tags]
                        print(f"✓ 已从 {item['name']} 移除标签: {', '.join(tags)}")
    else:
        if 'project_tags' in manifest:
            manifest['project_tags'] = [t for t in manifest['project_tags'] if t not in tags]
            print(f"✓ 已移除项目标签: {', '.join(tags)}")
    
    save_json(manifest, manifest_path)
    _update_tags_file(work_dir, manifest)
    
    log_operation(work_dir, 'untag', {
        'tags': tags,
        'target': target or 'project'
    })
    
    return manifest


def list_tags(work_dir):
    """列出所有标签"""
    manifest_path = os.path.join(work_dir, PROJECT_MANIFEST)
    manifest = load_json(manifest_path)
    
    if not manifest:
        print(f"错误: 未找到项目清单")
        return
    
    print("\n🏷️  标签列表")
    print("=" * 50)
    
    project_tags = manifest.get('project_tags', [])
    if project_tags:
        print(f"\n项目标签 ({len(project_tags)}):")
        for tag in project_tags:
            print(f"  - {tag}")
    
    all_item_tags = set()
    tagged_items = []
    for item_type in ['videos', 'images']:
        for item in manifest.get(item_type, []):
            item_tags = item.get('tags', [])
            if item_tags:
                tagged_items.append((item['name'], item_tags))
                all_item_tags.update(item_tags)
    
    if all_item_tags:
        print(f"\n文件标签 ({len(all_item_tags)} 种):")
        for tag in sorted(all_item_tags):
            print(f"  - {tag}")
    
    if tagged_items:
        print(f"\n已标记文件 ({len(tagged_items)}):")
        for name, tags in tagged_items:
            print(f"  {name}: {', '.join(tags)}")
    
    if not project_tags and not tagged_items:
        print("\n暂无标签，使用 tag add 添加标签")
    
    print()


def _update_tags_file(work_dir, manifest):
    """更新 tags.txt 文件"""
    tags_path = os.path.join(work_dir, TAGS_FILE)
    
    all_tags = set(manifest.get('project_tags', []))
    for item_type in ['videos', 'images']:
        for item in manifest.get(item_type, []):
            all_tags.update(item.get('tags', []))
    
    with open(tags_path, 'w', encoding='utf-8') as f:
        for tag in sorted(all_tags):
            f.write(f"#{tag}\n")


def get_hashtag_string(work_dir):
    """生成 hashtag 字符串"""
    tags_path = os.path.join(work_dir, TAGS_FILE)
    if os.path.exists(tags_path):
        with open(tags_path, 'r', encoding='utf-8') as f:
            tags = [line.strip() for line in f if line.strip()]
        return ' '.join(tags)
    return ''
