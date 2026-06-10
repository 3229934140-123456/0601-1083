import os
from pathlib import Path
from datetime import datetime
from tabulate import tabulate

from ..utils import load_json, save_json, log_operation, PROJECT_MANIFEST, CHECK_REPORT, PUBLISH_PLAN_DIR
from .check_cmd import PLATFORMS


def compare_platforms(work_dir, video_filter=None, platforms=None, export_format=None):
    manifest_path = os.path.join(work_dir, PROJECT_MANIFEST)
    manifest = load_json(manifest_path)

    if not manifest:
        print("错误: 未找到项目清单，请先运行 scan 命令")
        return None

    all_videos = manifest.get('videos', [])
    captions_info = manifest.get('captions', {})
    project_tags = manifest.get('project_tags', [])
    project_meta = manifest.get('metadata', {})

    if platforms is None:
        metadata = manifest.get('metadata', {})
        platforms = metadata.get('platforms', list(PLATFORMS.keys()))
    elif isinstance(platforms, str):
        platforms = [p.strip() for p in platforms.split(',') if p.strip()]

    if not platforms:
        platforms = list(PLATFORMS.keys())

    valid_platforms = [p for p in platforms if p in PLATFORMS]
    if not valid_platforms:
        print(f"错误: 没有有效的平台，可选: {', '.join(PLATFORMS.keys())}")
        return None

    check_report = None
    check_report_path = os.path.join(work_dir, CHECK_REPORT)
    if os.path.exists(check_report_path):
        check_report = load_json(check_report_path)

    if video_filter:
        videos = [v for v in all_videos if
                  video_filter.lower() in v['name'].lower()
                  or video_filter.lower() in Path(v['path']).stem.lower()]
        if not videos:
            print(f"错误: 未找到匹配 '{video_filter}' 的视频")
            return None
    else:
        videos = all_videos

    if not videos:
        print("错误: 没有视频可以对比")
        return None

    print(f"\n🔍 跨平台发布对比视图")
    print("=" * 120)

    results = []
    for video in videos:
        video_result = {
            'video_name': video['name'],
            'platforms': {}
        }

        video_meta = video.get('metadata', {})
        video_tags_raw = video.get('tags', []) + video_meta.get('tags', [])
        video_tags = list(dict.fromkeys(video_tags_raw))
        all_tags = list(dict.fromkeys(video_tags + [t for t in project_tags if t not in video_tags]))
        hashtag_str = ' '.join([f'#{t}' for t in all_tags]) if all_tags else ''
        cover_path = video.get('selected_cover', '')

        caption_files = []
        cap_info = captions_info.get(video['name'], {})
        for cap_type in ['srt', 'vtt']:
            cap_file = cap_info.get(cap_type)
            if cap_file:
                caption_files.append(cap_file)

        for platform_key in valid_platforms:
            platform = PLATFORMS[platform_key]
            platform_status = {}

            if check_report:
                for vs in check_report.get('video_status_by_platform', {}).get(platform_key, []):
                    if vs['video_name'] == video['name']:
                        platform_status = vs
                        break

            platform_title = video_meta.get(f'title_{platform_key}') or video_meta.get('title') or project_meta.get('title', '')
            platform_copy = video_meta.get(f'copy_{platform_key}') or video_meta.get('copy') or video_meta.get('description') or project_meta.get('description', '')
            platform_tags = video_meta.get(f'tags_{platform_key}') or all_tags
            platform_hashtag = ' '.join([f'#{t}' for t in platform_tags]) if platform_tags else ''

            todos = []
            if not platform_status.get('has_title', bool(platform_title)):
                todos.append('标题')
            if not platform_status.get('has_description', bool(platform_copy)):
                todos.append('文案')
            if not platform_status.get('has_cover', bool(cover_path)):
                todos.append('封面')
            if not platform_status.get('has_caption', bool(caption_files)):
                todos.append('字幕')
            if not platform_status.get('duration_ok', True):
                todos.append('时长')
            if not platform_status.get('ratio_ok', True):
                todos.append('比例')

            ready = len(todos) == 0
            priority = '🔴' if any(t in todos for t in ['封面', '标题']) else (
                '🟡' if any(t in todos for t in ['字幕', '文案', '时长']) else (
                    '🟢' if '比例' in todos else '✅'
                )
            )

            if not platform_title:
                platform_title_display = '（未设置）'
            else:
                platform_title_display = platform_title[:18] + ('...' if len(platform_title) > 18 else '')

            if not platform_copy:
                copy_display = '（未设置）'
            else:
                copy_display = platform_copy[:20] + ('...' if len(platform_copy) > 20 else '')

            video_result['platforms'][platform_key] = {
                'platform_name': platform['name'],
                'ideal_duration': f"{platform['ideal_duration'][0]}-{platform['ideal_duration'][1]}s",
                'ideal_ratio': platform['ideal_ratio'],
                'title': platform_title_display,
                'copy': copy_display,
                'hashtag_str': platform_hashtag,
                'cover': os.path.basename(cover_path) if cover_path else '（未选）',
                'captions': len(caption_files),
                'duration': video.get('duration_formatted', platform_status.get('duration', '?')),
                'aspect_ratio': platform_status.get('aspect_ratio', '?'),
                'missing': ', '.join(todos) if todos else '—',
                'priority_icon': priority,
                'ready': ready,
            }

        results.append(video_result)

    for video_result in results:
        _print_video_comparison_table(video_result)

    _print_summary_table(results, valid_platforms)

    if export_format in ('json', 'md', 'both'):
        export_dir = os.path.join(work_dir, PUBLISH_PLAN_DIR)
        Path(export_dir).mkdir(parents=True, exist_ok=True)
        exported = _export_comparison(results, valid_platforms, export_dir, export_format)
        print(f"\n📁 对比结果已导出: {exported}")

    log_operation(work_dir, 'compare_platforms', {
        'platforms': valid_platforms,
        'videos': len(results),
        'export_format': export_format,
    })

    return results


