from django.core.management.base import BaseCommand, CommandError

from analytics.demo_data import DEMO_PASSWORD, generate_demo_data


class Command(BaseCommand):
    help = '生成可用于论坛活跃、内容互动、用户分层和留存分析的确定性演示数据。'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=60, help='生成天数，至少 31，默认 60。')
        parser.add_argument('--users', type=int, default=180, help='演示用户数，至少 20，默认 180。')
        parser.add_argument('--seed', type=int, default=20260810, help='随机种子；相同参数生成相同分布。')
        parser.add_argument('--reset', action='store_true', help='删除此前由本命令生成的数据后重新生成。')

    def handle(self, *args, **options):
        try:
            result = generate_demo_data(
                days=options['days'],
                user_count=options['users'],
                seed=options['seed'],
                reset=options['reset'],
            )
        except ValueError as error:
            raise CommandError(str(error)) from error

        self.stdout.write(self.style.SUCCESS('论坛演示数据和指标已生成。'))
        self.stdout.write(f"时间范围：{result['start_date']} 至 {result['end_date']}")
        self.stdout.write(f"业务数据：{result['users']} 用户，{result['boards']} 板块，{result['posts']} 帖子，{result['replies']} 回复")
        self.stdout.write(f"事件数据：{result['events']} 条，其中匿名事件 {result['anonymous_events']} 条")
        self.stdout.write(f"最新指标：DAU {result['dau']}，WAU {result['wau']}，MAU {result['mau']}，新增用户 {result['new_users']}")
        self.stdout.write(f'演示用户登录密码：{DEMO_PASSWORD}')
