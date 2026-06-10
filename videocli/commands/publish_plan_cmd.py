import os
from pathlib import Path
from datetime import datetime
from tabulate import tabulate

from ..utils import (
    load_json, save_json, log_operation, PROJECT_MANIFEST, CHECK_REPORT
)
from .check_cmd import PLATFORMS


PUBLISH_PLAN_DIR = 'publish_plans'


def generate_publish_plan(work_dir, platforms=None, export_format='both'):
    manifest_path = os.path.join(work_dir, PROJECT_MANIFEST)
    manifest = load_json(manifest_path)

    if not manifest:
        print("错误: 未找到项目清单，请先运行 scan 命令")
        return None

    if platforms is None:
        metadata = manifest.get('metadata', {})
        platforms = metadata.get('platforms', list(PLATFORMS.keys()))
    elif isinstance(platforms, str):
        platforms = [p.strip() for p in platforms.split(',') if p.strip()]

    check_report = None
    check_report_path = os.path.join(work_dir, CHECK_REPORT)
    if os.path.exists(check_report_path):
        check_report = load_json(check_report_path)

    plans_root = os.path.join(work_dir, PUBLISH_PLAN_DIR)
    Path(plans_root).mkdir(parents=True, exist_ok=True)

    all_plans = {}
    total_videos = len(manifest.get('videos', []))
    project_tags = manifest.get('project_tags', [])
    project_meta = manifest.get('metadata', {})

    for platform_key in platforms:
        platform = PLATFORMS.get(platform_key)
        if not platform:
            continue

        platform_plan = _build_platform_plan(
            work_dir, manifest, platform_key, platform,
            project_tags, project_meta, check_report
        )
        all_plans[platform_key] = platform_plan

    if not all_plans:
        print("错误: 没有有效的目标平台")
        return None

    summary = _print_plan_summary(all_plans)

    export_count = 0
    for platform_key, plan in all_plans.items():
        platform = PLATFORMS.get(platform_key, {})
        plan_dir = os.path.join(plans_root, platform_key)
        Path(plan_dir).mkdir(parents=True, exist_ok=True)

        if export_format in ('json', 'both'):
            json_path = os.path.join(plan_dir, f'{platform_key}_plan.json')
            save_json(plan, json_path)
            export_count += 1

        if export_format in ('md', 'both'):
            md_path = os.path.join(plan_dir, f'{platform_key}_plan.md')
            _export_plan_md(plan, md_path, platform)
            export_count += 1

    combined = {
        'generated_at': datetime.now().isoformat(),
        'platforms': list(all_plans.keys()),
        'project_title': project_meta.get('title', ''),
        'project_author': project_meta.get('author', ''),
        'plans': all_plans,
        'summary': summary,
    }

    combined_json = os.path.join(plans_root, 'all_plans.json')
    save_json(combined, combined_json)

    if export_format in ('md', 'both'):
        combined_md = os.path.join(plans_root, 'all_plans.md')
        _export_combined_md(combined, combined_md)

    log_operation(work_dir, 'publish_plan', {
        'platforms': list(all_plans.keys()),
        'export_format': export_format,
        'videos_count': total_videos,
    })

    print(f"\n✅ 发布计划已生成!")
    print(f"   平台: {', '.join(all_plans.keys())}")
    print(f"   导出格式: {export_format}")
    print(f"   保存目录: {plans_root}")

    return combined


