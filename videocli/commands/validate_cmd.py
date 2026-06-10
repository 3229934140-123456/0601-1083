import os
import json
from pathlib import Path
from tabulate import tabulate


def validate_pack(pack_dir):
    if not os.path.exists(pack_dir):
        print(f"❌ 目录不存在: {pack_dir}")
        return False

    if not os.path.isdir(pack_dir):
        print(f"❌ 不是目录: {pack_dir}")
        return False

    print(f"\n🔍 校验交付包: {pack_dir}")
    print("=" * 80)

    issues = []
    warnings = []
    passed = []

    videos_dir = os.path.join(pack_dir, 'videos')
    if os.path.isdir(videos_dir):
        videos = [f for f in os.listdir(videos_dir) if not f.startswith('.')]
        if videos:
            passed.append(f"视频目录存在，{len(videos)} 个视频")
        else:
            warnings.append("视频目录存在但没有视频文件")
    else:
        issues.append("缺少 videos/ 视频目录")

    covers_dir = os.path.join(pack_dir, 'covers')
    if os.path.isdir(covers_dir):
        covers = [f for f in os.listdir(covers_dir) if not f.startswith('.')]
        if covers:
            passed.append(f"封面目录存在，{len(covers)} 个封面")
        else:
            warnings.append("封面目录存在但没有封面文件")
    else:
        warnings.append("缺少 covers/ 封面目录（可选）")

    captions_dir = os.path.join(pack_dir, 'captions')
    if os.path.isdir(captions_dir):
        captions = [f for f in os.listdir(captions_dir) if not f.startswith('.')]
        if captions:
            passed.append(f"字幕目录存在，{len(captions)} 个字幕文件")
        else:
            warnings.append("字幕目录存在但没有字幕文件")
    else:
        warnings.append("缺少 captions/ 字幕目录（可选）")

    images_dir = os.path.join(pack_dir, 'images')
    if os.path.isdir(images_dir):
        images = [f for f in os.listdir(images_dir) if not f.startswith('.')]
        if images:
            passed.append(f"图片目录存在，{len(images)} 张图片")
    else:
        pass

    readme_path = os.path.join(pack_dir, 'README.md')
    if os.path.isfile(readme_path):
        passed.append("README.md 存在")
    else:
        issues.append("缺少 README.md 交接文档")

    handoff_info_path = os.path.join(pack_dir, 'handoff_info.json')
    has_handoff_info = os.path.isfile(handoff_info_path)
    if has_handoff_info:
        passed.append("handoff_info.json 存在")
    else:
        warnings.append("缺少 handoff_info.json（可选，新版交付包特有）")

    plan_json_files = list(Path(pack_dir).glob('*_plan.json'))
    if plan_json_files:
        passed.append(f"发布计划 JSON 存在: {', '.join(f.name for f in plan_json_files)}")
    else:
        plan_json_files = list(Path(pack_dir).glob('**/*_plan.json'))
        if plan_json_files:
            passed.append(f"发布计划 JSON 存在（子目录）: {plan_json_files[0].name}")
        else:
            issues.append("缺少发布计划 JSON 文件 (*_plan.json)")

    plan_md_files = list(Path(pack_dir).glob('*_plan.md'))
    if plan_md_files:
        passed.append(f"发布计划 Markdown 存在: {', '.join(f.name for f in plan_md_files)}")
    else:
        plan_md_files = list(Path(pack_dir).glob('**/*_plan.md'))
        if plan_md_files:
            passed.append(f"发布计划 Markdown 存在（子目录）: {plan_md_files[0].name}")
        else:
            warnings.append("缺少发布计划 Markdown 文件")

    plan_path = plan_json_files[0] if plan_json_files else None
    if plan_path:
        try:
            with open(plan_path, 'r', encoding='utf-8') as f:
                plan = json.load(f)
            passed.append("发布计划 JSON 格式有效")

            videos = plan.get('videos', [])
            if not videos:
                warnings.append("发布计划中没有视频数据")
            else:
                video_issues = 0
                for v in videos:
                    video_name = v.get('video_name', '')
                    video_path_rel = v.get('video_path', '')
                    if video_path_rel:
                        video_full_path = os.path.join(pack_dir, video_path_rel)
                        if not os.path.isfile(video_full_path):
                            issues.append(f"视频文件缺失: {video_path_rel} (视频: {video_name})")
                            video_issues += 1

                    cover_path = v.get('cover_path', '')
                    if cover_path:
                        cover_full_path = os.path.join(pack_dir, cover_path)
                        if not os.path.isfile(cover_full_path):
                            issues.append(f"封面文件缺失: {cover_path} (视频: {video_name})")
                            video_issues += 1

                    caption_files = v.get('caption_files', [])
                    for cap in caption_files:
                        cap_full_path = os.path.join(pack_dir, cap)
                        if not os.path.isfile(cap_full_path):
                            issues.append(f"字幕文件缺失: {cap} (视频: {video_name})")
                            video_issues += 1

                if video_issues == 0:
                    passed.append(f"所有 {len(videos)} 个视频的素材路径有效")

            summary = plan.get('summary', {})
            if summary:
                passed.append(f"计划摘要: {summary.get('ready_videos', 0)}/{summary.get('total_videos', 0)} 就绪")

            if 'review_status' in videos[0] if videos else False:
                passed.append("计划包含审核状态数据")

            if 'todo_progress' in videos[0] if videos else False:
                passed.append("计划包含待办进度数据")

        except json.JSONDecodeError as e:
            issues.append(f"发布计划 JSON 格式错误: {e}")
        except Exception as e:
            issues.append(f"解析发布计划时出错: {e}")

    todo_list_path = os.path.join(pack_dir, 'todo_list.md')
    if os.path.isfile(todo_list_path):
        passed.append("待办列表 todo_list.md 存在")
    else:
        warnings.append("缺少 todo_list.md 待办列表")

    asset_list_path = os.path.join(pack_dir, 'asset_list.md')
    if os.path.isfile(asset_list_path):
        passed.append("素材清单 asset_list.md 存在")
    else:
        warnings.append("缺少 asset_list.md 素材清单")

    metadata_dir = os.path.join(pack_dir, 'metadata')
    if os.path.isdir(metadata_dir):
        meta_files = [f for f in os.listdir(metadata_dir) if not f.startswith('.')]
        if meta_files:
            passed.append(f"元数据目录存在，包含: {', '.join(meta_files[:5])}{'...' if len(meta_files) > 5 else ''}")
    else:
        warnings.append("缺少 metadata/ 元数据目录（可选，handoff 特有）")

    print()
    if passed:
        print("✅ 通过项:")
        for p in passed:
            print(f"   ✓ {p}")

    if warnings:
        print(f"\n⚠️  警告项 ({len(warnings)}):")
        for w in warnings:
            print(f"   ! {w}")

    if issues:
        print(f"\n❌ 错误项 ({len(issues)}):")
        for i in issues:
            print(f"   ✗ {i}")

    print()
    print("=" * 80)
    if issues:
        print(f"❌ 校验失败: {len(issues)} 个错误, {len(warnings)} 个警告")
        print("   请修复错误后再交付")
        return False
    elif warnings:
        print(f"⚠️  校验通过（有 {len(warnings)} 个警告）")
        print("   可交付，但建议核对警告项")
        return True
    else:
        print("✅ 校验完全通过")
        print("   交付包完整，可以直接交付")
        return True


