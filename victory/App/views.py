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
    GalleryImage, Parent, PlayerAssessment, Event, EventRegistration,News
)

from .forms import (
    UserForm, ParentForm, ChildForm,
    CoachRegistrationForm, ChildProfileForm,
    PlayerAssessmentForm, AssignCoachForm, BatchForm
)


# ----------------------- COMMON VIEWS -----------------------


def home(request):
    # Coaches
    all_approved = list(Coach.objects.filter(is_approved=True))
    random_coaches = sample(all_approved, min(3, len(all_approved)))

    # Gallery
    gallery_images = GalleryImage.objects.all().order_by('-uploaded_at')

    # 🆕 News
    news_list = News.objects.all().order_by('-created_at')[:6]

    return render(request, 'index.html', {
        'coaches': random_coaches,
        'images': gallery_images,
        'news_list': news_list,   # ✅ pass to template
    })


def logout_view(request):
    # Logout View

    logout(request)
    return redirect('home')


def check_username(request):
    # Username Availability Check View

    username = request.GET.get('username', None)
    exists = User.objects.filter(username__iexact=username).exists()
    return JsonResponse({'is_taken': exists})


def is_coach(user):
    # Check if User is Coach

    return hasattr(user, 'coach_profile')


def is_parent(user):
    # Check if User is Parent

    return hasattr(user, 'parent_profile')


# ----------------------- PARENT VIEWS -----------------------
@login_required(login_url='/login/parent/')
def register_event(request, event_id, child_id):
    EventRegistration.objects.get_or_create(
        event_id=event_id,
        child_id=child_id
    )
    return redirect('/events/')

def register_parent(request):
    # Parent Registration View

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
    # Parent Login View

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


from .models import Attendance

@login_required(login_url='/login/parent/')
def parent_dashboard(request):

    try:
        parent = Parent.objects.get(user=request.user)
    except Parent.DoesNotExist:
        return HttpResponseNotFound(
            "❌ Parent profile not found. Please contact admin."
        )

    children = parent.children.all()

    # Get attendance for all children
    attendance_data = Attendance.objects.filter(
        child__in=children
    ).order_by('-date')[:10]   # last 10 records

    return render(request, 'parent_dashboard.html', {
        'parent': parent,
        'children': children,
        'attendance_data': attendance_data
    })


@login_required(login_url='/login/parent/')
def enroll_child(request):
    # Child Enrollment View

    ChildFormSet = modelformset_factory(
        Child,
        form=ChildForm,
        extra=0,
        can_delete=True
    )

    parent = Parent.objects.get(user=request.user)

    if request.method == 'POST':

        formset = ChildFormSet(
            request.POST,
            request.FILES,
            queryset=Child.objects.none()
        )

        if formset.is_valid():
            children = formset.save(commit=False)

            for child in children:
                child.parent = parent
                child.save()

            formset = ChildFormSet(queryset=Child.objects.none())

    else:
        formset = ChildFormSet(queryset=Child.objects.none())

    return render(request, 'enroll_child.html', {
        'formset': formset,
        'existing_children': parent.children.all()
    })


@login_required(login_url='/login/parent/')
def create_or_update_child_profile(request, child_id):
    # Create or Update Child Profile View

    child = get_object_or_404(
        Child,
        id=child_id,
        parent__user=request.user
    )

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

    return render(request, 'child_profile.html', {
        'form': form,
        'child': child
    })


@login_required(login_url='/login/parent/')
def parent_assessment_charts(request, child_id):
    # Parent Assessment Charts View

    child = get_object_or_404(
        Child,
        id=child_id,
        parent__user=request.user
    )

    assessments = PlayerAssessment.objects.filter(child=child)

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
    # Parent Child Selection View

    parent = get_object_or_404(Parent, user=request.user)

    children = Child.objects.filter(parent=parent)

    return render(request, 'parent_child_selection.html', {
        'children': children
    })


@login_required(login_url='/login/parent/')
def events_page(request):

    parent = Parent.objects.get(user=request.user)
    children = parent.children.all()

    events = Event.objects.all().order_by('date')

    return render(request, 'events.html', {
        'events': events,
        'children': children
    })
def parent_fees(request):
    parent = request.user.parent_profile

    children = parent.children.all()

    fees = FeeAssignment.objects.filter(child__in=children)

    return render(request, "parent_fees.html", {"fees": fees})
