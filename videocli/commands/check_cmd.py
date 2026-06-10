import os
from pathlib import Path
from tabulate import tabulate

from ..utils import load_json, log_operation, PROJECT_MANIFEST
from ..media import format_duration


PLATFORMS = {
    'douyin': {
        'name': '抖音',
        'ideal_duration': (15, 60),
        'max_duration': 300,
        'aspect_ratios': {
            '9:16': '推荐（竖屏）',
            '1:1': '可用',
            '16:9': '可用（横屏）'
        },
        'ideal_ratio': '9:16',
        'min_resolution': (720, 1280),
        'max_file_size_mb': 512,
    },
    'kuaishou': {
        'name': '快手',
        'ideal_duration': (15, 120),
        'max_duration': 600,
        'aspect_ratios': {
            '9:16': '推荐（竖屏）',
            '1:1': '可用',
            '16:9': '可用'
        },
        'ideal_ratio': '9:16',
        'min_resolution': (720, 1280),
        'max_file_size_mb': 1024,
    },
    'xiaohongshu': {
        'name': '小红书',
        'ideal_duration': (30, 300),
        'max_duration': 900,
        'aspect_ratios': {
            '3:4': '推荐（竖屏）',
            '1:1': '推荐',
            '4:3': '可用'
        },
        'ideal_ratio': '3:4',
        'min_resolution': (720, 960),
        'max_file_size_mb': 2048,
    },
    'bilibili': {
        'name': 'B站',
        'ideal_duration': (60, 600),
        'max_duration': None,
        'aspect_ratios': {
            '16:9': '推荐（横屏）',
            '9:16': '可用（竖屏）',
            '1:1': '可用'
        },
        'ideal_ratio': '16:9',
        'min_resolution': (1920, 1080),
        'max_file_size_mb': 8192,
    },
    'weixin': {
        'name': '微信视频号',
        'ideal_duration': (30, 180),
        'max_duration': 1800,
        'aspect_ratios': {
            '9:16': '推荐（竖屏）',
            '16:9': '可用（横屏）',
            '1:1': '可用'
        },
        'ideal_ratio': '9:16',
        'min_resolution': (720, 1280),
        'max_file_size_mb': 2048,
    }
}


def check_project(work_dir, platforms=None):
    """检查项目内容，发现问题并给出平台建议"""
    manifest_path = os.path.join(work_dir, PROJECT_MANIFEST)
    manifest = load_json(manifest_path)
    
    if not manifest:
        print(f"错误: 未找到项目清单，请先运行 scan 命令")
        return None
    
    if platforms is None:
        platforms = list(PLATFORMS.keys())
    elif isinstance(platforms, str):
        platforms = [p.strip() for p in platforms.split(',') if p.strip()]
    
    issues = []
    warnings = []
    suggestions = []
    
    print("\n" + "=" * 70)
    print("  项目内容检查")
    print("=" * 70)
    
    video_checks = _check_videos(manifest)
    issues.extend(video_checks['errors'])
    warnings.extend(video_checks['warnings'])
    
    missing_checks = _check_missing_items(manifest)
    issues.extend(missing_checks['errors'])
    warnings.extend(missing_checks['warnings'])
    
    image_checks = _check_images(manifest)
    warnings.extend(image_checks['warnings'])
    
    print("\n❌ 严重问题")
    print("-" * 50)
    if issues:
        for issue in issues:
            print(f"  ✗ {issue}")
    else:
        print("  无严重问题 ✓")
    
    print("\n⚠️  警告提示")
    print("-" * 50)
    if warnings:
        for warn in warnings:
            print(f"  ! {warn}")
    else:
        print("  无警告 ✓")
    
    print("\n📱 平台适配建议")
    print("-" * 50)
    
    platform_recommendations = {}
    for platform_key in platforms:
        platform = PLATFORMS.get(platform_key)
        if not platform:
            continue
        
        rec = _check_platform_compatibility(manifest, platform)
        platform_recommendations[platform_key] = rec
        
        status = "✅ 推荐" if rec['score'] >= 80 else ("⚠️  一般" if rec['score'] >= 50 else "❌ 不推荐")
        print(f"\n  {platform['name']} ({status}) - 适配度: {rec['score']}/100")
        
        if rec['issues']:
            for issue in rec['issues']:
                print(f"    - {issue}")
        if rec['tips']:
            for tip in rec['tips']:
                print(f"    💡 {tip}")
    
    result = {
        'errors': issues,
        'warnings': warnings,
        'suggestions': suggestions,
        'platforms': platform_recommendations,
        'total_score': _calculate_overall_score(platform_recommendations),
    }
    
    log_operation(work_dir, 'check', {
        'errors_count': len(issues),
        'warnings_count': len(warnings),
        'platforms_checked': platforms
    })
    
    print(f"\n📊 总体评分: {result['total_score']}/100")
    
    return result