def _build_platform_plan(work_dir, manifest, platform_key, platform,
                          project_tags, project_meta, check_report):
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
        video_tags = video.get('tags', []) + video_meta.get('tags', [])
        video_tags = list(dict.fromkeys(video_tags))

        cover_path = video.get('selected_cover', '')
        caption_files = []
        cap_info = captions_info.get(video_name, {})
        for cap_type in ['srt', 'vtt']:
            cap_file = cap_info.get(cap_type)
            if cap_file:
                caption_files.append(cap_file)

        status = platform_status.get(video_name, {})

        title = video_meta.get('title') or project_meta.get('title', '')
        copy_text = video_meta.get('copy') or video_meta.get('description') or project_meta.get('description', '')

        hashtag_str = ' '.join([f'#{t}' for t in video_tags]) if video_tags else ''
        if project_tags:
            project_hashtag = ' '.join([f'#{t}' for t in project_tags])
            if hashtag_str:
                hashtag_str = hashtag_str + ' ' + project_hashtag
            else:
                hashtag_str = project_hashtag

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
            todos.append({'item': f"时长不符合推荐范围", 'priority': 'medium',
                          'action': f"调整时长至 {platform['ideal_duration'][0]}-{platform['ideal_duration'][1]}秒"})
        if not status.get('ratio_ok', True):
            todos.append({'item': f"比例非最佳", 'priority': 'low',
                          'action': f"建议调整为 {platform['ideal_ratio']}"})

        plan_videos.append({
            'video_name': video_name,
            'video_path': video['path'],
            'title': title,
            'copy': copy_text,
            'hashtags': video_tags + [t for t in project_tags if t not in video_tags],
            'hashtag_str': hashtag_str,
            'cover_path': cover_path,
            'caption_files': caption_files,
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


def _print_plan_summary(all_plans):
    print("\n" + "=" * 70)
    print("  📋 发布计划总览")
    print("=" * 70)

    summary_data = []
    for platform_key, plan in all_plans.items():
        s = plan['summary']
        status = "✅ 可发布" if s['publishable'] else ("⚠️  需完善" if s['ready_videos'] > 0 else "❌ 未就绪")
        summary_data.append([
            plan['platform_name'],
            s['total_videos'],
            s['ready_videos'],
            s['platform_score'],
            status,
        ])

    print()
    print(tabulate(summary_data,
                   headers=['平台', '视频数', '就绪数', '评分', '状态'],
                   tablefmt='simple'))

    for platform_key, plan in all_plans.items():
        print(f"\n{'─' * 50}")
        print(f"  【{plan['platform_name']}】")
        for v in plan['videos']:
            status_icon = "✅" if v['ready'] else "⚠️"
            print(f"  {status_icon} {v['video_name']}")
            if v['title']:
                print(f"     标题: {v['title']}")
            if v['copy']:
                copy_display = v['copy'][:60] + '...' if len(v['copy']) > 60 else v['copy']
                print(f"     文案: {copy_display}")
            if v['todos']:
                for t in v['todos']:
                    print(f"     → {t['item']} ({t['action']})")

    return {
        'total_platforms': len(all_plans),
        'publishable_platforms': sum(1 for p in all_plans.values() if p['summary']['publishable']),
    }


def _export_plan_md(plan, md_path, platform):
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(f"# {plan['platform_name']} 发布计划\n\n")
        f.write(f"生成时间: {plan['generated_at'][:19].replace('T', ' ')}\n\n")

        f.write("## 平台要求\n\n")
        for key, val in plan['platform_requirements'].items():
            label_map = {
                'ideal_duration': '推荐时长',
                'ideal_ratio': '最佳比例',
                'max_duration': '最大时长',
                'max_file_size': '文件大小限制',
            }
            f.write(f"- {label_map.get(key, key)}: {val}\n")
        f.write("\n")

        s = plan['summary']
        status = "✅ 可发布" if s['publishable'] else "⚠️ 需完善"
        f.write(f"## 发布状态: {status} (评分: {s['platform_score']}/100)\n\n")

        for v in plan['videos']:
            f.write(f"---\n\n")
            f.write(f"## {v['video_name']}\n\n")
            f.write(f"- **标题**: {v['title'] or '（未设置）'}\n")
            f.write(f"- **文案**: {v['copy'] or '（未设置）'}\n")
            f.write(f"- **话题**: {v['hashtag_str'] or '（无）'}\n")
            f.write(f"- **封面**: {v['cover_path'] or '（未选择）'}\n")
            if v['caption_files']:
                f.write(f"- **字幕**: {', '.join(v['caption_files'])}\n")
            else:
                f.write("- **字幕**: （无）\n")
            f.write(f"- **时长**: {v['duration']}\n")
            f.write(f"- **比例**: {v['aspect_ratio']}\n")

            if v['todos']:
                f.write(f"\n### 待办事项\n\n")
                for t in v['todos']:
                    priority_icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(t['priority'], '⚪')
                    f.write(f"- {priority_icon} {t['item']} → `{t['action']}`\n")
                f.write("\n")


def _export_combined_md(combined, md_path):
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# 全平台发布计划\n\n")
        f.write(f"生成时间: {combined['generated_at'][:19].replace('T', ' ')}\n")
        if combined.get('project_title'):
            f.write(f"项目: {combined['project_title']}\n")
        if combined.get('project_author'):
            f.write(f"作者: {combined['project_author']}\n")
        f.write(f"平台: {', '.join(combined['platforms'])}\n\n")

        f.write("## 总览\n\n")
        s = combined.get('summary', {})
        f.write(f"- 目标平台数: {s.get('total_platforms', 0)}\n")
        f.write(f"- 可发布平台数: {s.get('publishable_platforms', 0)}\n\n")

        for platform_key, plan in combined.get('plans', {}).items():
            ps = plan['summary']
            status = "✅" if ps['publishable'] else "⚠️"
            f.write(f"- {status} {plan['platform_name']}: {ps['ready_videos']}/{ps['total_videos']} 就绪, 评分 {ps['platform_score']}\n")
        f.write("\n")

        for platform_key, plan in combined.get('plans', {}).items():
            f.write(f"---\n\n## {plan['platform_name']}\n\n")
            reqs = plan['platform_requirements']
            f.write(f"要求: 时长 {reqs['ideal_duration']}, 比例 {reqs['ideal_ratio']}\n\n")

            for v in plan['videos']:
                icon = "✅" if v['ready'] else "⚠️"
                f.write(f"### {icon} {v['video_name']}\n\n")
                f.write(f"| 项目 | 内容 |\n| --- | --- |\n")
                f.write(f"| 标题 | {v['title'] or '未设置'} |\n")
                copy_display = (v['copy'][:80] + '...') if v['copy'] and len(v['copy']) > 80 else (v['copy'] or '未设置')
                f.write(f"| 文案 | {copy_display} |\n")
                f.write(f"| 话题 | {v['hashtag_str'] or '无'} |\n")
                f.write(f"| 封面 | {v['cover_path'] or '未选择'} |\n")
                f.write(f"| 字幕 | {', '.join(v['caption_files']) if v['caption_files'] else '无'} |\n")
                f.write(f"| 时长 | {v['duration']} |\n")
                f.write(f"| 比例 | {v['aspect_ratio']} |\n\n")

                if v['todos']:
                    f.write(f"**待办:**\n")
                    for t in v['todos']:
                        f.write(f"- {t['item']} ({t['action']})\n")
                    f.write("\n")


def show_publish_plan(work_dir, platform=None):
    manifest_path = os.path.join(work_dir, PROJECT_MANIFEST)
    manifest = load_json(manifest_path)

    if not manifest:
        print("错误: 未找到项目清单")
        return

    plans_dir = os.path.join(work_dir, PUBLISH_PLAN_DIR)
    if not os.path.exists(plans_dir):
        print("尚未生成发布计划，请先运行 publish-plan generate")
        return

    all_json = os.path.join(plans_dir, 'all_plans.json')
    combined = load_json(all_json)
    if not combined:
        print("尚未生成发布计划，请先运行 publish-plan generate")
        return

    if platform:
        platform_key = platform
        if platform_key not in combined.get('plans', {}):
            for pk, pv in combined.get('plans', {}).items():
                if pv.get('platform_name') == platform:
                    platform_key = pk
                    break

        plan = combined.get('plans', {}).get(platform_key)
        if not plan:
            print(f"未找到平台 {platform} 的发布计划")
            return

        _print_single_plan_detail(plan)
    else:
        _print_plan_summary(combined.get('plans', {}))


def _print_single_plan_detail(plan):
    s = plan['summary']
    status = "✅ 可发布" if s['publishable'] else "⚠️ 需完善"

    print(f"\n{'=' * 60}")
    print(f"  {plan['platform_name']} 发布计划 - {status}")
    print(f"  评分: {s['platform_score']}/100")
    print(f"{'=' * 60}")

    print(f"\n📋 平台要求")
    print("-" * 40)
    for key, val in plan['platform_requirements'].items():
        label_map = {
            'ideal_duration': '推荐时长',
            'ideal_ratio': '最佳比例',
            'max_duration': '最大时长',
            'max_file_size': '文件大小限制',
        }
        print(f"  {label_map.get(key, key)}: {val}")

    for v in plan['videos']:
        print(f"\n🎬 {v['video_name']}")
        print("-" * 40)
        table_data = [
            ['标题', v['title'] or '未设置'],
            ['文案', (v['copy'][:50] + '...') if v['copy'] and len(v['copy']) > 50 else (v['copy'] or '未设置')],
            ['话题', v['hashtag_str'] or '无'],
            ['封面', v['cover_path'] or '未选择'],
            ['字幕', ', '.join(v['caption_files']) if v['caption_files'] else '无'],
            ['时长', v['duration']],
            ['比例', v['aspect_ratio']],
        ]
        print(tabulate(table_data, headers=['项目', '内容'], tablefmt='simple'))

        if v['todos']:
            print(f"\n  待办:")
            for t in v['todos']:
                icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(t['priority'], '⚪')
                print(f"    {icon} {t['item']} → {t['action']}")