def validate_project(work_dir):
    from ..utils import load_json, PROJECT_MANIFEST, CHECK_REPORT

    print(f"\n🔍 校验项目: {work_dir}")
    print("=" * 80)

    issues = []
    warnings = []
    passed = []

    manifest_path = os.path.join(work_dir, PROJECT_MANIFEST)
    if os.path.isfile(manifest_path):
        try:
            manifest = load_json(manifest_path)
            passed.append("项目清单存在且有效")
        except Exception as e:
            issues.append(f"项目清单格式错误: {e}")
            manifest = None
    else:
        issues.append("缺少 project_manifest.json，请先运行 scan")
        manifest = None

    if manifest:
        videos = manifest.get('videos', [])
        missing_videos = 0
        for v in videos:
            vp = v.get('path', '')
            if not os.path.isfile(vp):
                issues.append(f"视频文件不存在: {vp}")
                missing_videos += 1
        if missing_videos == 0 and videos:
            passed.append(f"所有 {len(videos)} 个视频文件路径有效")

        images = manifest.get('images', [])
        missing_images = 0
        for img in images:
            ip = img.get('path', '')
            if not os.path.isfile(ip):
                warnings.append(f"图片文件不存在: {ip}")
                missing_images += 1
        if missing_images == 0 and images:
            passed.append(f"所有 {len(images)} 张图片路径有效")

    check_report_path = os.path.join(work_dir, CHECK_REPORT)
    if os.path.isfile(check_report_path):
        passed.append("检查报告存在")
    else:
        warnings.append("缺少 check_report.json，建议先运行 check")

    print()
    if passed:
        print("✅ 通过项:")
        for p in passed:
            print(f"   ✓ {p}")

    if warnings:
        print(f"\n⚠️  警告项 ({len(warnings)}):")
        for w in warnings:
            print(f"   ! {w}")

    if issues:
        print(f"\n❌ 错误项 ({len(issues)}):")
        for i in issues:
            print(f"   ✗ {i}")

    print()
    print("=" * 80)
    if issues:
        print(f"❌ 校验失败: {len(issues)} 个错误, {len(warnings)} 个警告")
        return False
    else:
        print(f"✅ 校验通过 ({len(warnings)} 个警告)")
        return True
