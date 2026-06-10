import os
import click
from dotenv import load_dotenv

from . import __version__
from .commands.scan_cmd import scan_directory, print_scan_report
from .commands.tag_cmd import add_tags, remove_tags, list_tags
from .commands.cover_cmd import extract_covers, list_covers, select_cover
from .commands.caption_cmd import generate_caption_draft, list_captions
from .commands.check_cmd import check_project
from .commands.pack_cmd import pack_project, list_packs
from .commands.metadata_cmd import set_project_metadata, set_video_metadata, show_metadata, import_metadata
from .commands.publish_plan_cmd import generate_publish_plan, show_publish_plan
from .commands.todo_cmd import (
    list_todos, mark_todo_done, reopen_todo,
    refresh_todos, mark_category_done
)
from .commands.handoff_cmd import export_handoff, list_handoffs
from .commands.compare_cmd import compare_platforms

load_dotenv()


@click.group()
@click.version_option(__version__, '-v', '--version')
@click.option('-d', '--directory', default='.', help='工作目录，默认为当前目录')
@click.pass_context
def cli(ctx, directory):
    """短视频创作者命令行工具 - 批量整理发布前内容"""
    ctx.ensure_object(dict)
    ctx.obj['work_dir'] = os.path.abspath(directory)


@cli.command()
@click.option('--recursive/--no-recursive', default=True, help='是否递归扫描子目录')
@click.pass_context
def scan(ctx, recursive):
    """扫描目录中的视频和图片，生成项目清单"""
    work_dir = ctx.obj['work_dir']
    click.echo(f"扫描目录: {work_dir}")
    manifest = scan_directory(work_dir, recursive=recursive)
    if manifest:
        print_scan_report(manifest)


@cli.group()
def tag():
    """管理主题标签"""
    pass


@tag.command('add')
@click.argument('tags')
@click.option('-t', '--target', default=None, help='目标文件路径，不指定则添加到项目')
@click.pass_context
def tag_add(ctx, tags, target):
    """添加标签，多个标签用逗号分隔"""
    work_dir = ctx.obj['work_dir']
    add_tags(work_dir, tags, target)


@tag.command('remove')
@click.argument('tags')
@click.option('-t', '--target', default=None, help='目标文件路径')
@click.pass_context
def tag_remove(ctx, tags, target):
    """移除标签"""
    work_dir = ctx.obj['work_dir']
    remove_tags(work_dir, tags, target)


@tag.command('list')
@click.pass_context
def tag_list(ctx):
    """列出所有标签"""
    work_dir = ctx.obj['work_dir']
    list_tags(work_dir)


@cli.group()
def cover():
    """管理视频封面"""
    pass


@cover.command('extract')
@click.option('-n', '--num', default=5, help='每个视频提取的封面数量')
@click.option('-v', '--video', default=None, help='指定视频文件，不指定则处理所有视频')
@click.pass_context
def cover_extract(ctx, num, video):
    """提取候选封面"""
    work_dir = ctx.obj['work_dir']
    extract_covers(work_dir, num_thumbs=num, target_video=video)


@cover.command('list')
@click.pass_context
def cover_list(ctx):
    """列出所有候选封面"""
    work_dir = ctx.obj['work_dir']
    list_covers(work_dir)


@cover.command('select')
@click.argument('index', type=int)
@click.pass_context
def cover_select(ctx, index):
    """选择封面（按序号）"""
    work_dir = ctx.obj['work_dir']
    select_cover(work_dir, index)


@cli.group()
def caption():
    """管理字幕时间轴"""
    pass


@caption.command('generate')
@click.option('-v', '--video', default=None, help='指定视频文件')
@click.option('-t', '--template', default='basic',
              type=click.Choice(['basic', 'intro', 'story']),
              help='字幕模板类型')
@click.pass_context
def caption_generate(ctx, video, template):
    """生成字幕时间轴草稿"""
    work_dir = ctx.obj['work_dir']
    generate_caption_draft(work_dir, target_video=video, template_type=template)


