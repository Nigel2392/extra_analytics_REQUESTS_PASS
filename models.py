from django.db import models
from django.db.models.functions import TruncDate
from django.conf import settings
from django.utils.translation import gettext_lazy as _


# Create your models here.
# Analytics
class AbstractAnalytics(models.Model):
    win = models.IntegerField(default=0)
    linux = models.IntegerField(default=0)
    mac = models.IntegerField(default=0)
    android = models.IntegerField(default=0)
    iphone = models.IntegerField(default=0)
    other = models.IntegerField(default=0)

    class Meta:
        abstract = True

class Analytics(AbstractAnalytics):
    class Meta:
        verbose_name = _('General OS Analytic')
        verbose_name_plural = _('General OS Analytics')

class UserAnalytics(AbstractAnalytics):
    sessionid = models.CharField(max_length=100, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='analytics')

    class Meta:
        verbose_name = _('User OS Analytics')
        verbose_name_plural = _('User OS Analytics')

    def __str__(self):
        if self.user:
            return f'{self.user.username}'
        else:
            return f'{self.sessionid}'

    @property
    def count_page_visits(self):
        qs = self.meta.all().annotate(total_visits=models.F('page_visits')).aggregate(visitations_total=models.Sum('total_visits'))
        return qs

class UserAnalyticsMetaManager(models.Manager):
    def get_queryset(self):
        # return UserAnalyticsQuerySet(self.model, using=self._db)
        return super(UserAnalyticsMetaManager, self).get_queryset()

    def getattr(self, key):
        return getattr(self.get_query_set(), key)

    def get_most_popular_pages(self):
        qs = self.values('current_page').annotate(
                page_visits= models.Sum('page_visits')
            ).order_by('-page_visits')
        return qs
    
    def get_page_visits_per_day(self):
        #select_data = {"date_created": """strftime('%%m/%%d/%%Y', created_at)"""}
        #qs = self.extra(select=select_data).values('date_created').annotate(models.Sum("page_visits"))
        #return qs
        return self.values(date_created=TruncDate('created_at')).annotate(models.Sum("page_visits"))
    def get_most_active_users(self):
        qs = self.filter(
                bound_to__user__isnull=False
            ).values('bound_to__user').annotate(
                page_visits_total= models.Sum('page_visits')
            ).order_by('-page_visits_total')
        return qs

    def get_all_most_active(self):
        qs = self.annotate(bound=models.Case(
                models.When(
                    bound_to__user__isnull=False, 
                        then=models.F('bound_to__user')),
                models.When(
                    bound_to__sessionid__isnull=False, 
                        then=models.F('bound_to__sessionid')),
                default=models.F('bound_to__sessionid')
            )).values('bound').annotate(page_visits=models.Sum('page_visits')).order_by('-page_visits')
        return qs


class UserAnalyticsMeta(models.Model):
    bound_to = models.ForeignKey(UserAnalytics, on_delete=models.CASCADE, related_name='meta')
    ip = models.GenericIPAddressField()
    current_page = models.CharField(max_length=500)
    page_visits = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = UserAnalyticsMetaManager()

    class Meta:
        verbose_name = _('Specific Site Analytics')
        verbose_name_plural = _('Specific Site Analytics')

    def __str__(self):
        return self.current_page

    def save(self, *args, **kwargs):
        request = kwargs.get('request', None)
        print(request)