def _print_video_comparison_table(video_result):
    video_name = video_result['video_name']
    platforms = video_result['platforms']

    print(f"\n🎬 {video_name}")
    print("-" * 120)

    headers = ['项目'] + [p['platform_name'] for p in platforms.values()]
    first_p = list(platforms.values())[0]

    rows = [
        ['推荐时长'] + [p['ideal_duration'] for p in platforms.values()],
        ['最佳比例'] + [p['ideal_ratio'] for p in platforms.values()],
        ['实际时长'] + [p['duration'] for p in platforms.values()],
        ['实际比例'] + [p['aspect_ratio'] for p in platforms.values()],
        ['标题'] + [p['title'] for p in platforms.values()],
        ['文案'] + [p['copy'] for p in platforms.values()],
        ['封面'] + [p['cover'] for p in platforms.values()],
        ['字幕数'] + [str(p['captions']) for p in platforms.values()],
        ['缺项'] + [p['missing'] for p in platforms.values()],
        ['状态'] + [p['priority_icon'] for p in platforms.values()],
    ]

    print(tabulate(rows, headers=headers, tablefmt='simple', maxcolwidths=[10, 20, 20, 20, 20]))


def _print_summary_table(results, platform_keys):
    print(f"\n📊 发布优先级总览")
    print("=" * 100)

    headers = ['视频'] + [PLATFORMS[k]['name'] for k in platform_keys] + ['推荐优先']
    rows = []

    for video_result in results:
        name = video_result['video_name']
        platform_scores = []
        for pk in platform_keys:
            p = video_result['platforms'][pk]
            if p['ready']:
                platform_scores.append('✅')
            else:
                platform_scores.append(p['priority_icon'])

        priority_rank = []
        for i, pk in enumerate(platform_keys):
            p = video_result['platforms'][pk]
            rank_value = 0
            if p['ready']:
                rank_value = 100
            else:
                if '封面' in p['missing']: rank_value -= 40
                if '标题' in p['missing']: rank_value -= 30
                if '文案' in p['missing']: rank_value -= 10
                if '字幕' in p['missing']: rank_value -= 10
                if '时长' in p['missing']: rank_value -= 8
                if '比例' in p['missing']: rank_value -= 2
            priority_rank.append((rank_value, PLATFORMS[pk]['name']))

        priority_rank.sort(reverse=True)
        best_platforms = [name for _, name in priority_rank[:2]]

        rows.append([name] + platform_scores + [' > '.join(best_platforms)])

    print(tabulate(rows, headers=headers, tablefmt='simple'))
    print("\n✅ 可直接发布   🔴 高优先级缺项   🟡 中优先级缺项   🟢 低优先级缺项")