def _check_videos(manifest):
    """检查视频文件"""
    errors = []
    warnings = []
    videos = manifest.get('videos', [])
    
    if not videos:
        errors.append("项目中没有视频文件")
        return {'errors': errors, 'warnings': warnings}
    
    for video in videos:
        name = video['name']
        
        if video.get('has_ffprobe', True) is False:
            warnings.append(f"{name}: 无法获取视频元数据（建议安装 ffmpeg）")
            continue
        
        duration = video.get('duration')
        if duration is not None:
            if duration < 3:
                errors.append(f"{name}: 视频时长过短 ({format_duration(duration)})，不适合发布")
            elif duration > 600:
                warnings.append(f"{name}: 视频时长较长 ({format_duration(duration)})，部分平台可能有限制")
        
        width = video.get('width')
        height = video.get('height')
        if width and height:
            if width < 640 or height < 640:
                warnings.append(f"{name}: 分辨率较低 ({width}x{height})，可能影响观看体验")
        
        size_mb = video.get('size_mb', 0)
        if size_mb > 500:
            warnings.append(f"{name}: 文件较大 ({size_mb} MB)，上传可能较慢")
    
    return {'errors': errors, 'warnings': warnings}


def _check_missing_items(manifest):
    """检查缺失项"""
    errors = []
    warnings = []
    videos = manifest.get('videos', [])
    
    if not videos:
        return {'errors': errors, 'warnings': warnings}
    
    project_tags = manifest.get('project_tags', [])
    if not project_tags:
        warnings.append("项目缺少主题标签，使用 tag add 添加")
    
    has_cover = False
    for video in videos:
        if video.get('selected_cover'):
            has_cover = True
            break
    
    covers = manifest.get('covers', [])
    if not covers and not has_cover:
        warnings.append("尚未提取候选封面，使用 cover extract 提取")
    
    captions = manifest.get('captions', {})
    if not captions:
        warnings.append("尚未生成字幕草稿，使用 caption generate 生成")
    
    videos_without_cover = []
    for video in videos:
        if not video.get('selected_cover'):
            videos_without_cover.append(video['name'])
    
    if videos_without_cover and len(videos) > 1:
        warnings.append(f"有 {len(videos_without_cover)} 个视频未选择封面: {', '.join(videos_without_cover)}")
    
    if not manifest.get('title'):
        warnings.append("项目缺少标题，请设置标题")
    
    if not manifest.get('description'):
        warnings.append("项目缺少描述，请添加描述文案")
    
    return {'errors': errors, 'warnings': warnings}


def _check_images(manifest):
    """检查图片文件"""
    warnings = []
    images = manifest.get('images', [])
    
    for img in images:
        name = img['name']
        width = img.get('width')
        height = img.get('height')
        
        if width and height:
            if width < 640 or height < 640:
                warnings.append(f"{name}: 图片分辨率较低 ({width}x{height})")
    
    return {'warnings': warnings}


def _check_platform_compatibility(manifest, platform):
    """检查平台兼容性"""
    videos = manifest.get('videos', [])
    issues = []
    tips = []
    score = 100
    
    if not videos:
        return {'score': 0, 'issues': ['无视频文件'], 'tips': []}
    
    main_video = videos[0]
    duration = main_video.get('duration')
    
    if duration is not None:
        min_dur, max_dur = platform['ideal_duration']
        if duration < min_dur:
            score -= 20
            issues.append(f"时长偏短 ({format_duration(duration)})，推荐 {min_dur}-{max_dur} 秒")
        elif duration > max_dur:
            score -= 15
            issues.append(f"时长偏长 ({format_duration(duration)})，推荐 {min_dur}-{max_dur} 秒")
        
        if platform['max_duration'] and duration > platform['max_duration']:
            score -= 40
            issues.append(f"超过平台最大时长限制 ({platform['max_duration']} 秒)")
    
    width = main_video.get('width')
    height = main_video.get('height')
    
    if width and height:
        ideal_ratio = platform['ideal_ratio']
        ratio_w, ratio_h = _parse_ratio(ideal_ratio)
        actual_ratio = width / height
        ideal_ratio_value = ratio_w / ratio_h
        ratio_diff = abs(actual_ratio - ideal_ratio_value) / ideal_ratio_value
        
        if ratio_diff > 0.15:
            score -= 25
            issues.append(f"画面比例 {width}:{height} 不是 {ideal_ratio}（{platform['aspect_ratios'].get(ideal_ratio, '推荐')}）")
        elif ratio_diff > 0.05:
            score -= 10
            tips.append(f"建议调整为 {ideal_ratio} 比例以获得最佳展示效果")
        
        min_w, min_h = platform['min_resolution']
        if width < min_w or height < min_h:
            score -= 20
            issues.append(f"分辨率 {width}x{height} 低于推荐的 {min_w}x{min_h}")
    
    size_mb = main_video.get('size_mb', 0)
    if size_mb > platform['max_file_size_mb']:
        score -= 30
        issues.append(f"文件大小 {size_mb} MB 超过限制 {platform['max_file_size_mb']} MB")
    
    project_tags = manifest.get('project_tags', [])
    if not project_tags:
        score -= 10
        tips.append("建议添加相关话题标签以增加曝光")
    elif len(project_tags) < 3:
        tips.append("可以添加更多相关话题标签")
    
    return {
        'score': max(0, score),
        'issues': issues,
        'tips': tips
    }


def _parse_ratio(ratio_str):
    """解析比例字符串，如 '9:16' 返回 (9, 16)"""
    parts = ratio_str.split(':')
    return int(parts[0]), int(parts[1])


def _calculate_overall_score(platform_recommendations):
    """计算总体评分"""
    if not platform_recommendations:
        return 0
    
    scores = [rec['score'] for rec in platform_recommendations.values()]
    return int(sum(scores) / len(scores))