# ----------------------- COACH VIEWS -----------------------

def register_coach(request):
    # Coach Registration View

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

                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password
                )

                user.is_active = False
                user.save()

                coach = form.save(commit=False)
                coach.user = user
                coach.is_approved = False
                coach.save()

                messages.success(
                    request,
                    "Registration successful. Await admin approval."
                )

                return redirect('login_coach')

        else:

            print("❌ Form is invalid!")
            print(form.errors)

            messages.error(
                request,
                "There are errors in your form. "
                "Check the terminal for details."
            )

    else:
        form = CoachRegistrationForm()

    return render(request, 'register_coach.html', {
        'form': form
    })


def login_coach(request):
    # Coach Login View

    if request.method == 'POST':

        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        print("🔍 Login attempt for:", username)
        print("✅ Authenticated user:", user)

        if user and hasattr(user, 'coach_profile'):

            if not user.coach_profile.is_approved:

                messages.warning(
                    request,
                    "Your coach account is pending admin approval."
                )

                return redirect('login_coach')

            login(request, user)

            print("🎉 Login success. Redirecting to dashboard.")

            return redirect('coach_dashboard')

        else:
            messages.error(request, "Invalid coach credentials.")

    return render(request, 'login_coach.html')


@login_required(login_url='/login/coach/')
@user_passes_test(is_coach, login_url='/login/coach/')
def coach_dashboard(request):

    coach = request.user.coach_profile

    # ✅ GET ASSIGNED BATCHES
    batches = coach.batches.all().order_by('age_group')

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

    daily_quotes = [
        "Let's make today legendary.",
        "Train like a beast, shine like a champ.",
        "Your energy defines your legacy.",
        "Inspire greatness every session.",
        "Push limits. Build champions.",
        "Consistency is key, coach!",
        "Every goal begins with discipline.",
    ]

    daily_greeting = daily_quotes[
        now.timetuple().tm_yday % len(daily_quotes)
    ]

    return render(request, 'coach_dashboard.html', {
        'coach': coach,
        'batches': batches,   # ✅ ADD THIS
        'time_greeting': time_greeting,
        'daily_greeting': daily_greeting,
    })


@login_required(login_url='/login/coach/')
@user_passes_test(is_coach, login_url='/login/coach/')
def create_assessment(request, child_id):
    # Create Player Assessment View

    coach = request.user.coach_profile

    child = get_object_or_404(
        Child,
        id=child_id,
        batch__coach=coach
    )

    if request.method == 'POST':

        form = PlayerAssessmentForm(request.POST)

        if form.is_valid():

            assessment = form.save(commit=False)

            assessment.child = child
            assessment.coach = coach

            assessment.save()

            messages.success(
                request,
                "Assessment submitted successfully!"
            )

            return redirect('manage_performance')

        else:
            print("❌ Form errors:", form.errors)

    else:
        form = PlayerAssessmentForm()

    return render(request, 'create_assessment.html', {
        'form': form,
        'child': child
    })

@login_required(login_url='/login/coach/')
@user_passes_test(is_coach, login_url='/login/coach/')
def manage_performance_view(request):
    # Manage Player Performance View

    coach = request.user.coach_profile

    assigned_batches = Batch.objects.filter(
        coach=coach
    )

    grouped_children = {}

    for batch in assigned_batches:

        children_in_batch = Child.objects.filter(
            batch=batch
        ).select_related(
            'profile'
        ).prefetch_related(
            'playerassessment_set'
        )

        for child in children_in_batch:

            if hasattr(child, 'profile'):

                child.preferred_position = (
                    child.profile.preferred_position
                )

            else:

                child.preferred_position = 'N/A'

            latest_assessment = (
                child.playerassessment_set
                .order_by('-date')
                .first()
            )

            child.last_assessment_date = (
                latest_assessment.date
                if latest_assessment else None
            )

            child.has_assessments = (
                child.playerassessment_set.exists()
            )

        grouped_children[batch.name] = children_in_batch

    return render(request, 'manage_performance.html', {
        'grouped_children': grouped_children,
        'assigned_batches': assigned_batches,
    })

