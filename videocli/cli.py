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


def main():
    cli()


if __name__ == '__main__':
    main()