def _export_comparison(results, platform_keys, export_dir, export_format):
    exported_files = []
    data = {
        'generated_at': datetime.now().isoformat(),
        'videos': [],
    }

    for video_result in results:
        video_row = {
            'video_name': video_result['video_name'],
            'platforms': video_result['platforms'],
        }
        data['videos'].append(video_row)

    if export_format in ('json', 'both'):
        json_path = os.path.join(export_dir, 'platform_comparison.json')
        save_json(data, json_path)
        exported_files.append(json_path)

    if export_format in ('md', 'both'):
        md_path = os.path.join(export_dir, 'platform_comparison.md')
        _write_comparison_md(data, platform_keys, md_path)
        exported_files.append(md_path)

    return ', '.join(os.path.basename(f) for f in exported_files)


def _write_comparison_md(data, platform_keys, md_path):
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# 跨平台发布对比\n\n")
        f.write(f"生成时间: {data['generated_at'][:19].replace('T', ' ')}\n\n")

        for video_row in data['videos']:
            f.write(f"## {video_row['video_name']}\n\n")
            headers = ['项目'] + [PLATFORMS[k]['name'] for k in platform_keys]
            platforms = video_row['platforms']

            if not platforms:
                continue

            rows = []
            first_pk = list(platforms.keys())[0]
            first_p = platforms[first_pk]
            fields = [
                ('推荐时长', 'ideal_duration'),
                ('最佳比例', 'ideal_ratio'),
                ('实际时长', 'duration'),
                ('实际比例', 'aspect_ratio'),
                ('标题', 'title'),
                ('文案', 'copy'),
                ('封面', 'cover'),
                ('字幕数', 'captions'),
                ('缺项', 'missing'),
                ('状态', 'priority_icon'),
            ]
            for label, key in fields:
                row = [label]
                for pk in platform_keys:
                    if pk in platforms:
                        val = platforms[pk].get(key, '')
                        row.append(str(val))
                    else:
                        row.append('—')
                rows.append(row)

            f.write(tabulate(rows, headers=headers, tablefmt='pipe'))
            f.write("\n\n")

        f.write("---\n\n")
        f.write("## 推荐发布顺序\n\n")

        for video_row in data['videos']:
            f.write(f"### {video_row['video_name']}\n\n")
            rank_list = []
            platforms = video_row['platforms']
            for pk in platform_keys:
                if pk not in platforms:
                    continue
                p = platforms[pk]
                rank_value = 0
                if p['ready']:
                    rank_value = 100
                else:
                    missing = p.get('missing', '')
                    if missing != '—':
                        if '封面' in missing: rank_value -= 40
                        if '标题' in missing: rank_value -= 30
                        if '文案' in missing: rank_value -= 10
                        if '字幕' in missing: rank_value -= 10
                        if '时长' in missing: rank_value -= 8
                        if '比例' in missing: rank_value -= 2
                rank_list.append((rank_value, pk, PLATFORMS[pk]['name']))

            rank_list.sort(reverse=True)
            for i, (_, pk, name) in enumerate(rank_list, 1):
                p = platforms.get(pk, {})
                icon = '✅' if p.get('ready') else p.get('priority_icon', '')
                missing = p.get('missing', '')
                if missing and missing != '—':
                    f.write(f"{i}. **{name}** {icon} (缺: {missing})\n")
                else:
                    f.write(f"{i}. **{name}** {icon}\n")
            f.write("\n")
