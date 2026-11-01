import uuid

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.validators import validate_email, MinLengthValidator, MaxLengthValidator
from django.core.exceptions import ValidationError
from django.utils import timezone

from . import Role


class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError('Username is required')
        if not email:
            raise ValueError('Email is required')
        
        try:
            validate_email(email)
        except ValidationError:
            raise ValueError('Invalid email address')
        
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, email, password, **extra_fields)


class User(AbstractBaseUser):
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(
        max_length=150,
        unique=True,
        validators=[
            MinLengthValidator(4, message="Username must be at least 3 characters long."),
            MaxLengthValidator(20, message="Username must be at most 20 characters long.")
        ],
        help_text=(
            "Required. 20 characters or fewer. Letters, digits and @/./+/-/_ only."
        )
    )
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(unique=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  
    is_superuser = models.BooleanField(default=False)
    
    date_joined = models.DateTimeField(("date joined"), default=timezone.now)
    
    last_updated = models.DateTimeField(auto_now=True)
    
    objects = UserManager()

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]
    
    is_bootstrap_admin = models.BooleanField(default=False)
    
    failed_login_attempts = models.PositiveSmallIntegerField(default=0, blank=True)
    is_locked = models.BooleanField(default=False)
    locked_at = models.DateTimeField(null=True, blank=True)
    
    def lock_account(self):
        self.is_locked = True
        self.locked_at = timezone.now()
        self.save(update_fields=['is_locked', 'locked_at'])

    def unlock_account(self):
        self.is_locked = False
        self.failed_login_attempts = 0
        self.locked_at = None
        self.save(update_fields=['is_locked', 'failed_login_attempts', 'locked_at'])
        
    def failed_attempt(self):
        self.failed_login_attempts += 1
        self.save(update_fields=['failed_login_attempts'])

    def reset_login_attempts(self):
        if self.failed_login_attempts > 0:
            self.failed_login_attempts = 0
            self.save(update_fields=['failed_login_attempts'])

    def has_perm(self, perm, obj=None):
        return self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_superuser
    
    def __str__(self):
        return self.get_username()
    
    class Meta:
        db_table = "users"
        verbose_name = "user"
        verbose_name_plural = "users"