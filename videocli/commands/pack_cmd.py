import os
import shutil
from pathlib import Path
from datetime import datetime
from tabulate import tabulate

from ..utils import (
    load_json, save_json, log_operation, CHECK_REPORT,
    PROJECT_MANIFEST, TAGS_FILE, TODO_FILE, OPERATION_LOG, PACK_DIR
)
from .check_cmd import PLATFORMS


def pack_project(work_dir, output_name=None, platforms=None, overwrite=False):
    manifest_path = os.path.join(work_dir, PROJECT_MANIFEST)
    manifest = load_json(manifest_path)

    if not manifest:
        print("错误: 未找到项目清单，请先运行 scan 命令")
        return None

    if platforms is None:
        metadata = manifest.get('metadata', {})
        platforms = metadata.get('platforms', [])
    elif isinstance(platforms, str):
        platforms = [p.strip() for p in platforms.split(',') if p.strip()]

    if not output_name:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dir_name = os.path.basename(os.path.normpath(work_dir))
        output_name = f"{dir_name}_publish_{timestamp}"

    packs_root = os.path.join(work_dir, PACK_DIR)
    pack_dir = os.path.join(packs_root, output_name)

    if os.path.exists(pack_dir):
        if overwrite:
            print(f"⚠  已存在同名目录，正在覆盖: {output_name}")
            shutil.rmtree(pack_dir)
        else:
            original_name = output_name
            counter = 1
            while os.path.exists(os.path.join(packs_root, output_name)):
                output_name = f"{original_name}_v{counter}"
                counter += 1
            print(f"⚠  已存在同名目录 {original_name}，自动改名为: {output_name}")
            pack_dir = os.path.join(packs_root, output_name)

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

    check_report_src = os.path.join(work_dir, CHECK_REPORT)
    if os.path.exists(check_report_src):
        shutil.copy2(check_report_src, os.path.join(metadata_dir, 'check_report.json'))
        print("  ✓ 检查报告")

    _generate_publish_info(pack_dir, manifest, platforms)
    print("  ✓ 发布信息")

    check_report = load_json(check_report_src, None) if os.path.exists(check_report_src) else None
    _generate_todo_list(work_dir, pack_dir, manifest, platforms, check_report)
    print("  ✓ 待办列表")

    log_operation(work_dir, 'pack', {
        'output_name': output_name,
        'videos_count': len(packed['videos']),
        'covers_count': len(packed['covers'])
    })

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

    if platforms:
        print()
        for platform_key in platforms:
            platform = PLATFORMS.get(platform_key)
            if not platform:
                continue
            _pack_platform_subdir(pack_dir, work_dir, manifest, platform_key, platform, check_report)

    print(f"\n✅ 打包完成!")
    print(f"   目录: {pack_dir}")
    print(f"   视频: {len(packed['videos'])} 个")
    print(f"   封面: {len(packed['covers'])} 张已选")
    print(f"   字幕: {len(packed['captions'])} 个文件")
    if platforms:
        print(f"   平台子目录: {', '.join(platforms)}")

    return pack_dir


