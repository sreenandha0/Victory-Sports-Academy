import datetime
import json
import random
from random import sample
from django.db.models import Count, Q

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Avg, Max
from django.forms import modelformset_factory
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import (
    Attendance, Batch, Child, ChildProfile, Coach,
    GalleryImage, Parent, PlayerAssessment
)

from .forms import (
    UserForm, ParentForm, ChildForm,
    CoachRegistrationForm, ChildProfileForm, PlayerAssessmentForm
)




# ----------------------- COMMON VIEWS -----------------------

def home(request):
    all_approved = list(Coach.objects.filter(is_approved=True))
    random_coaches = sample(all_approved, min(3, len(all_approved)))
    
    gallery_images = GalleryImage.objects.all().order_by('-uploaded_at')  # or [:8] to limit

    return render(request, 'index.html', {
        'coaches': random_coaches,
        'images': gallery_images,
    })

def logout_view(request):
    logout(request)
    return redirect('home')

def check_username(request):
    username = request.GET.get('username', None)
    exists = User.objects.filter(username__iexact=username).exists()
    return JsonResponse({'is_taken': exists})

def is_coach(user):
    return hasattr(user, 'coach')

def is_parent(user):
    return hasattr(user, 'parent')


# ----------------------- PARENT VIEWS -----------------------

def register_parent(request):
    if request.method == 'POST':
        user_form = UserForm(request.POST)
        parent_form = ParentForm(request.POST)
        if user_form.is_valid() and parent_form.is_valid():
            user = user_form.save(commit=False)
            user.set_password(user_form.cleaned_data['password'])
            user.save()
            parent = parent_form.save(commit=False)
            parent.user = user
            parent.save()
            login(request, user)
            return redirect('login_parent')
    else:
        user_form = UserForm()
        parent_form = ParentForm()
    return render(request, 'register_parent.html', {
        'user_form': user_form,
        'parent_form': parent_form
    })

