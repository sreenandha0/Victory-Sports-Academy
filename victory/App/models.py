from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date

# ----------------------------
# COACH MODEL
# ----------------------------
class Coach(models.Model):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='coach_profile', null=True, blank=True)
    full_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    nationality = models.CharField(max_length=50)
    contact_number = models.CharField(max_length=15)
    email = models.EmailField(unique=True)
    address = models.TextField()
    photo = models.ImageField(upload_to='coach_photos/', blank=True, null=True)
    qualification = models.CharField(max_length=100)
    experience_years = models.PositiveIntegerField(default=0)
    declaration = models.BooleanField(default=False)
    date_registered = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return self.full_name


# ----------------------------
# BATCH MODEL
# ----------------------------
class Batch(models.Model):
    AGE_GROUP_CHOICES = [
        ('U8', 'Under 8'),
        ('U10', 'Under 10'),
        ('U12', 'Under 12'),
        ('U14', 'Under 14'),
        ('U16', 'Under 16'),
        ('U18', 'Under 18'),
    ]

    name = models.CharField(max_length=100)
    sport = models.CharField(max_length=50)
    age_group = models.CharField(max_length=20, choices=AGE_GROUP_CHOICES)
    coach = models.ForeignKey(Coach, on_delete=models.SET_NULL, null=True, related_name='batches')

    def __str__(self):
        return f"{self.name} ({self.age_group})"


# ----------------------------
# PARENT MODEL
# ----------------------------
class Parent(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='parent_profile')
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)

    def __str__(self):
        return self.full_name


# ----------------------------
# CHILD MODEL
# ----------------------------
class Child(models.Model):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]
    AGE_GROUP_CHOICES = Batch.AGE_GROUP_CHOICES

    batch = models.ForeignKey('Batch', on_delete=models.SET_NULL, null=True, related_name='children')
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE, related_name='children')
    name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    dob = models.DateField()
    school = models.CharField(max_length=100)
    place = models.CharField(max_length=100)
    profile_image = models.ImageField(upload_to='child_profiles/', blank=True, null=True)
    age_group = models.CharField(max_length=10, choices=AGE_GROUP_CHOICES, default='U10')

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.dob:
            today = date.today()
            age = today.year - self.dob.year - ((today.month, today.day) < (self.dob.month, self.dob.day))

            if age <= 8:
                self.age_group = 'U8'
            elif age <= 10:
                self.age_group = 'U10'
            elif age <= 12:
                self.age_group = 'U12'
            elif age <= 14:
                self.age_group = 'U14'
            elif age <= 16:
                self.age_group = 'U16'
            else:
                self.age_group = 'U18'

        # Auto-assign batch based on age group
        from .models import Batch
        if not self.batch or self.batch.age_group != self.age_group:
            batch_match = Batch.objects.filter(age_group=self.age_group).first()
            if batch_match:
                self.batch = batch_match

        super().save(*args, **kwargs)


# ----------------------------
# CHILD PROFILE MODEL
# ----------------------------
PREFERRED_POSITION_CHOICES = [
    ('GK', 'Goalkeeper'),
    ('CB', 'Centre Back'),
    ('LB', 'Left Back'),
    ('RB', 'Right Back'),
    ('CM', 'Central Midfielder'),
    ('CAM', 'Attacking Midfielder'),
    ('CDM', 'Defensive Midfielder'),
    ('LM', 'Left Midfielder'),
    ('RM', 'Right Midfielder'),
    ('LW', 'Left Winger'),
    ('RW', 'Right Winger'),
    ('ST', 'Striker'),
]

class ChildProfile(models.Model):
    child = models.OneToOneField(Child, on_delete=models.CASCADE, related_name='profile')
    preferred_position = models.CharField(max_length=20, choices=PREFERRED_POSITION_CHOICES, blank=True)
    playing_background = models.TextField(blank=True)
    height_cm = models.FloatField(null=True, blank=True)
    weight_kg = models.FloatField(null=True, blank=True)
    medical_issues = models.TextField(blank=True)
    consent_signed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.child.name}'s Profile"

    @property
    def parent(self):
        return self.child.parent


# ----------------------------
# ATTENDANCE MODEL
# ----------------------------
class Attendance(models.Model):
    STATUS_CHOICES = [
        ('Present', 'Present'),
        ('Absent', 'Absent'),
        ('Leave', 'Leave'),
    ]

    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='attendances')
    coach = models.ForeignKey(Coach, on_delete=models.CASCADE, related_name='attendances_taken')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='attendance_batch', null=True, blank=True)
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Present')
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('child', 'date')

    def __str__(self):
        return f"{self.child.name} - {self.status} on {self.date}"

    def save(self, *args, **kwargs):
        if not self.batch and self.child:
            self.batch = self.child.batch
        super().save(*args, **kwargs)


# ----------------------------
# PLAYER ASSESSMENT MODEL
# ----------------------------
class PlayerAssessment(models.Model):
    child = models.ForeignKey(Child, on_delete=models.CASCADE)
    coach = models.ForeignKey(Coach, on_delete=models.SET_NULL, null=True)
    date = models.DateField(auto_now_add=True)
    position = models.CharField(max_length=50)

    # Cognitive / Tactical
    spatial_awareness = models.IntegerField()
    decision_making = models.IntegerField()
    understanding_position = models.IntegerField()
    off_the_ball_movement = models.IntegerField()
    game_intelligence = models.IntegerField()

    # Technical
    ball_control = models.IntegerField()
    passing = models.IntegerField()
    shooting = models.IntegerField()
    dribbling = models.IntegerField()
    tackling = models.IntegerField()

    # Physical
    speed = models.IntegerField()
    stamina = models.IntegerField()
    strength = models.IntegerField()
    agility = models.IntegerField()
    balance = models.IntegerField()

    # Psychological
    confidence = models.IntegerField()
    leadership = models.IntegerField()
    teamwork = models.IntegerField()
    discipline = models.IntegerField()
    focus = models.IntegerField()

    coach_summary = models.TextField()
    strengths = models.TextField()
    improvements = models.TextField()
    suggested_drills = models.TextField()
    short_term_goal = models.TextField()
    long_term_goal = models.TextField()

    def __str__(self):
        return f"{self.child} - {self.date}"


# ----------------------------
# GALLERY MODEL
# ----------------------------
class GalleryImage(models.Model):
    title = models.CharField(max_length=100)
    image = models.ImageField(upload_to='gallery_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
