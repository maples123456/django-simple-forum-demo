from django.contrib import admin

from .models import AnalyticsEvent, ProductMetricsDaily, RetentionCohort, UserActivityDaily


@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    list_display = ('event_name', 'user', 'source', 'occurred_at')
    list_filter = ('event_name', 'source', 'occurred_at')
    search_fields = ('user__username', 'anonymous_id', 'session_id')
    readonly_fields = ('event_id', 'received_at')


admin.site.register(UserActivityDaily)
admin.site.register(ProductMetricsDaily)
admin.site.register(RetentionCohort)

# Register your models here.
