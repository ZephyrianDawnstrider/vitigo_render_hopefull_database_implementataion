from django.contrib import admin
from .models import (
    SupportCategory,
    SupportTicket,
    SupportResponse,
    SupportAttachment,
    FAQ,
    KnowledgeBaseArticle,
    SupportRating
)

@admin.register(SupportCategory)
class SupportCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'user', 'category', 'status', 'priority', 'created_at', 'updated_at')
    list_filter = ('status', 'priority', 'category')
    search_fields = ('subject', 'description', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'

@admin.register(SupportResponse)
class SupportResponseAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('message', 'ticket__subject', 'user__email')
    readonly_fields = ('created_at',)

@admin.register(SupportAttachment)
class SupportAttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'response', 'file', 'uploaded_at')
    list_filter = ('uploaded_at',)
    readonly_fields = ('uploaded_at',)

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'category', 'created_at', 'updated_at')
    list_filter = ('category', 'created_at')
    search_fields = ('question', 'answer')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(KnowledgeBaseArticle)
class KnowledgeBaseArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'created_by', 'created_at', 'updated_at')
    list_filter = ('category', 'created_at')
    search_fields = ('title', 'content')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(SupportRating)
class SupportRatingAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    readonly_fields = ('created_at',)
    search_fields = ('ticket__subject', 'comments')