def _pack_platform_subdir(pack_dir, work_dir, manifest, platform_key, platform, check_report):
    platform_dir = os.path.join(pack_dir, platform_key)
    Path(platform_dir).mkdir(parents=True, exist_ok=True)

    project_tags = manifest.get('project_tags', [])
    project_meta = manifest.get('metadata', {})

    platform_status = {}
    if check_report:
        for vs in check_report.get('video_status_by_platform', {}).get(platform_key, []):
            platform_status[vs['video_name']] = vs

    videos_dir = os.path.join(platform_dir, 'videos')
    Path(videos_dir).mkdir(exist_ok=True)
    for video in manifest.get('videos', []):
        src = video['path']
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(videos_dir, video['name']))

    covers_dir = os.path.join(platform_dir, 'covers')
    Path(covers_dir).mkdir(exist_ok=True)
    for video in manifest.get('videos', []):
        selected_cover = video.get('selected_cover')
        if selected_cover and os.path.exists(selected_cover):
            dst = os.path.join(covers_dir, f"{Path(video['name']).stem}_cover{Path(selected_cover).suffix}")
            shutil.copy2(selected_cover, dst)

    captions_dir = os.path.join(platform_dir, 'captions')
    Path(captions_dir).mkdir(exist_ok=True)
    captions_info = manifest.get('captions', {})
    for video_name, info in captions_info.items():
        for cap_type in ['srt', 'vtt']:
            cap_file = info.get(cap_type)
            if cap_file and os.path.exists(cap_file):
                shutil.copy2(cap_file, os.path.join(captions_dir, os.path.basename(cap_file)))

    images_dir = os.path.join(platform_dir, 'images')
    Path(images_dir).mkdir(exist_ok=True)
    for img in manifest.get('images', []):
        src = img['path']
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(images_dir, img['name']))

    plan = _build_platform_plan(manifest, platform_key, platform, project_tags, project_meta, check_report, relative=True)
    plan_path = os.path.join(platform_dir, f'{platform_key}_plan.json')
    save_json(plan, plan_path)

    _write_platform_plan_md(plan, os.path.join(platform_dir, f'{platform_key}_plan.md'), platform)

    _write_platform_todo(plan, platform_dir, work_dir, platform_key)

    _write_platform_asset_list(plan, platform_dir, manifest)

    _write_platform_readme(plan, platform_dir, manifest)

    print(f"  ✓ 平台目录: {platform_key}/ ({platform['name']})")


def _build_platform_plan(manifest, platform_key, platform, project_tags, project_meta, check_report, relative=False):
    videos = manifest.get('videos', [])
    captions_info = manifest.get('captions', {})

    platform_status = {}
    if check_report:
        for vs in check_report.get('video_status_by_platform', {}).get(platform_key, []):
            platform_status[vs['video_name']] = vs

    plan_videos = []
    for video in videos:
        video_meta = video.get('metadata', {})
        video_name = video['name']

        video_tags_raw = video.get('tags', []) + video_meta.get('tags', [])
        video_tags = []
        seen_vtags = set()
        for t in video_tags_raw:
            if t not in seen_vtags:
                seen_vtags.add(t)
                video_tags.append(t)

        cover_path = video.get('selected_cover', '')
        cover_rel = ''
        if cover_path:
            if relative:
                cover_ext = Path(cover_path).suffix
                cover_rel = f"covers/{Path(video_name).stem}_cover{cover_ext}"
            else:
                cover_rel = cover_path

        caption_files = []
        caption_rel = []
        cap_info = captions_info.get(video_name, {})
        for cap_type in ['srt', 'vtt']:
            cap_file = cap_info.get(cap_type)
            if cap_file:
                caption_files.append(cap_file)
                if relative:
                    caption_rel.append(f"captions/{os.path.basename(cap_file)}")
                else:
                    caption_rel.append(cap_file)

        status = platform_status.get(video_name, {})

        title = video_meta.get('title') or project_meta.get('title', '')
        copy_text = video_meta.get('copy') or video_meta.get('description') or project_meta.get('description', '')

        unique_tags = []
        seen_hash = set()
        for t in video_tags:
            if t not in seen_hash:
                seen_hash.add(t)
                unique_tags.append(t)
        for t in project_tags:
            if t not in seen_hash:
                seen_hash.add(t)
                unique_tags.append(t)

        hashtag_str = ' '.join([f'#{t}' for t in unique_tags]) if unique_tags else ''

        todos = []
        if not status.get('has_cover', bool(cover_path)):
            todos.append({'item': '未选择封面', 'priority': 'high', 'action': 'cover select'})
        if not status.get('has_title', bool(title)):
            todos.append({'item': '缺少标题', 'priority': 'high', 'action': 'metadata set-video --title'})
        if not status.get('has_description', bool(copy_text)):
            todos.append({'item': '缺少文案描述', 'priority': 'medium', 'action': 'metadata set-video --copy'})
        if not status.get('has_caption', bool(caption_files)):
            todos.append({'item': '缺少字幕', 'priority': 'medium', 'action': 'caption generate'})
        if not status.get('duration_ok', True):
            todos.append({'item': '时长不在推荐范围', 'priority': 'medium',
                          'action': f"调整至 {platform['ideal_duration'][0]}-{platform['ideal_duration'][1]}秒"})
        if not status.get('ratio_ok', True):
            todos.append({'item': '比例非最佳', 'priority': 'low',
                          'action': f"建议调整为 {platform['ideal_ratio']}"})

        video_rel = f"videos/{video_name}" if relative else video['path']

        plan_videos.append({
            'video_name': video_name,
            'video_path': video_rel,
            'title': title,
            'copy': copy_text,
            'hashtags': unique_tags,
            'hashtag_str': hashtag_str,
            'cover_path': cover_rel,
            'caption_files': caption_rel,
            'duration': video.get('duration_formatted', status.get('duration', '未知')),
            'aspect_ratio': status.get('aspect_ratio', '未知'),
            'todos': todos,
            'ready': len(todos) == 0,
        })

    ready_count = sum(1 for v in plan_videos if v['ready'])
    platform_score = 100
    critical_missing = 0
    for v in plan_videos:
        for t in v['todos']:
            if t['priority'] == 'high':
                platform_score -= 15
                critical_missing += 1
            elif t['priority'] == 'medium':
                platform_score -= 8
            else:
                platform_score -= 3
    platform_score = max(0, platform_score)

    return {
        'platform_key': platform_key,
        'platform_name': platform['name'],
        'generated_at': datetime.now().isoformat(),
        'platform_requirements': {
            'ideal_duration': f"{platform['ideal_duration'][0]}-{platform['ideal_duration'][1]}秒",
            'ideal_ratio': platform['ideal_ratio'],
            'max_duration': f"{platform['max_duration']}秒" if platform['max_duration'] else '无限制',
            'max_file_size': f"{platform['max_file_size_mb']}MB",
        },
        'videos': plan_videos,
        'summary': {
            'total_videos': len(plan_videos),
            'ready_videos': ready_count,
            'platform_score': platform_score,
            'critical_missing': critical_missing,
            'publishable': ready_count == len(plan_videos) and len(plan_videos) > 0,
        },
    }


