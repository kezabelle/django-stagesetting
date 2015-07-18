from django.core.cache.backends.base import MEMCACHE_MAX_KEY_LENGTH
from django.utils.translation import ugettext_lazy as _
from django.db.models import Model
from django.db.models.fields import SlugField
from django.db.models.fields import DateTimeField
from django.db.models.fields.related import ForeignKey
from jsonfield import JSONField


class RuntimeSetting(Model):
    key = SlugField(max_length=MEMCACHE_MAX_KEY_LENGTH, primary_key=True)
    value = JSONField()
    site = ForeignKey('sites.Site', null=True, blank=True)
    created = DateTimeField(auto_now_add=True)
    modified = DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('key', 'site')
        ordering = ('key',)
        verbose_name = _("Setting")
        verbose_name_plural = _("Settings")