@caption.command('list')
@click.pass_context
def caption_list(ctx):
    """列出所有字幕文件"""
    work_dir = ctx.obj['work_dir']
    list_captions(work_dir)


@cli.group()
def metadata():
    """管理项目和视频元数据"""
    pass


@metadata.command('set')
@click.option('--title', default=None, help='项目标题')
@click.option('--desc', 'description', default=None, help='项目描述')
@click.option('--platforms', default=None, help='发布平台，多个用逗号分隔')
@click.option('--author', default=None, help='作者信息')
@click.option('--notes', default=None, help='备注信息')
@click.pass_context
def metadata_set(ctx, title, description, platforms, author, notes):
    """设置项目元数据"""
    work_dir = ctx.obj['work_dir']
    set_project_metadata(work_dir, title=title, description=description,
                         platforms=platforms, author=author, notes=notes)


@metadata.command('set-video')
@click.argument('video_path')
@click.option('--title', default=None, help='视频标题')
@click.option('--desc', 'description', default=None, help='视频描述')
@click.option('--copy', default=None, help='视频文案')
@click.option('--tags', default=None, help='自定义标签，多个用逗号分隔')
@click.pass_context
def metadata_set_video(ctx, video_path, title, description, copy, tags):
    """设置单个视频的元数据"""
    work_dir = ctx.obj['work_dir']
    set_video_metadata(work_dir, video_path, title=title, description=description,
                     copy=copy, tags=tags)


@metadata.command('import')
@click.argument('file_path')
@click.option('--format', 'file_format', default=None,
              type=click.Choice(['csv', 'json']),
              help='文件格式，默认根据扩展名自动判断')
@click.pass_context
def metadata_import(ctx, file_path, file_format):
    """从 CSV 或 JSON 文件批量导入视频元数据"""
    work_dir = ctx.obj['work_dir']
    import_metadata(work_dir, file_path, file_format=file_format)


@metadata.command('show')
@click.option('-v', '--video', default=None, help='指定视频查看，不指定则显示项目')
@click.pass_context
def metadata_show(ctx, video):
    """显示元数据"""
    work_dir = ctx.obj['work_dir']
    show_metadata(work_dir, video_path=video)


@cli.group('publish-plan')
def publish_plan():
    """管理多平台发布计划"""
    pass


@publish_plan.command('generate')
@click.option('-p', '--platforms', default=None, help='目标平台，多个用逗号分隔')
@click.option('-f', '--format', 'export_format', default='both',
              type=click.Choice(['md', 'json', 'both']),
              help='导出格式')
@click.pass_context
def publish_plan_generate(ctx, platforms, export_format):
    """生成各平台发布计划"""
    work_dir = ctx.obj['work_dir']
    generate_publish_plan(work_dir, platforms=platforms, export_format=export_format)


@publish_plan.command('show')
@click.option('-p', '--platform', default=None, help='查看指定平台的发布计划')
@click.pass_context
def publish_plan_show(ctx, platform):
    """查看发布计划"""
    work_dir = ctx.obj['work_dir']
    show_publish_plan(work_dir, platform=platform)


@cli.command()
@click.option('-p', '--platforms', default=None,
              help='目标平台，多个用逗号分隔 (douyin,kuaishou,xiaohongshu,bilibili,weixin)')
@click.pass_context
def check(ctx, platforms):
    """检查时长、比例、缺失项和平台适配"""
    work_dir = ctx.obj['work_dir']
    check_project(work_dir, platforms=platforms)


@cli.group()
def pack():
    """打包发布内容"""
    pass


@pack.command('create')
@click.option('-n', '--name', default=None, help='发布包名称')
@click.option('-p', '--platforms', default=None, help='目标平台')
@click.option('--overwrite', is_flag=True, default=False, help='如果存在同名目录则覆盖')
@click.pass_context
def pack_create(ctx, name, platforms, overwrite):
    """打包为发布目录"""
    work_dir = ctx.obj['work_dir']
    pack_project(work_dir, output_name=name, platforms=platforms, overwrite=overwrite)


