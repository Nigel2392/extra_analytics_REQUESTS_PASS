
from django.contrib import admin
from django.core.serializers.json import DjangoJSONEncoder
import json
from .models import Analytics,UserAnalytics,UserAnalyticsMeta
from django.utils.translation import gettext_lazy as _
from django.db.models import F, Case, When


class BaseAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['win','linux','mac','android','iphone','other']
    list_filter = ['win','linux','mac','android','iphone','other']
    search_fields = ['win','linux','mac','android','iphone','other']
    ordering = ['-win',]

class AnalyticsAdmin(BaseAnalyticsAdmin):
    def changelist_view(self,request,extra_context=None):
       chart_data = (
           Analytics.objects.annotate().values("win","linux","mac","android","iphone","other")
       )

       as_json = json.dumps(list(chart_data), cls=DjangoJSONEncoder)
       extra_context = extra_context or {"chart_data": as_json}
       return super().changelist_view(request, extra_context=extra_context)

class UserAnalyticsAdmin(BaseAnalyticsAdmin):
    list_display  = ['user','count_page_visits','sessionid'] + BaseAnalyticsAdmin.list_display
    list_filter   = ['user']                                 + BaseAnalyticsAdmin.list_filter
    search_fields = ['user__username','user__email']         + BaseAnalyticsAdmin.search_fields

    ordering = ('-win',)

    def count_page_visits(self,obj):
        return obj.count_page_visits['visitations_total']
    count_page_visits.short_description = _("Total pages visited")

    def changelist_view(self,request,extra_context=None):
        # Get most active users for a pie chart. 
       chart_data = (
           UserAnalytics.objects.annotate(bound=Case(
                When(user__isnull=False, then=F('user__username')),
                When(sessionid__isnull=False, then=F('sessionid')),
                default=F('sessionid')
            )).values('bound').annotate(total_count=F('win')+F('linux')+F('mac')+F('android')+F('iphone')+F('other'))
       )
       # Serialize and attach the chart data to the template context
       as_json = json.dumps(list(chart_data), cls=DjangoJSONEncoder)
       extra_context = extra_context or {"chart_data": as_json}

       # Call the superclass changelist_view to render the page
       return super().changelist_view(request, extra_context=extra_context)


class UserAnalyticsMetaAdmin(admin.ModelAdmin):
    list_display = ('bound_to','ip','current_page', 'date_created','page_visits')
    list_filter = ('bound_to__user__email','ip','current_page', 'created_at')
    search_fields = ('bound_to__user__email','ip','current_page','created_at')
    ordering = ('-page_visits',)

    def date_created(self,obj):
        return obj.created_at.date()

    def save_model(self, request, obj, form, change):
        obj.save(request=request)

    def changelist_view(self,request,extra_context=None):
        chart_data = (
            UserAnalyticsMeta.objects.get_most_popular_pages()
        )
        # Serialize and attach the chart data to the template context
        as_json = json.dumps(list(chart_data), cls=DjangoJSONEncoder)
        chart_data2 = (
           UserAnalyticsMeta.objects.get_page_visits_per_day()
        )
        
        # Serialize and attach the chart data to the template context
        as_json = json.dumps(list(chart_data), cls=DjangoJSONEncoder)
        as_json_2 = json.dumps(list(chart_data2), cls=DjangoJSONEncoder)

        extra_context = extra_context or {"chart_data": as_json, "chart_data2": as_json_2}

        # Call the superclass changelist_view to render the page
        return super().changelist_view(request, extra_context=extra_context)


# Register admin classes to 
admin.site.register(Analytics,AnalyticsAdmin)
admin.site.register(UserAnalytics,UserAnalyticsAdmin)
admin.site.register(UserAnalyticsMeta,UserAnalyticsMetaAdmin)