@login_required(login_url='/login/coach/')
@user_passes_test(is_coach, login_url='/login/coach/')
def view_assessments_view(request, child_id):
    # View Child Assessments View

    coach = request.user.coach_profile

    child = get_object_or_404(
        Child,
        id=child_id,
        batch__coach=coach
    )

    assessments = PlayerAssessment.objects.filter(
        child=child
    ).order_by('-date')

    return render(request, 'view_assessments.html', {
        'child': child,
        'assessments': assessments,
    })


@login_required(login_url='/login/coach/')
@user_passes_test(is_coach, login_url='/login/coach/')
def add_child_to_batch_view(request, batch_name):
    # Add Child to Batch View

    context = {
        'batch_name': batch_name,
        'message': (
            f"This is a placeholder view for adding "
            f"a new child to the {batch_name} batch."
        )
    }

    return render(request, 'add_child_to_batch.html', context)


@login_required(login_url='/login/coach/')
def mark_attendance(request):

    coach = request.user.coach_profile

    today = timezone.now().date()

    selected_date_str = request.GET.get(
        'date',
        str(today)
    )

    try:

        selected_date = datetime.datetime.strptime(
            selected_date_str,
            '%Y-%m-%d'
        ).date()

    except ValueError:

        selected_date = today

    selected_batch_id = request.GET.get('batch_id')

    batches = Batch.objects.filter(
        coach=coach
    )

    children = []

    selected_batch = None

    # Selected Batch
    if selected_batch_id:

        selected_batch = get_object_or_404(
            Batch,
            id=selected_batch_id,
            coach=coach
        )

        children = selected_batch.children.all()

    # SAVE ATTENDANCE
    if request.method == 'POST':

        batch_id = request.POST.get('batch_id')

        date_str = request.POST.get('date')

        try:

            attendance_date = datetime.datetime.strptime(
                date_str,
                '%Y-%m-%d'
            ).date()

        except ValueError:

            messages.error(
                request,
                "Invalid date."
            )

            return redirect('mark_attendance')

        batch = get_object_or_404(
            Batch,
            id=batch_id,
            coach=coach
        )

        children = batch.children.all()

        for child in children:

            status = request.POST.get(
                f'status_{child.id}',
                'Present'
            )

            remarks = request.POST.get(
                f'remarks_{child.id}',
                ''
            )

            Attendance.objects.update_or_create(

                child=child,
                date=attendance_date,

                defaults={

                    'coach': coach,

                    'batch': batch,

                    'status': status,

                    'remarks': remarks
                }
            )

        messages.success(
            request,
            "Attendance marked successfully."
        )

        return redirect(
            f'/attendance/mark/?batch_id={batch.id}&date={attendance_date}'
        )

    # Existing Attendance
    existing_attendance = []

    if selected_batch:

        existing_attendance = Attendance.objects.filter(
            batch=selected_batch,
            date=selected_date
        ).select_related('child')

    existing_data = {

        attendance.child.id: attendance

        for attendance in existing_attendance
    }

    # Attendance Summary
    past_attendance_summary = Attendance.objects.filter(
        coach=coach
    ).values(
        'date',
        'batch__name',
        'batch__id'
    ).annotate(

        present=Count(
            'id',
            filter=Q(status='Present')
        ),

        absent=Count(
            'id',
            filter=Q(status='Absent')
        ),

        leave=Count(
            'id',
            filter=Q(status='Leave')
        )

    ).order_by('-date')[:5]

    context = {

        'batches': batches,

        'selected_batch': selected_batch,

        'children': children,

        'selected_date': selected_date,

        'existing_data': existing_data,

        'past_attendance_summary': past_attendance_summary,
    }

    return render(
        request,
        'attendance_portal.html',
        context
    )

def coach_profile_view(request, coach_id):
    # Coach Profile View

    coach = get_object_or_404(Coach, id=coach_id)

    return render(request, 'coach_profile.html', {
        'coach': coach
    })


# ----------------------- ADMIN VIEWS -----------------------

def login_admin(request):
    # Admin Login View

    if request.method == 'POST':

        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user and user.is_staff:

            login(request, user)

            return redirect('admin_dashboard')

        else:
            messages.error(
                request,
                "Invalid credentials or not authorized."
            )

    return render(request, 'admin_login.html')


def is_admin(user):
    # Check if User is Admin

    return user.is_superuser


@login_required(login_url='/login/admin/')
@user_passes_test(is_admin, login_url='/login/admin/')
def admin_dashboard_view(request):
    # Admin Dashboard View

    return render(request, 'admin_dashboard.html', {
        'admin_username': request.user.username
    })