@pack.command('list')
@click.pass_context
def pack_list(ctx):
    """列出已打包的发布包"""
    work_dir = ctx.obj['work_dir']
    list_packs(work_dir)


@cli.group()
def todo():
    """管理待办事项状态"""
    pass


@todo.command('refresh')
@click.option('-p', '--platforms', default=None, help='目标平台，多个用逗号分隔')
@click.pass_context
def todo_refresh(ctx, platforms):
    """根据检查结果刷新待办列表"""
    work_dir = ctx.obj['work_dir']
    refresh_todos(work_dir, platforms=platforms)


@todo.command('list')
@click.option('-s', '--status', default=None,
              type=click.Choice(['pending', 'done']),
              help='按状态筛选')
@click.option('-p', '--platform', default=None, help='按平台筛选')
@click.option('--priority', default=None,
              type=click.Choice(['high', 'medium', 'low']),
              help='按优先级筛选')
@click.option('-c', '--category', default=None,
              help='按类别筛选: title, cover, caption, description, duration, ratio')
@click.pass_context
def todo_list_cmd(ctx, status, platform, priority, category):
    """列出待办事项"""
    work_dir = ctx.obj['work_dir']
    list_todos(work_dir,
               filter_status=status,
               filter_platform=platform,
               filter_priority=priority,
               filter_category=category)


@todo.command('done')
@click.argument('todo_id')
@click.pass_context
def todo_done(ctx, todo_id):
    """标记待办为完成（按 ID，可输入前缀匹配）"""
    work_dir = ctx.obj['work_dir']
    mark_todo_done(work_dir, todo_id)


@todo.command('reopen')
@click.argument('todo_id')
@click.pass_context
def todo_reopen_cmd(ctx, todo_id):
    """重新打开已完成的待办"""
    work_dir = ctx.obj['work_dir']
    reopen_todo(work_dir, todo_id)


@todo.command('fix-category')
@click.argument('category')
@click.option('-p', '--platform', default=None, help='指定平台')
@click.option('-v', '--video', default=None, help='指定视频')
@click.pass_context
def todo_fix_category(ctx, category, platform, video):
    """批量标记某类别待办为完成（如封面已全部选好）"""
    work_dir = ctx.obj['work_dir']
    mark_category_done(work_dir, category, platform=platform, video=video)


@cli.group('handoff')
def handoff():
    """管理可交付发布包"""
    pass


@handoff.command('export')
@click.argument('platform')
@click.option('-n', '--name', default=None, help='输出目录名称')
@click.option('--overwrite', is_flag=True, default=False, help='同名目录覆盖')
@click.pass_context
def handoff_export_cmd(ctx, platform, name, overwrite):
    """导出单个平台的可交付包，可单独拷走"""
    work_dir = ctx.obj['work_dir']
    export_handoff(work_dir, platform, output_dir=name, overwrite=overwrite)


@handoff.command('list')
@click.pass_context
def handoff_list_cmd(ctx):
    """列出所有交付包"""
    work_dir = ctx.obj['work_dir']
    list_handoffs(work_dir)


@cli.command('compare-platforms')
@click.option('-v', '--video', default=None, help='只对比指定视频（名称或路径关键字）')
@click.option('-p', '--platforms', default=None, help='对比平台，多个用逗号分隔')
@click.option('-e', '--export', 'export_format', default=None,
              type=click.Choice(['json', 'md', 'both']),
              help='导出对比结果到 publish_plans/')
@click.pass_context
def compare_platforms_cmd(ctx, video, platforms, export_format):
    """跨平台对比同一视频的发布信息"""
    work_dir = ctx.obj['work_dir']
    compare_platforms(work_dir, video_filter=video, platforms=platforms, export_format=export_format)


def main():
    cli()


if __name__ == '__main__':
    main()
