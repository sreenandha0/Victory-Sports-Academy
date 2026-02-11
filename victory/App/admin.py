from django.contrib import admin
from .models import Parent, Child, ChildProfile, PlayerAssessment, GalleryImage, Attendance
from .models import Coach

admin.site.register(Parent)
admin.site.register(Child)
admin.site.register(ChildProfile)
admin.site.register(PlayerAssessment)
admin.site.register(GalleryImage)
admin.site.register(Attendance)






@admin.register(Coach)
class CoachAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'is_approved']
    list_filter = ['is_approved']
    search_fields = ['full_name', 'email']
