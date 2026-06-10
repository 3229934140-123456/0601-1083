import os
from pathlib import Path
from datetime import datetime
from tabulate import tabulate

from ..utils import (
    load_json, save_json, log_operation, REVIEW_STATE_FILE,
    PROJECT_MANIFEST
)
from .check_cmd import PLATFORMS


REVIEW_STATUSES = {
    'pending': {'label': '待审核', 'icon': '⏳', 'color': 'yellow'},
    'approved': {'label': '已通过', 'icon': '✅', 'color': 'green'},
    'rejected': {'label': '已驳回', 'icon': '❌', 'color': 'red'},
}


def get_review_state(work_dir):
    state_path = os.path.join(work_dir, REVIEW_STATE_FILE)
    state = load_json(state_path, {})
    if not state:
        state = {
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'reviews': {},
            'reviewers': [],
        }
    return state


def save_review_state(work_dir, state):
    state['updated_at'] = datetime.now().isoformat()
    state_path = os.path.join(work_dir, REVIEW_STATE_FILE)
    save_json(state, state_path)
    return state


def set_review_status(work_dir, platform_key, video_name, status,
                       reviewer=None, comment=None):
    if status not in REVIEW_STATUSES:
        valid = ', '.join(REVIEW_STATUSES.keys())
        print(f"错误: 无效状态 '{status}'，可选: {valid}")
        return None

    manifest_path = os.path.join(work_dir, PROJECT_MANIFEST)
    manifest = load_json(manifest_path)
    if not manifest:
        print("错误: 未找到项目清单")
        return None

    if platform_key not in PLATFORMS:
        print(f"错误: 无效平台 '{platform_key}'")
        return None

    video_found = False
    for v in manifest.get('videos', []):
        if v['name'] == video_name or video_name in v['name']:
            video_name = v['name']
            video_found = True
            break

    if not video_found:
        print(f"错误: 未找到视频 '{video_name}'")
        return None

    state = get_review_state(work_dir)
    reviews = state.setdefault('reviews', {})
    platform_reviews = reviews.setdefault(platform_key, {})

    video_review = platform_reviews.get(video_name, {})
    old_status = video_review.get('status', 'pending')

    video_review.update({
        'status': status,
        'video_name': video_name,
        'reviewer': reviewer or video_review.get('reviewer', ''),
        'comment': comment or video_review.get('comment', ''),
        'updated_at': datetime.now().isoformat(),
    })

    if 'created_at' not in video_review:
        video_review['created_at'] = datetime.now().isoformat()

    if old_status != status:
        history = video_review.setdefault('history', [])
        history.append({
            'from': old_status,
            'to': status,
            'reviewer': reviewer,
            'comment': comment,
            'at': datetime.now().isoformat(),
        })

    platform_reviews[video_name] = video_review

    if reviewer and reviewer not in state.get('reviewers', []):
        state['reviewers'] = state.get('reviewers', []) + [reviewer]

    save_review_state(work_dir, state)
    log_operation(work_dir, 'review_set', {
        'platform': platform_key,
        'video': video_name,
        'status': status,
        'reviewer': reviewer,
    })

    status_info = REVIEW_STATUSES[status]
    print(f"{status_info['icon']} [{PLATFORMS[platform_key]['name']}] {video_name}: {status_info['label']}")
    if reviewer:
        print(f"   审核人: {reviewer}")
    if comment:
        print(f"   备注: {comment}")

    return state


def batch_review(work_dir, platform_key, status, reviewer=None, comment=None,
                 video_filter=None):
    if status not in REVIEW_STATUSES:
        valid = ', '.join(REVIEW_STATUSES.keys())
        print(f"错误: 无效状态 '{status}'，可选: {valid}")
        return None

    manifest_path = os.path.join(work_dir, PROJECT_MANIFEST)
    manifest = load_json(manifest_path)
    if not manifest:
        print("错误: 未找到项目清单")
        return None

    if platform_key not in PLATFORMS:
        print(f"错误: 无效平台 '{platform_key}'")
        return None

    target_videos = []
    for v in manifest.get('videos', []):
        if video_filter:
            if video_filter.lower() in v['name'].lower():
                target_videos.append(v['name'])
        else:
            target_videos.append(v['name'])

    if not target_videos:
        print("错误: 没有符合条件的视频")
        return None

    state = get_review_state(work_dir)
    reviews = state.setdefault('reviews', {})
    platform_reviews = reviews.setdefault(platform_key, {})

    updated = 0
    for video_name in target_videos:
        video_review = platform_reviews.get(video_name, {})
        old_status = video_review.get('status', 'pending')

        video_review.update({
            'status': status,
            'video_name': video_name,
            'reviewer': reviewer or video_review.get('reviewer', ''),
            'comment': comment or video_review.get('comment', ''),
            'updated_at': datetime.now().isoformat(),
        })

        if 'created_at' not in video_review:
            video_review['created_at'] = datetime.now().isoformat()

        if old_status != status:
            history = video_review.setdefault('history', [])
            history.append({
                'from': old_status,
                'to': status,
                'reviewer': reviewer,
                'comment': comment,
                'at': datetime.now().isoformat(),
            })
            updated += 1

        platform_reviews[video_name] = video_review

    if reviewer and reviewer not in state.get('reviewers', []):
        state['reviewers'] = state.get('reviewers', []) + [reviewer]

    save_review_state(work_dir, state)
    log_operation(work_dir, 'review_batch', {
        'platform': platform_key,
        'status': status,
        'count': len(target_videos),
        'updated': updated,
    })

    status_info = REVIEW_STATUSES[status]
    print(f"{status_info['icon']} 批量 {status_info['label']}: {len(target_videos)} 个视频（更新了 {updated} 个状态）")
    return state


