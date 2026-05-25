from django.contrib import admin

from .models import Chapter, Concept, Document, Subject

admin.site.register(Subject)
admin.site.register(Document)
admin.site.register(Chapter)
admin.site.register(Concept)
