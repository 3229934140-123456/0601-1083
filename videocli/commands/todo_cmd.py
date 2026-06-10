import os
from pathlib import Path
from datetime import datetime
from tabulate import tabulate

from ..utils import (
    load_json, save_json, log_operation, TODO_STATE_FILE,
    PROJECT_MANIFEST, CHECK_REPORT
)
from .check_cmd import PLATFORMS


def _normalize_item_key(text):
    return text.strip().replace(' ', '_').replace(':', '_').lower()[:60]


def get_todo_state(work_dir):
    state_path = os.path.join(work_dir, TODO_STATE_FILE)
    state = load_json(state_path, {})
    if not state:
        state = {
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'todos': {}
        }
    return state


def save_todo_state(work_dir, state):
    state['updated_at'] = datetime.now().isoformat()
    state_path = os.path.join(work_dir, TODO_STATE_FILE)
    save_json(state, state_path)
    return state


def refresh_todos(work_dir, platforms=None):
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

    state = get_todo_state(work_dir)

    generated_todos = []
    if check_report:
        video_status_by_platform = check_report.get('video_status_by_platform', {})
        for platform_key, video_statuses in video_status_by_platform.items():
            if platforms and platform_key not in platforms:
                continue
            platform = PLATFORMS.get(platform_key, {})
            platform_name = platform.get('name', platform_key)
            for status in video_statuses:
                if not status.get('has_title'):
                    generated_todos.append({
                        'item': f"[{platform_name}] {status['video_name']} 缺少标题",
                        'priority': 'high',
                        'category': 'title',
                        'platform': platform_key,
                        'video': status['video_name'],
                    })
                if not status.get('has_description'):
                    generated_todos.append({
                        'item': f"[{platform_name}] {status['video_name']} 缺少描述文案",
                        'priority': 'medium',
                        'category': 'description',
                        'platform': platform_key,
                        'video': status['video_name'],
                    })
                if not status.get('has_cover'):
                    generated_todos.append({
                        'item': f"[{platform_name}] {status['video_name']} 未选择封面",
                        'priority': 'high',
                        'category': 'cover',
                        'platform': platform_key,
                        'video': status['video_name'],
                    })
                if not status.get('has_caption'):
                    generated_todos.append({
                        'item': f"[{platform_name}] {status['video_name']} 缺少字幕",
                        'priority': 'medium',
                        'category': 'caption',
                        'platform': platform_key,
                        'video': status['video_name'],
                    })
                if not status.get('duration_ok'):
                    generated_todos.append({
                        'item': f"[{platform_name}] {status['video_name']} 时长 ({status['duration']}) 不在推荐范围",
                        'priority': 'medium',
                        'category': 'duration',
                        'platform': platform_key,
                        'video': status['video_name'],
                    })
                if not status.get('ratio_ok'):
                    generated_todos.append({
                        'item': f"[{platform_name}] {status['video_name']} 比例 ({status['aspect_ratio']}) 不是最佳比例",
                        'priority': 'low',
                        'category': 'ratio',
                        'platform': platform_key,
                        'video': status['video_name'],
                    })

    existing_keys = set(state.get('todos', {}).keys())
    new_keys = set()

    for todo in generated_todos:
        key = _normalize_item_key(todo['item'])
        new_keys.add(key)
        if key in state.get('todos', {}):
            state['todos'][key].update({
                'priority': todo['priority'],
                'category': todo['category'],
                'platform': todo['platform'],
                'video': todo['video'],
            })
        else:
            state['todos'][key] = {
                'id': key,
                'item': todo['item'],
                'priority': todo['priority'],
                'category': todo['category'],
                'platform': todo['platform'],
                'video': todo['video'],
                'status': 'pending',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
            }

    stale_keys = existing_keys - new_keys
    for stale_key in stale_keys:
        if state['todos'].get(stale_key, {}).get('status') == 'pending':
            del state['todos'][stale_key]

    save_todo_state(work_dir, state)
    log_operation(work_dir, 'todo_refresh', {
        'platforms': platforms,
        'total': len(state['todos']),
        'new': len(new_keys - existing_keys),
    })

    return state


