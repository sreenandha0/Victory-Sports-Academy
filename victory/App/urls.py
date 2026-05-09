from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('', views.home, name='home'),

    # 🧑‍💼 Parent
    path('register/', views.register_parent, name='register_parent'),
    path('login/parent/', views.login_parent, name='login_parent'),
    path('dashboard/parent/', views.parent_dashboard, name='parent_dashboard'),
    path('enroll-child/', views.enroll_child, name='enroll_child'),
    path('child/<int:child_id>/profile/', views.create_or_update_child_profile, name='child_profile'),
    path('assessment/charts/<int:child_id>/', views.parent_assessment_charts, name='assessment_charts'),
    path('dashboard/parent/performance/',views.parent_child_selection_view, name='parent_child_selection'),

    # 🧑‍🏫 Coach
    path('register/coach/', views.register_coach, name='register_coach'),
    path('login/coach/', views.login_coach, name='login_coach'),
    path('dashboard/coach/', views.coach_dashboard, name='coach_dashboard'),
    path('assessment/create/<int:child_id>/', views.create_assessment, name='create_assessment'),
    path('performance/', views.manage_performance_view, name='manage_performance'),
    path('assessment/view/<int:child_id>/', views.view_assessments_view, name='view_assessments'), # New: for viewing past assessments
    path('child/add-to-batch/<str:batch_name>/', views.add_child_to_batch_view, name='add_child_to_batch'), # New: for adding child to a specific batch
    path('attendance/mark/', views.mark_attendance, name='mark_attendance'),
    path('dashboard/coach/coach_profile/<int:coach_id>/', views.coach_profile_view, name='coach_profile'),





    # 🛠 Admin
    path('login/admin/', views.login_admin, name='login_admin'),
    path('dashboard/admin/', views.admin_dashboard_view, name='admin_dashboard'),
    path('pending-approvals/', views.pending_coach_approvals, name='pending_coach_approvals'),
    path('approve/coach/<int:coach_id>/', views.approve_coach, name='approve_coach'),
  path(
    'dashboard/admin/manage-batches/',
    views.manage_batches,
    name='manage_batches'
),

path(
    'admin/batch/<int:batch_id>/assign-coach/',
    views.assign_coach_to_batch,
    name='assign_coach_to_batch'
),
path(
    'dashboard/admin/add-batch/',
    views.add_batch,
    name='add_batch'
),
path(
    'manage-enrolled-children/',
    views.manage_enrolled_children,
    name='manage_enrolled_children'
),
    # ✅ Utilities
    path('logout/', views.logout_view, name='logout'),
    path('ajax/check-username/', views.check_username, name='check_username'),
]

# 📂 Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
