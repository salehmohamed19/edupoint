from django.contrib import admin
from .models import Certificate, Course, Enrollment, InstructorPayout, Lesson, Review


@admin.register(InstructorPayout)
class InstructorPayoutAdmin(admin.ModelAdmin):
  list_display = ('instructor', 'amount', 'created_at')
  search_fields = ('instructor__username', 'instructor__email', 'notes')
  list_filter = ('created_at',)


admin.site.register(Course)
admin.site.register(Lesson)
admin.site.register(Enrollment)
admin.site.register(Certificate)
admin.site.register(Review)