def list_todos(work_dir, filter_status=None, filter_platform=None,
               filter_priority=None, filter_category=None):
    state = get_todo_state(work_dir)

    todos = state.get('todos', {})
    if not todos:
        print("暂无待办，先运行 check 或 todo refresh 生成")
        return state

    rows = []
    for key, todo in todos.items():
        if filter_status and todo.get('status') != filter_status:
            continue
        if filter_platform and todo.get('platform') != filter_platform:
            continue
        if filter_priority and todo.get('priority') != filter_priority:
            continue
        if filter_category and todo.get('category') != filter_category:
            continue

        status_icon = {
            'pending': '⬜',
            'done': '✅',
        }.get(todo.get('status', 'pending'), '⬜')

        priority_icon = {
            'high': '🔴',
            'medium': '🟡',
            'low': '🟢',
        }.get(todo.get('priority', 'medium'), '⚪')

        rows.append([
            key[:10],
            status_icon,
            priority_icon,
            todo.get('platform', ''),
            todo.get('category', ''),
            todo.get('item', '')[:50],
        ])

    rows.sort(key=lambda r: ({'high': 0, 'medium': 1, 'low': 2}.get(r[2], 99), r[4]))

    print(f"\n📝 待办列表（共 {len(rows)} 项）")
    print("=" * 100)
    print(tabulate(rows,
                   headers=['ID', '状态', '优先级', '平台', '类别', '事项'],
                   tablefmt='simple',
                   maxcolwidths=[12, 6, 6, 10, 8, 60]))

    done_count = sum(1 for t in todos.values() if t.get('status') == 'done')
    pending_count = sum(1 for t in todos.values() if t.get('status') == 'pending')
    print(f"\n📊 统计: ✅ 已完成 {done_count} | ⬜ 待处理 {pending_count}")
    if pending_count + done_count > 0:
        progress = round(done_count / (done_count + pending_count) * 100)
        print(f"   进度: {progress}% ({done_count}/{done_count + pending_count})")

    return state


def mark_todo_done(work_dir, todo_id):
    state = get_todo_state(work_dir)
    todos = state.get('todos', {})

    target = None
    for key, todo in todos.items():
        if key == todo_id or key.startswith(todo_id):
            target = todo
            break

    if not target:
        print(f"错误: 未找到 ID 为 '{todo_id}' 的待办")
        print("提示: 运行 todo list 查看 ID")
        return None

    target['status'] = 'done'
    target['completed_at'] = datetime.now().isoformat()
    target['updated_at'] = datetime.now().isoformat()

    save_todo_state(work_dir, state)
    log_operation(work_dir, 'todo_done', {'todo_id': target['id'], 'item': target['item']})

    print(f"✅ 已标记完成: {target['item']}")
    return state


def reopen_todo(work_dir, todo_id):
    state = get_todo_state(work_dir)
    todos = state.get('todos', {})

    target = None
    for key, todo in todos.items():
        if key == todo_id or key.startswith(todo_id):
            target = todo
            break

    if not target:
        print(f"错误: 未找到 ID 为 '{todo_id}' 的待办")
        print("提示: 运行 todo list 查看 ID")
        return None

    target['status'] = 'pending'
    target['reopened_at'] = datetime.now().isoformat()
    target['updated_at'] = datetime.now().isoformat()

    save_todo_state(work_dir, state)
    log_operation(work_dir, 'todo_reopen', {'todo_id': target['id'], 'item': target['item']})

    print(f"🔄 已重新打开: {target['item']}")
    return state


def mark_category_done(work_dir, category, platform=None, video=None):
    state = get_todo_state(work_dir)
    todos = state.get('todos', {})

    marked = 0
    for key, todo in todos.items():
        if todo.get('category') != category:
            continue
        if platform and todo.get('platform') != platform:
            continue
        if video and todo.get('video') != video:
            continue
        if todo.get('status') == 'pending':
            todo['status'] = 'done'
            todo['completed_at'] = datetime.now().isoformat()
            todo['updated_at'] = datetime.now().isoformat()
            marked += 1

    if marked == 0:
        print(f"没有找到匹配的待办（类别: {category}）")
        return None

    save_todo_state(work_dir, state)
    log_operation(work_dir, 'todo_category_done', {
        'category': category,
        'platform': platform,
        'marked_count': marked,
    })

    print(f"✅ 已批量标记 {marked} 项 {category} 类待办为完成")
    return state
