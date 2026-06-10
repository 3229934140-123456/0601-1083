import os
import shutil
import json
from pathlib import Path
from datetime import datetime
from tabulate import tabulate

from ..utils import (
    load_json, save_json, log_operation, PROJECT_MANIFEST,
    CHECK_REPORT, PACK_DIR, PUBLISH_PLAN_DIR
)
from .check_cmd import PLATFORMS
from .pack_cmd import (
    _build_platform_plan,
    _write_platform_plan_md,
    _write_platform_todo,
    _write_platform_asset_list,
    _write_platform_readme,
)


def export_handoff(work_dir, platform_key, output_dir=None, overwrite=False):
    manifest_path = os.path.join(work_dir, PROJECT_MANIFEST)
    manifest = load_json(manifest_path)

    if not manifest:
        print("错误: 未找到项目清单，请先运行 scan 命令")
        return None

    platform = PLATFORMS.get(platform_key)
    if not platform:
        valid = ', '.join(PLATFORMS.keys())
        print(f"错误: 无效的平台 '{platform_key}'，可选: {valid}")
        return None

    if not output_dir:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = f"{platform_key}_handoff_{timestamp}"

    export_root = os.path.join(work_dir, PACK_DIR)
    target_dir = os.path.join(export_root, output_dir)

    if os.path.exists(target_dir):
        if overwrite:
            print(f"⚠  已存在同名目录，正在覆盖: {output_dir}")
            shutil.rmtree(target_dir)
        else:
            original = output_dir
            counter = 1
            while os.path.exists(os.path.join(export_root, output_dir)):
                output_dir = f"{original}_v{counter}"
                counter += 1
            print(f"⚠  已存在同名目录 {original}，自动改名为: {output_dir}")
            target_dir = os.path.join(export_root, output_dir)

    Path(target_dir).mkdir(parents=True, exist_ok=True)

    print(f"\n📤 生成【{platform['name']}】可交付包: {output_dir}")
    print("-" * 60)

    videos_dir = os.path.join(target_dir, 'videos')
    Path(videos_dir).mkdir(exist_ok=True)
    video_count = 0
    for video in manifest.get('videos', []):
        src = video['path']
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(videos_dir, video['name']))
            video_count += 1
    print(f"  ✓ 视频素材: {video_count} 个")

    covers_dir = os.path.join(target_dir, 'covers')
    Path(covers_dir).mkdir(exist_ok=True)
    cover_count = 0
    for video in manifest.get('videos', []):
        selected_cover = video.get('selected_cover')
        if selected_cover and os.path.exists(selected_cover):
            ext = Path(selected_cover).suffix
            dst = os.path.join(covers_dir, f"{Path(video['name']).stem}_cover{ext}")
            shutil.copy2(selected_cover, dst)
            cover_count += 1
    print(f"  ✓ 封面素材: {cover_count} 个")

    captions_dir = os.path.join(target_dir, 'captions')
    Path(captions_dir).mkdir(exist_ok=True)
    caption_count = 0
    captions_info = manifest.get('captions', {})
    for video_name, info in captions_info.items():
        for cap_type in ['srt', 'vtt']:
            cap_file = info.get(cap_type)
            if cap_file and os.path.exists(cap_file):
                shutil.copy2(cap_file, os.path.join(captions_dir, os.path.basename(cap_file)))
                caption_count += 1
    print(f"  ✓ 字幕文件: {caption_count} 个")

    images_dir = os.path.join(target_dir, 'images')
    Path(images_dir).mkdir(exist_ok=True)
    image_count = 0
    for img in manifest.get('images', []):
        src = img['path']
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(images_dir, img['name']))
            image_count += 1
    if image_count:
        print(f"  ✓ 图片素材: {image_count} 张")

    metadata_dir = os.path.join(target_dir, 'metadata')
    Path(metadata_dir).mkdir(exist_ok=True)

    shutil.copy2(manifest_path, os.path.join(metadata_dir, 'project_manifest.json'))
    print("  ✓ 项目清单")

    check_report_src = os.path.join(work_dir, CHECK_REPORT)
    if os.path.exists(check_report_src):
        shutil.copy2(check_report_src, os.path.join(metadata_dir, 'check_report.json'))
        print("  ✓ 检查报告")

    from ..utils import OPERATION_LOG, TODO_STATE_FILE
    op_log_src = os.path.join(work_dir, OPERATION_LOG)
    if os.path.exists(op_log_src):
        op_log = load_json(op_log_src, [])
        recent_ops = op_log[-50:]
        summary_path = os.path.join(metadata_dir, 'operation_summary.md')
        _write_operation_summary(recent_ops, summary_path, platform_key)
        shutil.copy2(op_log_src, os.path.join(metadata_dir, 'operation_log.json'))
        print("  ✓ 操作记录")

    todo_state_src = os.path.join(work_dir, TODO_STATE_FILE)
    if os.path.exists(todo_state_src):
        shutil.copy2(todo_state_src, os.path.join(metadata_dir, 'todo_state.json'))

    from ..utils import REVIEW_STATE_FILE
    review_state_src = os.path.join(work_dir, REVIEW_STATE_FILE)
    if os.path.exists(review_state_src):
        shutil.copy2(review_state_src, os.path.join(metadata_dir, 'review_state.json'))

    project_tags = manifest.get('project_tags', [])
    project_meta = manifest.get('metadata', {})
    check_report = load_json(check_report_src, None) if os.path.exists(check_report_src) else None

    plan = _build_platform_plan(work_dir, manifest, platform_key, platform,
                                 project_tags, project_meta, check_report, relative=True)

    _write_platform_plan_md(plan, os.path.join(target_dir, f'{platform_key}_plan.md'), platform)
    save_json(plan, os.path.join(target_dir, f'{platform_key}_plan.json'))
    print("  ✓ 发布计划 (md+json)")

    _write_platform_todo(plan, target_dir, work_dir, platform_key)
    print("  ✓ 待办列表")

    _write_platform_asset_list(plan, target_dir, manifest)
    print("  ✓ 素材清单")

    _write_platform_readme(plan, target_dir, manifest)
    print("  ✓ 交接文档 (README)")

    handoff_info = {
        'platform_key': platform_key,
        'platform_name': platform['name'],
        'generated_at': datetime.now().isoformat(),
        'output_dir': output_dir,
        'contents': {
            'videos': video_count,
            'covers': cover_count,
            'captions': caption_count,
            'images': image_count,
        },
        'summary': plan.get('summary', {}),
    }
    save_json(handoff_info, os.path.join(target_dir, 'handoff_info.json'))

    log_operation(work_dir, 'handoff_export', {
        'platform': platform_key,
        'output_dir': output_dir,
        'videos': video_count,
        'covers': cover_count,
    })

    s = plan.get('summary', {})
    status = "✅ 可发布" if s.get('publishable') else "⚠️ 需完善"
    print(f"\n{'=' * 60}")
    print(f"  📮 【{platform['name']}】交付包完成")
    print(f"  状态: {status}  (评分 {s.get('platform_score', '?')}/100)")
    print(f"  就绪: {s.get('ready_videos', 0)}/{s.get('total_videos', 0)} 个视频")
    print(f"  目录: {target_dir}")
    print(f"{'=' * 60}")
    print(f"\n  可直接拷贝目录: {output_dir}")
    print(f"  打开 README.md 查看交接说明")

    return target_dir