def _write_platform_plan_md(plan, md_path, platform):
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(f"# {plan['platform_name']} 发布计划\n\n")
        f.write(f"生成时间: {plan['generated_at'][:19].replace('T', ' ')}\n\n")

        f.write("## 平台要求\n\n")
        label_map = {
            'ideal_duration': '推荐时长',
            'ideal_ratio': '最佳比例',
            'max_duration': '最大时长',
            'max_file_size': '文件大小限制',
        }
        for key, val in plan['platform_requirements'].items():
            f.write(f"- {label_map.get(key, key)}: {val}\n")
        f.write("\n")

        s = plan['summary']
        status = "✅ 可发布" if s['publishable'] else "⚠️ 需完善"
        f.write(f"## 发布状态: {status} (评分: {s['platform_score']}/100)\n\n")

        for v in plan['videos']:
            f.write(f"---\n\n## {v['video_name']}\n\n")
            f.write(f"- **标题**: {v['title'] or '（未设置）'}\n")
            f.write(f"- **文案**: {v['copy'] or '（未设置）'}\n")
            f.write(f"- **话题**: {v['hashtag_str'] or '（无）'}\n")
            f.write(f"- **封面**: {v['cover_path'] or '（未选择）'}\n")
            if v['caption_files']:
                f.write(f"- **字幕**: {', '.join(v['caption_files'])}\n")
            else:
                f.write("- **字幕**: （无）\n")
            f.write(f"- **视频文件**: {v['video_path']}\n")
            f.write(f"- **时长**: {v['duration']}\n")
            f.write(f"- **比例**: {v['aspect_ratio']}\n")

            if v['todos']:
                f.write(f"\n### 待办事项\n\n")
                for t in v['todos']:
                    priority_icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(t['priority'], '⚪')
                    f.write(f"- {priority_icon} {t['item']} → `{t['action']}`\n")
                f.write("\n")


