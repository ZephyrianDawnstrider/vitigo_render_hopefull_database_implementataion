from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from .models import Query, QueryUpdate, QueryTag, QueryAttachment

admin.site.register(Query)
admin.site.register(QueryTag)
admin.site.register(QueryAttachment)
admin.site.register(QueryUpdate)