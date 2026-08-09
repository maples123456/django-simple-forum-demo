from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from analytics.services import generate_metrics


class Command(BaseCommand):
    help = '生成用户日活、内容互动及留存指标。默认生成昨天的数据。'

    def add_arguments(self, parser):
        parser.add_argument('--date', dest='single_date', help='指定日期，格式 YYYY-MM-DD')
        parser.add_argument('--start', help='开始日期，格式 YYYY-MM-DD')
        parser.add_argument('--end', help='结束日期，格式 YYYY-MM-DD')

    def handle(self, *args, **options):
        try:
            if options['single_date']:
                start_date = end_date = date.fromisoformat(options['single_date'])
            elif options['start'] or options['end']:
                if not options['start'] or not options['end']:
                    raise CommandError('--start 和 --end 必须同时提供。')
                start_date = date.fromisoformat(options['start'])
                end_date = date.fromisoformat(options['end'])
            else:
                start_date = end_date = timezone.localdate() - timedelta(days=1)
        except ValueError as error:
            raise CommandError('日期格式必须为 YYYY-MM-DD。') from error
        if start_date > end_date:
            raise CommandError('开始日期不能晚于结束日期。')
        generate_metrics(start_date, end_date)
        self.stdout.write(self.style.SUCCESS(f'已生成 {start_date} 至 {end_date} 的指标。'))