def _write_operation_summary(recent_ops, summary_path, platform_key):
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("# 操作记录摘要\n\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"平台: {platform_key}\n\n")
        f.write("---\n\n")
        f.write("## 最近 50 条操作\n\n")

        if not recent_ops:
            f.write("（暂无操作记录）\n")
            return

        op_label_map = {
            'scan': '🔍 扫描',
            'tag_add': '🏷️ 添加标签',
            'tag_remove': '🏷️ 移除标签',
            'cover_extract': '🖼️ 提取封面',
            'cover_select': '🖼️ 选择封面',
            'caption_generate': '📝 生成字幕',
            'check': '✅ 检查',
            'pack': '📦 打包',
            'metadata_set': '📋 设置项目元数据',
            'metadata_set_video': '📋 设置视频元数据',
            'metadata_import': '📋 批量导入元数据',
            'publish_plan': '📊 生成发布计划',
            'todo_refresh': '📝 刷新待办',
            'todo_done': '✅ 完成待办',
            'todo_reopen': '🔄 重新打开待办',
            'handoff_export': '📤 导出交付包',
        }

        for entry in reversed(recent_ops):
            ts = entry.get('timestamp', '')
            op = entry.get('operation', '')
            details = entry.get('details', {})
            label = op_label_map.get(op, op)

            detail_parts = []
            for k, v in details.items():
                if isinstance(v, list):
                    v_str = ', '.join(str(x) for x in v)
                else:
                    v_str = str(v)
                if len(v_str) > 30:
                    v_str = v_str[:27] + '...'
                detail_parts.append(f"{k}: {v_str}")

            detail_str = ' | '.join(detail_parts) if detail_parts else ''
            f.write(f"- **{ts[:19].replace('T', ' ')}** {label}")
            if detail_str:
                f.write(f"  \n  {detail_str}")
            f.write("\n")


def list_handoffs(work_dir):
    packs_root = os.path.join(work_dir, PACK_DIR)
    if not os.path.exists(packs_root):
        print("\n暂无交付包")
        return []

    handoffs = []
    for item in sorted(os.listdir(packs_root)):
        item_path = os.path.join(packs_root, item)
        if os.path.isdir(item_path):
            handoff_info = os.path.join(item_path, 'handoff_info.json')
            if os.path.exists(handoff_info):
                info = load_json(handoff_info)
                handoffs.append({
                    'name': item,
                    'platform': info.get('platform_key', '?'),
                    'platform_name': info.get('platform_name', '?'),
                    'created_at': info.get('generated_at', '?'),
                    'score': info.get('summary', {}).get('platform_score', '?'),
                    'videos': info.get('contents', {}).get('videos', 0),
                    'ready': f"{info.get('summary', {}).get('ready_videos', 0)}/{info.get('summary', {}).get('total_videos', 0)}",
                })

    if not handoffs:
        print("\n暂无交付包")
        return []

    print("\n📮 交付包列表")
    print("=" * 80)
    table_data = []
    for i, h in enumerate(handoffs, 1):
        table_data.append([
            i,
            h['name'],
            h['platform_name'],
            h['created_at'][:19].replace('T', ' '),
            f"{h['score']}/100",
            h['videos'],
            h['ready'],
        ])
    print(tabulate(table_data,
                   headers=['#', '名称', '平台', '创建时间', '评分', '视频', '就绪'],
                   tablefmt='simple'))
    return handoffs
