from django.contrib import admin
from .models import (
    Category, Certificate, Coupon, Course, CourseAnswer, CourseQuestion, Enrollment, BundlePurchase, CourseBundle, Favorite, InstructorPayout, InstructorRating, Lesson, LessonComment, Notification, Review,
    Quiz, Question, Choice, ContactMessage, QuizAttempt, QuizAnswer,
)


@admin.register(InstructorPayout)
class InstructorPayoutAdmin(admin.ModelAdmin):
  list_display = ('instructor', 'amount', 'created_at')
  search_fields = ('instructor__username', 'instructor__email', 'notes')
  list_filter = ('created_at',)


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
  list_display = ('title', 'lesson', 'passing_score')
  list_filter = ('lesson__course',)
  search_fields = ('title', 'lesson__title')


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
  list_display = ('text', 'quiz', 'order')
  list_filter = ('quiz',)
  search_fields = ('text',)


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
  list_display = ('text', 'question', 'is_correct')
  list_filter = ('is_correct',)
  search_fields = ('text',)


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
  list_display = ('student', 'quiz', 'score', 'total_questions', 'passed', 'completed_at')
  list_filter = ('passed', 'completed_at')
  search_fields = ('student__username', 'quiz__title')


@admin.register(QuizAnswer)
class QuizAnswerAdmin(admin.ModelAdmin):
  list_display = ('attempt', 'question', 'choice')
  search_fields = ('question__text', 'choice__text')


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
  list_display = ('name', 'email', 'subject', 'created_at', 'is_read')
  list_filter = ('is_read', 'created_at')
  search_fields = ('name', 'email', 'subject')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
  list_display = ('name', 'slug')
  prepopulated_fields = {'slug': ('name',)}
  search_fields = ('name',)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
  list_display = ('student', 'course', 'created_at')
  list_filter = ('created_at',)
  search_fields = ('student__username', 'course__title')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
  list_display = ('user', 'title', 'is_read', 'created_at')
  list_filter = ('is_read', 'created_at')
  search_fields = ('user__username', 'title', 'message')


@admin.register(CourseQuestion)
class CourseQuestionAdmin(admin.ModelAdmin):
  list_display = ('title', 'course', 'student', 'is_resolved', 'created_at')
  list_filter = ('is_resolved', 'created_at')
  search_fields = ('title', 'content', 'course__title', 'student__username')


@admin.register(CourseAnswer)
class CourseAnswerAdmin(admin.ModelAdmin):
  list_display = ('question', 'student', 'is_accepted', 'created_at')
  list_filter = ('is_accepted', 'created_at')
  search_fields = ('content', 'question__title', 'student__username')


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
  list_display = ('code', 'course', 'discount_type', 'discount_value', 'used_count', 'usage_limit', 'is_active', 'expires_at')
  list_filter = ('discount_type', 'is_active', 'created_at')
  search_fields = ('code', 'course__title')
  list_editable = ('is_active',)


@admin.register(CourseBundle)
class CourseBundleAdmin(admin.ModelAdmin):
  list_display = ('title', 'price', 'total_individual_price', 'savings', 'is_active', 'created_at')
  list_filter = ('is_active', 'created_at')
  search_fields = ('title', 'description')
  filter_horizontal = ('courses',)


@admin.register(BundlePurchase)
class BundlePurchaseAdmin(admin.ModelAdmin):
  list_display = ('student', 'bundle', 'amount_paid', 'status', 'purchased_at')
  list_filter = ('status', 'purchased_at')
  search_fields = ('student__username', 'bundle__title')


@admin.register(LessonComment)
class LessonCommentAdmin(admin.ModelAdmin):
  list_display = ('lesson', 'student', 'created_at', 'is_approved')
  list_filter = ('is_approved', 'created_at')
  search_fields = ('content', 'lesson__title', 'student__username')
  list_editable = ('is_approved',)


@admin.register(InstructorRating)
class InstructorRatingAdmin(admin.ModelAdmin):
  list_display = ('instructor', 'student', 'course', 'rating', 'created_at')
  list_filter = ('rating', 'created_at')
  search_fields = ('instructor__username', 'student__username', 'course__title')


admin.site.register(Course)
admin.site.register(Lesson)
admin.site.register(Enrollment)
admin.site.register(Certificate)
admin.site.register(Review)