def show_reviews(work_dir, platform=None, video=None, status_filter=None):
    state = get_review_state(work_dir)
    reviews = state.get('reviews', {})

    manifest_path = os.path.join(work_dir, PROJECT_MANIFEST)
    manifest = load_json(manifest_path, {})
    videos = [v['name'] for v in manifest.get('videos', [])]

    print(f"\n🔍 审核状态总览")
    print("=" * 80)

    platform_keys = [platform] if platform else list(reviews.keys())
    if not platform_keys and not reviews:
        platform_keys = [p for p in PLATFORMS.keys()]

    all_summary = []
    for pk in platform_keys:
        if pk not in PLATFORMS:
            continue
        platform_name = PLATFORMS[pk]['name']
        platform_reviews = reviews.get(pk, {})

        counts = {'pending': 0, 'approved': 0, 'rejected': 0}
        for vname in videos:
            s = platform_reviews.get(vname, {}).get('status', 'pending')
            counts[s] = counts.get(s, 0) + 1

        all_summary.append([
            platform_name,
            f"{counts['approved']}/{len(videos)}",
            f"{counts['pending']}",
            f"{counts['rejected']}",
            f"{round(counts['approved']/len(videos)*100) if videos else 0}%",
        ])

    print(tabulate(all_summary,
                   headers=['平台', '已通过', '待审核', '已驳回', '通过率'],
                   tablefmt='simple'))

    if video or platform:
        print(f"\n📋 详情")
        print("-" * 80)

        target_platforms = [platform] if platform else list(reviews.keys())
        for pk in target_platforms:
            if pk not in PLATFORMS:
                continue
            if pk not in reviews and not video:
                continue

            print(f"\n【{PLATFORMS[pk]['name']}】")
            platform_reviews = reviews.get(pk, {})

            target_videos = [video] if video else videos
            for vname in target_videos:
                if video and video.lower() not in vname.lower():
                    continue
                review = platform_reviews.get(vname, {})
                status = review.get('status', 'pending')
                info = REVIEW_STATUSES[status]
                reviewer = review.get('reviewer', '-')
                comment = review.get('comment', '')

                status_str = f"{info['icon']} {info['label']}"
                row = [
                    vname,
                    status_str,
                    reviewer,
                    review.get('updated_at', '-')[:19].replace('T', ' '),
                ]
                print(f"  {row[0]:30s} {row[1]:12s} {row[2]:10s} {row[3]}")
                if comment:
                    print(f"    💬 备注: {comment}")

    return state


def get_platform_video_review(work_dir, platform_key, video_name):
    """获取单个视频在某平台的审核状态（供其他模块调用）"""
    state = get_review_state(work_dir)
    reviews = state.get('reviews', {})
    platform_reviews = reviews.get(platform_key, {})
    return platform_reviews.get(video_name, {'status': 'pending'})


def get_platform_review_summary(work_dir, platform_key):
    """获取平台审核概况（供其他模块调用）"""
    state = get_review_state(work_dir)
    reviews = state.get('reviews', {})
    platform_reviews = reviews.get(platform_key, {})

    manifest_path = os.path.join(work_dir, PROJECT_MANIFEST)
    manifest = load_json(manifest_path, {})
    videos = [v['name'] for v in manifest.get('videos', [])]

    counts = {'pending': 0, 'approved': 0, 'rejected': 0}
    for vname in videos:
        s = platform_reviews.get(vname, {}).get('status', 'pending')
        counts[s] = counts.get(s, 0) + 1

    return {
        'total': len(videos),
        'approved': counts['approved'],
        'pending': counts['pending'],
        'rejected': counts['rejected'],
        'approval_rate': round(counts['approved'] / len(videos) * 100, 1) if videos else 0,
    }