@login_required(login_url='/login/admin/')
@user_passes_test(is_admin, login_url='/login/admin/')
def approve_coach(request, coach_id):
    # Approve Coach View

    coach = get_object_or_404(Coach, id=coach_id)

    coach.is_approved = True

    coach.user.is_active = True
    coach.user.save()

    coach.save()

    messages.success(
        request,
        f"{coach.full_name} has been approved."
    )

    return redirect('pending_coach_approvals')


@login_required(login_url='/login/admin/')
@user_passes_test(is_admin, login_url='/login/admin/')
def pending_coach_approvals(request):
    # Pending Coach Approvals View

    pending_coaches = Coach.objects.filter(
        is_approved=False
    )

    approved_coaches = Coach.objects.filter(
        is_approved=True
    )

    return render(request, 'pending_coach_approvals.html', {
        'coaches': pending_coaches,
        'approved_coaches': approved_coaches
    })


def gallery_view(request):
    # Gallery Display View

    images = GalleryImage.objects.all().order_by(
        '-uploaded_at'
    )

    return render(request, 'gallery.html', {
        'images': images
    })


@login_required(login_url='/login/admin/')
@user_passes_test(is_admin, login_url='/login/admin/')
def manage_batches(request):
    # Manage Batches View

    batches = Batch.objects.all()

    return render(request, 'manage_batches.html', {
        'batches': batches
    })


@login_required(login_url='/login/admin/')
@user_passes_test(is_admin, login_url='/login/admin/')
def assign_coach_to_batch(request, batch_id):
    # Assign Coach to Batch View

    batch = get_object_or_404(Batch, id=batch_id)

    if request.method == 'POST':

        form = AssignCoachForm(
            request.POST,
            instance=batch
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Coach assigned successfully."
            )

            return redirect('manage_batches')

    else:
        form = AssignCoachForm(instance=batch)

    return render(request, 'assign_coach.html', {
        'form': form,
        'batch': batch
    })


@login_required(login_url='/login/admin/')
@user_passes_test(is_admin, login_url='/login/admin/')
def add_batch(request):
    # Add Batch View

    if request.method == 'POST':

        form = BatchForm(request.POST)

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Batch added successfully."
            )

            return redirect('manage_batches')

    else:
        form = BatchForm()

    return render(request, 'add_batch.html', {
        'form': form
    })


@login_required(login_url='/login/admin/')
@user_passes_test(lambda u: u.is_superuser)
def manage_enrolled_children(request):
    # Admin View - View All Enrolled Children + Assessment Details

    children = Child.objects.select_related(
        'parent',
        'batch'
    ).prefetch_related(
        'playerassessment_set'
    ).all().order_by('name')

    return render(request, 'manage_enrolled_children.html', {
        'children': children
    })
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import Event

@login_required(login_url='/login/admin/')
def event_dashboard(request):

    if request.method == 'POST':
        Event.objects.create(
            title=request.POST.get('title'),
            description=request.POST.get('description'),
            date=request.POST.get('date'),
            time=request.POST.get('time'),
            location=request.POST.get('location')
        )
        return redirect('/events-admin/')

    events = Event.objects.all().order_by('-date')

    return render(request, 'event_dashboard.html', {
        'events': events
    })
from .models import Fee, FeeAssignment, Child

def create_fee(request):
    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        amount = request.POST.get("amount")
        due_date = request.POST.get("due_date")
        batch_id = request.POST.get("batch")

        batch = Batch.objects.get(id=batch_id)

        fee = Fee.objects.create(
            title=title,
            description=description,
            amount=amount,
            due_date=due_date,
            batch=batch
        )

        # Assign to children in that batch
        children = Child.objects.filter(batch=batch)

        for child in children:
            FeeAssignment.objects.create(
                fee=fee,
                child=child
            )

        return redirect("fee_list")

    batches = Batch.objects.all()
    return render(request, "create_fee.html", {"batches": batches})

from django.contrib import messages

def pay_fee(request, id):
    fee = FeeAssignment.objects.get(id=id)

    fee.is_paid = True
    fee.paid_at = timezone.now()
    fee.save()

    messages.success(request, "Payment Successful ✅")

    return redirect("parent_fees")