def login_parent(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user and hasattr(user, 'parent_profile'):
            login(request, user)
            return redirect('parent_dashboard')
        else:
            messages.error(request, "Invalid parent credentials.")
    return render(request, 'login_parent.html')

@login_required(login_url='/login/parent/')
def parent_dashboard(request):
    try:
        parent = Parent.objects.get(user=request.user)
    except Parent.DoesNotExist:
        return HttpResponseNotFound("❌ Parent profile not found. Please contact admin.")

    children = parent.children.all()
    return render(request, 'parent_dashboard.html', {
        'parent': parent,
        'children': children
    })

@login_required(login_url='/login/parent/')
def enroll_child(request):
    ChildFormSet = modelformset_factory(Child, form=ChildForm, extra=0, can_delete=True)
    parent = Parent.objects.get(user=request.user)

    if request.method == 'POST':
        formset = ChildFormSet(request.POST, request.FILES, queryset=Child.objects.none())
        if formset.is_valid():
            children = formset.save(commit=False)
            for child in children:
                child.parent = parent
                child.save()
            formset = ChildFormSet(queryset=Child.objects.none())  # reset
    else:
        formset = ChildFormSet(queryset=Child.objects.none())

    return render(request, 'enroll_child.html', {
        'formset': formset,
        'existing_children': parent.children.all()
    })

@login_required(login_url='/login/parent/')
def create_or_update_child_profile(request, child_id):
    child = get_object_or_404(Child, id=child_id, parent__user=request.user)
    profile = getattr(child, 'profile', None)

    if request.method == 'POST':
        form = ChildProfileForm(request.POST, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.child = child
            profile.save()
            return redirect('parent_dashboard')
    else:
        form = ChildProfileForm(instance=profile)

    return render(request, 'child_profile.html', {'form': form, 'child': child})


@login_required(login_url='/login/parent/')
def parent_assessment_charts(request, child_id):
    # Ensure the child belongs to the logged-in parent
    child = get_object_or_404(Child, id=child_id, parent__user=request.user)
    
    assessments = PlayerAssessment.objects.filter(child=child)

    # Calculate average scores
    avg_data = assessments.aggregate(
        spatial_awareness=Avg('spatial_awareness'),
        decision_making=Avg('decision_making'),
        ball_control=Avg('ball_control'),
        passing=Avg('passing'),
        stamina=Avg('stamina'),
        speed=Avg('speed'),
        confidence=Avg('confidence'),
    )

    context = {
        'child': child,
        'avg_data': avg_data,
    }
    return render(request, 'assessment_charts.html', context)


@login_required(login_url='/login/parent/')
def parent_child_selection_view(request):
    # Get the logged-in parent
    parent = get_object_or_404(Parent, user=request.user)
    children = Child.objects.filter(parent=parent)

    return render(request, 'parent_child_selection.html', {
        'children': children
    })


# ----------------------- COACH VIEWS -----------------------


#----------------------- COACH REGISTRATION -----------------------
def register_coach(request):
    if request.method == 'POST':
        form = CoachRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            if User.objects.filter(username=username).exists():
                messages.error(request, "Username already taken.")
            elif User.objects.filter(email=email).exists():
                messages.error(request, "Email already registered.")
            else:
                user = User.objects.create_user(username=username, email=email, password=password)
                user.is_active = False  # wait for admin approval
                user.save()

                coach = form.save(commit=False)
                coach.user = user
                coach.is_approved = False
                coach.save()

                messages.success(request, "Registration successful. Await admin approval.")
                return redirect('login_coach')
        else:
            # <<< DEBUG BLOCK >>>
            print("❌ Form is invalid!")
            print(form.errors)  # prints field-specific errors in terminal
            messages.error(request, "There are errors in your form. Check the terminal for details.")
    else:
        form = CoachRegistrationForm()

    return render(request, 'register_coach.html', {'form': form})



#----------------------- COACH LOGIN -----------------------
def login_coach(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        print("🔍 Login attempt for:", username)
        print("✅ Authenticated user:", user)

        if user and hasattr(user, 'coach_profile'):
            if not user.coach_profile.is_approved:
                messages.warning(request, "Your coach account is pending admin approval.")
                return redirect('login_coach')

            login(request, user)
            print("🎉 Login success. Redirecting to dashboard.")
            return redirect('coach_dashboard')
        else:
            messages.error(request, "Invalid coach credentials.")
    return render(request, 'login_coach.html')

def is_coach(user):
    return hasattr(user, 'coach_profile')

import datetime
import random

# ----------------------- COACH DASHBOARD -----------------------
@login_required(login_url='/login/coach/')
@user_passes_test(is_coach, login_url='/login/coach/')
def coach_dashboard(request):
    coach = request.user.coach_profile

    # 🌞 Determine greeting based on time
    now = datetime.datetime.now()
    hour = now.hour

    if hour < 12:
        time_greeting = "Good morning"
    elif 12 <= hour < 17:
        time_greeting = "Good afternoon"
    elif 17 <= hour < 21:
        time_greeting = "Good evening"
    else:
        time_greeting = "Good night"

    # 📅 Daily rotating greetings (change every day)
    daily_quotes = [
        "Let's make today legendary.",
        "Train like a beast, shine like a champ.",
        "Your energy defines your legacy.",
        "Inspire greatness every session.",
        "Push limits. Build champions.",
        "Consistency is key, coach!",
        "Every goal begins with discipline.",
    ]
    # rotate quote daily by using day of year
    daily_greeting = daily_quotes[now.timetuple().tm_yday % len(daily_quotes)]

    return render(request, 'coach_dashboard.html', {
        'coach': coach,
        'time_greeting': time_greeting,
        'daily_greeting': daily_greeting,
    })


# ----------------------- CREATE ASSESSMENT VIEW -----------------------
@login_required
@user_passes_test(is_coach)
def create_assessment(request, child_id):
    child = get_object_or_404(Child, id=child_id)
    if request.method == 'POST':
        form = PlayerAssessmentForm(request.POST)
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.child = child
            assessment.coach = request.user.coach_profile  # ✅ use correct related name
            assessment.save()
            messages.success(request, "Assessment submitted successfully!")
            return redirect('coach_dashboard')
        else:
            print("❌ Form errors:", form.errors)  # Add this
    else:
        form = PlayerAssessmentForm()
    return render(request, 'create_assessment.html', {'form': form, 'child': child})


# ----------------------- MANAGE PERFORMANCE VIEW -----------------------
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Max # Max is not strictly needed for .first() but good to keep in mind for aggregates
from .models import Child, ChildProfile, PlayerAssessment # Import all necessary models
from datetime import date # Import date for current date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Max
from .models import Child, ChildProfile, PlayerAssessment # Import all necessary models
from datetime import date # Import date for current date

# Assuming you have a utility function 'is_coach' in a utils.py or similar file
# Example:
def is_coach(user):
    """
    Checks if the given user is a coach and is approved.
    """
    return hasattr(user, 'coach_profile') and user.coach_profile.is_approved

@login_required(login_url='/login/coach/')
@user_passes_test(is_coach, login_url='/login/coach/')
def manage_performance_view(request):
    """
    View to manage player performance, displaying children grouped by age batch.
    Fetches child profiles and their latest assessment dates.
    """
    batches = ['U8', 'U10', 'U12', 'U14', 'U16', 'U18']
    grouped_children = {}

    for batch in batches:
        # Fetch children in the current batch
        # Use select_related('profile') for the OneToOneField relationship to ChildProfile
        # Use prefetch_related('playerassessment_set') for the ForeignKey relationship to PlayerAssessment
        children_in_batch = Child.objects.filter(age_group=batch).select_related('profile').prefetch_related('playerassessment_set')

        for child in children_in_batch:
            # Attach preferred_position from ChildProfile
            # Check if a ChildProfile exists for the child to avoid DoesNotExist error
            if hasattr(child, 'profile'):
                child.preferred_position = child.profile.preferred_position
            else:
                child.preferred_position = 'N/A' # Default if no profile exists

            # Attach last_assessment_date and has_assessments flag
            # Order by '-date' to get the most recent assessment
            latest_assessment = child.playerassessment_set.order_by('-date').first()
            child.last_assessment_date = latest_assessment.date if latest_assessment else None
            child.has_assessments = child.playerassessment_set.exists() # Check if any assessments exist

        grouped_children[batch] = children_in_batch

    return render(request, 'manage_performance.html', {
        'grouped_children': grouped_children,
        'batches': batches, # Pass batches list for the navbar dropdown
    })

@login_required(login_url='/login/coach/')
@user_passes_test(is_coach, login_url='/login/coach/')
def view_assessments_view(request, child_id):
    """
    Placeholder view to display past assessments for a specific child.
    You will need to implement the actual logic to fetch and display assessments.
    """
    child = get_object_or_404(Child, id=child_id)
    assessments = PlayerAssessment.objects.filter(child=child).order_by('-date')
    
    context = {
        'child': child,
        'assessments': assessments,
        'message': f"Displaying assessments for {child.name}. This is a placeholder view."
    }
    return render(request, 'view_assessments.html', context) # You'll need to create view_assessments.html

@login_required(login_url='/login/coach/')
@user_passes_test(is_coach, login_url='/login/coach/')
def add_child_to_batch_view(request, batch_name):
    """
    Placeholder view to handle adding a new child to a specific batch.
    You will need to implement the actual form and saving logic here.
    """
    context = {
        'batch_name': batch_name,
        'message': f"This is a placeholder view for adding a new child to the {batch_name} batch."
    }
    # In a real application, you would render a form here, e.g.:
    # from .forms import ChildForm
    # form = ChildForm(initial={'age_group': batch_name})
    # context['form'] = form
    return render(request, 'add_child_to_batch.html', context) # You'll need to create add_child_to_batch.html

# You will also need to ensure your urls.py has entries for:
# - 'create_assessment/<int:child_id>/' (already exists)
# - 'view_assessments/<int:child_id>/' (now has a view function)
# - 'add_child_to_batch/<str:batch_name>/' (now has a view function)



@login_required(login_url='/login/coach/')
def mark_attendance(request):
    coach = request.user.coach_profile
    today = timezone.now().date()
    selected_date_str = request.GET.get('date') or str(today)
    selected_date = datetime.datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    selected_batch_id = request.GET.get('batch_id')

    batches = Batch.objects.filter(coach=coach)

    children = []
    selected_batch = None

    if selected_batch_id:
        selected_batch = get_object_or_404(Batch, id=selected_batch_id)
        children = selected_batch.children.all()

    if request.method == 'POST':
        batch_id = request.POST.get('batch_id')
        date_str = request.POST.get('date')
        remarks = request.POST.get('remarks')
        date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()

        batch = get_object_or_404(Batch, id=batch_id)
        children = batch.children.all()

        # Delete old attendance if exists
        Attendance.objects.filter(batch=batch, date=date_obj).delete()

        for child in children:
            status = request.POST.get(f'status_{child.id}')
            individual_remarks = request.POST.get(f'remarks_{child.id}')
            Attendance.objects.create(
                child=child,
                coach=coach,
                batch=batch,
                date=date_obj,
                status=status,
                remarks=individual_remarks or remarks
            )

        return redirect('mark_attendance')

    # Fetch past 5 entries to display inline
    past_attendance_summary = Attendance.objects.filter(
        coach=coach
    ).exclude(date=today).values('date', 'batch__name').annotate(
        present=Count('id', filter=Q(status='Present')),
        absent=Count('id', filter=Q(status='Absent')),
        leave=Count('id', filter=Q(status='Leave'))
    ).order_by('-date')[:5]

    # Pre-fill existing attendance for selected batch/date (for editing)
    existing_attendance = Attendance.objects.filter(batch=selected_batch, date=selected_date).select_related('child') if selected_batch else []

    existing_data = {att.child.id: att for att in existing_attendance}

    context = {
        'batches': batches,
        'selected_batch': selected_batch,
        'children': children,
        'today': today,
        'selected_date': selected_date,
        'existing_data': existing_data,
        'past_attendance_summary': past_attendance_summary,
    }
    return render(request, 'attendance_portal.html', context)


def coach_profile_view(request, coach_id):
    coach = get_object_or_404(Coach, id=coach_id)
    return render(request, 'coach_profile.html', {'coach': coach})




# ----------------------- ADMIN VIEWS -----------------------

def login_admin(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user and user.is_staff:
            login(request, user)
            return redirect('admin_dashboard')
        else:
            messages.error(request, "Invalid credentials or not authorized.")
    return render(request, 'admin_login.html')

def is_admin(user):
    return user.is_superuser

@login_required(login_url='/login/admin/')
@user_passes_test(is_admin, login_url='/login/admin/')
def admin_dashboard_view(request):
    return render(request, 'admin_dashboard.html', {
        'admin_username': request.user.username
    })

@login_required(login_url='/login/admin/')
@user_passes_test(is_admin, login_url='/login/admin/')
def approve_coach(request, coach_id):
    coach = get_object_or_404(Coach, id=coach_id)
    coach.is_approved = True
    coach.user.is_active = True
    coach.user.save()
    coach.save()
    messages.success(request, f"{coach.full_name} has been approved.")
    return redirect('pending_coach_approvals')
@login_required(login_url='/login/admin/')
@user_passes_test(is_admin, login_url='/login/admin/')
def pending_coach_approvals(request):
    pending_coaches = Coach.objects.filter(is_approved=False)
    approved_coaches = Coach.objects.filter(is_approved=True)

    return render(request, 'pending_coach_approvals.html', {
        'coaches': pending_coaches,
        'approved_coaches': approved_coaches
    })

#image Gallery
def gallery_view(request):
    images = GalleryImage.objects.all().order_by('-uploaded_at')  # latest first
    return render(request, 'gallery.html', {'images': images})