def _write_platform_readme(plan, platform_dir, manifest):
    readme_path = os.path.join(platform_dir, 'README.md')
    s = plan['summary']
    status = "✅ 可发布" if s['publishable'] else "⚠️ 需完善"
    project_meta = manifest.get('metadata', {})

    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(f"# {plan['platform_name']} 发布交接文档\n\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        if project_meta.get('title'):
            f.write(f"**项目**: {project_meta['title']}\n\n")
        if project_meta.get('author'):
            f.write(f"**作者**: {project_meta['author']}\n\n")
        if project_meta.get('notes'):
            f.write(f"**备注**: {project_meta['notes']}\n\n")

        f.write("---\n\n")
        f.write("## 📊 状态总览\n\n")
        f.write(f"- **发布状态**: {status}  (评分 {s['platform_score']}/100)\n")
        f.write(f"- **视频总数**: {s['total_videos']}\n")
        f.write(f"- **就绪视频**: {s['ready_videos']}/{s['total_videos']}\n")
        f.write(f"- **高优先级缺失**: {s['critical_missing']}\n\n")

        f.write("---\n\n")
        f.write("## 📋 交付内容\n\n")
        f.write("### 文件结构\n\n")
        f.write("```\n")
        f.write(f"{plan['platform_key']}/\n")
        f.write("├── videos/           # 视频素材\n")
        f.write("├── covers/           # 封面图\n")
        f.write("├── captions/         # 字幕文件\n")
        f.write("├── images/           # 配图素材\n")
        f.write(f"├── {plan['platform_key']}_plan.md    # 发布计划（详细）\n")
        f.write(f"├── {plan['platform_key']}_plan.json  # 发布计划（机器可读）\n")
        f.write("├── todo_list.md      # 待办事项\n")
        f.write("├── asset_list.md     # 素材清单\n")
        f.write("└── README.md         # 本文档\n")
        f.write("```\n\n")

        f.write("---\n\n")
        f.write("## 🎬 视频发布清单\n\n")
        for i, v in enumerate(plan['videos'], 1):
            icon = "✅" if v['ready'] else "⚠️"
            f.write(f"### {i}. {icon} {v['video_name']}\n\n")
            f.write(f"- **标题**: {v['title'] or '（待填写）'}\n")
            copy_display = (v['copy'][:100] + '...') if v['copy'] and len(v['copy']) > 100 else (v['copy'] or '（待编写）')
            f.write(f"- **文案**: {copy_display}\n")
            f.write(f"- **话题**: {v['hashtag_str'] or '（待添加）'}\n")
            f.write(f"- **素材位置**: `{v['video_path']}`\n")
            if v['cover_path']:
                f.write(f"- **封面**: `{v['cover_path']}`\n")
            else:
                f.write(f"- **封面**: （待选择）\n")
            if v['caption_files']:
                f.write(f"- **字幕**: {', '.join('`'+c+'`' for c in v['caption_files'])}\n")
            f.write(f"- **时长**: {v['duration']}  |  **比例**: {v['aspect_ratio']}\n")

            if v['todos']:
                f.write(f"\n  **待完成**:\n")
                for t in v['todos']:
                    icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(t['priority'], '⚪')
                    f.write(f"  - {icon} {t['item']}\n")
            f.write("\n")

        f.write("---\n\n")
        f.write("## 💡 发布说明\n\n")
        reqs = plan['platform_requirements']
        f.write(f"- **推荐时长**: {reqs['ideal_duration']}\n")
        f.write(f"- **最佳比例**: {reqs['ideal_ratio']}\n")
        f.write(f"- **最大时长**: {reqs['max_duration']}\n")
        f.write(f"- **文件大小上限**: {reqs['max_file_size']}\n\n")
        f.write("发布前请确保所有待办事项已处理完成。\n")


def _write_platform_asset_list(plan, platform_dir, manifest):
    list_path = os.path.join(platform_dir, 'asset_list.md')

    with open(list_path, 'w', encoding='utf-8') as f:
        f.write(f"# {plan['platform_name']} 素材清单\n\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        for v in plan['videos']:
            f.write(f"## {v['video_name']}\n\n")
            f.write(f"| 类型 | 文件 |\n| --- | --- |\n")
            f.write(f"| 视频 | {v['video_path']} |\n")
            if v['cover_path']:
                f.write(f"| 封面 | {v['cover_path']} |\n")
            for cap_file in v['caption_files']:
                f.write(f"| 字幕 | {cap_file} |\n")
            f.write("\n")

        images = manifest.get('images', [])
        if images:
            f.write("## 图片素材\n\n")
            for img in images:
                f.write(f"- images/{img['name']}\n")
            f.write("\n")


def _write_platform_todo(plan, platform_dir, work_dir, platform_key):
    todo_path = os.path.join(platform_dir, 'todo_list.md')

    all_todos = []
    for v in plan['videos']:
        for t in v['todos']:
            all_todos.append((t['priority'], f"[{v['video_name']}] {t['item']}", t['action']))

    seen = set()
    unique_todos = []
    for priority, title, desc in all_todos:
        key = (priority, title)
        if key not in seen:
            seen.add(key)
            unique_todos.append((priority, title, desc))

    unique_todos.append(('low', '检查视频质量', '确认视频画质、音质、画面稳定性'))
    unique_todos.append(('low', '预览最终效果', '完整观看一遍确认无误'))

    with open(todo_path, 'w', encoding='utf-8') as f:
        f.write(f"# {plan['platform_name']} 发布前待办\n\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        priority_order = {'high': '🔴 高优先级', 'medium': '🟡 中优先级', 'low': '🟢 低优先级'}
        for priority in ['high', 'medium', 'low']:
            priority_todos = [(t, d) for (p, t, d) in unique_todos if p == priority]
            if priority_todos:
                f.write(f"## {priority_order[priority]}\n\n")
                for title, desc in priority_todos:
                    f.write(f"- [ ] {title}\n")
                    f.write(f"  → {desc}\n")
                f.write("\n")


def _generate_publish_info(pack_dir, manifest, platforms=None):
    info_path = os.path.join(pack_dir, '05_metadata', 'publish_info.md')

    project_tags = manifest.get('project_tags', [])
    hashtag_str = ' '.join([f'#{tag}' for tag in project_tags])

    metadata = manifest.get('metadata', {})

    with open(info_path, 'w', encoding='utf-8') as f:
        f.write("# 发布信息\n\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## 项目信息\n\n")
        f.write(f"- 项目目录: {manifest.get('work_directory', '')}\n")
        if metadata.get('title'):
            f.write(f"- 项目标题: {metadata['title']}\n")
        if metadata.get('author'):
            f.write(f"- 作者: {metadata['author']}\n")
        f.write(f"- 视频数量: {len(manifest.get('videos', []))}\n")
        f.write(f"- 图片数量: {len(manifest.get('images', []))}\n\n")

        f.write("## 话题标签\n\n")
        if hashtag_str:
            f.write(f"{hashtag_str}\n\n")
        else:
            f.write("（暂无标签）\n\n")

        f.write("## 视频详情\n\n")
        for i, video in enumerate(manifest.get('videos', []), 1):
            video_meta = video.get('metadata', {})
            f.write(f"### 视频 {i}: {video['name']}\n\n")
            if video_meta.get('title'):
                f.write(f"- 标题: {video_meta['title']}\n")
            f.write(f"- 时长: {video.get('duration_formatted', 'N/A')}\n")
            f.write(f"- 分辨率: {video.get('width', '?')}x{video.get('height', '?')}\n")
            f.write(f"- 文件大小: {video.get('size_mb', '?')} MB\n")
            f.write(f"- 标签: {', '.join(video.get('tags', [])) or '无'}\n")
            f.write(f"- 封面: {os.path.basename(video.get('selected_cover', '')) or '未选择'}\n")
            if video_meta.get('description') or video_meta.get('copy'):
                f.write(f"- 文案: {video_meta.get('description') or video_meta.get('copy')}\n")
            f.write("\n")

        if platforms:
            f.write("## 平台发布提示\n\n")
            for platform_key in platforms:
                platform = PLATFORMS.get(platform_key)
                if platform:
                    f.write(f"### {platform['name']}\n\n")
                    f.write(f"- 推荐时长: {platform['ideal_duration'][0]}-{platform['ideal_duration'][1]} 秒\n")
                    f.write(f"- 最佳比例: {platform['ideal_ratio']}\n")
                    f.write(f"- 最大文件: {platform['max_file_size_mb']} MB\n\n")


def _generate_todo_list(work_dir, pack_dir, manifest, platforms=None, check_report=None):
    todo_path = os.path.join(pack_dir, '05_metadata', TODO_FILE)

    todos = []

    metadata = manifest.get('metadata', {})

    if check_report:
        for error in check_report.get('errors', []):
            todos.append(('high', error, '需要立即修复的问题'))

        for warning in check_report.get('warnings', []):
            todos.append(('medium', warning, '建议处理的问题'))

        video_status_by_platform = check_report.get('video_status_by_platform', {})
        for platform_key, video_statuses in video_status_by_platform.items():
            platform = PLATFORMS.get(platform_key, {})
            platform_name = platform.get('name', platform_key)
            for status in video_statuses:
                if not status.get('has_title'):
                    todos.append(('high',
                        f"[{platform_name}] {status['video_name']} 缺少标题",
                        "请使用 metadata set-video 设置视频标题"
                    ))
                if not status.get('has_description'):
                    todos.append(('medium',
                        f"[{platform_name}] {status['video_name']} 缺少描述文案",
                        "请使用 metadata set-video 设置视频描述或文案"
                    ))
                if not status.get('has_cover'):
                    todos.append(('high',
                        f"[{platform_name}] {status['video_name']} 未选择封面",
                        "请使用 cover select 选择视频封面"
                    ))
                if not status.get('has_caption'):
                    todos.append(('medium',
                        f"[{platform_name}] {status['video_name']} 缺少字幕",
                        "请使用 caption generate 生成字幕草稿"
                    ))
                if not status.get('duration_ok'):
                    todos.append(('medium',
                        f"[{platform_name}] {status['video_name']} 时长 ({status['duration']}) 不在推荐范围",
                        f"请调整时长至符合 {platform_name} 要求"
                    ))
                if not status.get('ratio_ok'):
                    todos.append(('medium',
                        f"[{platform_name}] {status['video_name']} 比例 ({status['aspect_ratio']}) 不是最佳比例",
                        f"建议调整为 {platform.get('ideal_ratio', '推荐比例')}"
                    ))
    else:
        if not metadata.get('title'):
            todos.append(('high', '设置项目标题', '为项目设置吸引人的标题'))

        if not metadata.get('description'):
            todos.append(('high', '编写项目描述', '撰写项目简介和描述文案'))

        if not manifest.get('project_tags', []):
            todos.append(('high', '添加话题标签', '添加相关话题标签以增加曝光'))

        selected_covers_count = sum(1 for v in manifest.get('videos', []) if v.get('selected_cover'))
        total_videos = len(manifest.get('videos', []))
        if selected_covers_count < total_videos:
            todos.append(('medium', '选择封面图', f'已选 {selected_covers_count}/{total_videos} 个视频选择了封面'))

        captions_count = len(manifest.get('captions', {}))
        if captions_count < total_videos:
            todos.append(('medium', '完善字幕', f'已生成 {captions_count}/{total_videos} 个视频字幕草稿'))

        for video in manifest.get('videos', []):
            video_meta = video.get('metadata', {})
            if not video_meta.get('title'):
                todos.append(('high', f"{video['name']} 缺少标题", "请使用 metadata set-video 设置视频标题"))
            if not video_meta.get('description') and not video_meta.get('copy'):
                todos.append(('medium', f"{video['name']} 缺少描述文案", "请使用 metadata set-video 设置视频描述或文案"))

    todos = _deduplicate_todos(todos)

    todos.append(('low', '检查视频质量', '确认视频画质、音质、画面稳定性'))
    todos.append(('low', '预览最终效果', '完整观看一遍确认无误'))

    if platforms:
        todos.append(('medium', '适配各平台', f'根据 {len(platforms)} 个平台要求调整内容'))

    with open(todo_path, 'w', encoding='utf-8') as f:
        f.write("# 发布前待办列表\n\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        if check_report:
            f.write(f"> 基于检查报告生成 (check_report.json)\n\n")

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
            op_log = load_json(op_log_path, [])
            for entry in reversed(op_log[-10:]):
                ts = entry.get('timestamp', '')
                op = entry.get('operation', '')
                details = entry.get('details', {})
                detail_str = ''
                if details.get('output_name'):
                    detail_str = f" ({details['output_name']})"
                elif details.get('tags'):
                    detail_str = f" ({', '.join(details['tags'])})"
                f.write(f"- {ts}: {op}{detail_str}\n")

    return todos


def _deduplicate_todos(todos):
    seen = set()
    unique = []
    for priority, title, desc in todos:
        key = (priority, title)
        if key not in seen:
            seen.add(key)
            unique.append((priority, title, desc))
    return unique


def list_packs(work_dir):
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
