from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

COLLEGE_CHOICES = [
    ('College of Computer Studies', 'College of Computer Studies'),
    ('College of Education', 'College of Education'),
    ('College of Agriculture', 'College of Agriculture'),
]

ADMIN_FULLNAME = 'AdminSCS'
ADMIN_STUDENT_ID = 1234567
EDIT_WINDOW_SECONDS = 30


class Account(models.Model):
    ROLE_STUDENT = 'student'
    ROLE_STAFF = 'staff'
    ROLE_ADMIN = 'admin'
    ROLE_CHOICES = [
        (ROLE_STUDENT, 'Student'),
        (ROLE_STAFF, 'Staff'),
        (ROLE_ADMIN, 'Admin'),
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    Fullname = models.CharField(max_length=100)
    StudentID = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(9999999)]
    )
    College = models.CharField(max_length=100, choices=COLLEGE_CHOICES, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    last_seen_concerns = models.DateTimeField(null=True, blank=True)
    last_seen_public_chat = models.DateTimeField(null=True, blank=True)
    last_active_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ['role', 'Fullname']

    def __str__(self):
        return f"{self.Fullname} ({self.get_role_display()})"

    @property
    def can_manage(self):
        return self.role in (self.ROLE_STAFF, self.ROLE_ADMIN)


class StudentConcern(models.Model):
    COLLEGE_CHOICES = COLLEGE_CHOICES
    CATEGORY_CHOICES = [
        ('Academic', 'Academic'),
        ('Facilities', 'Facilities'),
        ('Financial', 'Financial'),
        ('Welfare & Safety', 'Welfare & Safety'),
        ('Administrative', 'Administrative'),
        ('Other', 'Other'),
    ]
    PRIORITY_CHOICES = [
        ('Low', 'Low'),
        ('Normal', 'Normal'),
        ('High', 'High'),
        ('Urgent', 'Urgent'),
    ]
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Review', 'In Review'),
        ('In Progress', 'In Progress'),
        ('Resolved', 'Resolved'),
        ('Rejected', 'Rejected'),
    ]

    author = models.ForeignKey(
        Account, null=True, blank=True, on_delete=models.SET_NULL, related_name='concerns'
    )
    Fullname = models.CharField(max_length=100)
    StudentID = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(9999999)]
    )
    College = models.CharField(max_length=100, choices=COLLEGE_CHOICES)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='Other')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Normal')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    Concern = models.CharField(max_length=999)
    evidence = models.ImageField(upload_to='evidence/%Y/%m/', blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f"{self.Fullname} ({self.StudentID})"

    def owned_by(self, account):
        if account is None:
            return False
        if self.author_id is not None:
            return self.author_id == account.id
        return (
            account.role == Account.ROLE_STUDENT
            and self.StudentID is not None
            and self.StudentID == account.StudentID
            and self.Fullname.lower() == account.Fullname.lower()
        )

    def delete(self, *args, **kwargs):
        storage, name = self.evidence.storage, self.evidence.name
        result = super().delete(*args, **kwargs)
        if name:
            storage.delete(name)
        return result


class ConcernReply(models.Model):
    KIND_FEEDBACK = 'Feedback'
    KIND_REPORT = 'Action Report'
    KIND_CHOICES = [
        (KIND_FEEDBACK, 'Feedback'),
        (KIND_REPORT, 'Action Report'),
    ]

    concern = models.ForeignKey(StudentConcern, on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(Account, null=True, blank=True, on_delete=models.SET_NULL)
    author_name = models.CharField(max_length=100)
    author_role = models.CharField(max_length=10)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default=KIND_FEEDBACK)
    message = models.CharField(max_length=1000)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self):
        return f"{self.kind} on #{self.concern_id} by {self.author_name}"


class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('login', 'Login'),
        ('login_failed', 'Failed login'),
        ('logout', 'Logout'),
        ('view_dashboard', 'Viewed dashboard'),
        ('search', 'Searched'),
        ('view_concern', 'Viewed concern'),
        ('submit_concern', 'Submitted concern'),
        ('update_concern', 'Edited concern'),
        ('delete_concern', 'Deleted concern'),
        ('change_status', 'Changed status'),
        ('reply', 'Posted reply'),
        ('export', 'Exported CSV'),
        ('chat_message', 'Sent chat message'),
        ('chat_edit', 'Edited chat message'),
        ('chat_delete', 'Deleted chat message'),
        ('private_message', 'Sent private message'),
        ('private_edit', 'Edited private message'),
        ('private_delete', 'Deleted private message'),
        ('create_account', 'Registered account'),
        ('update_account', 'Edited account'),
        ('delete_account', 'Deleted account'),
    ]

    account = models.ForeignKey(Account, null=True, blank=True, on_delete=models.SET_NULL)
    Fullname = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=10, blank=True)
    StudentID = models.CharField(max_length=20, blank=True)
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    detail = models.CharField(max_length=300, blank=True)
    ip = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f"{self.Fullname} - {self.action}"


class MessageBase(models.Model):
    message = models.CharField(max_length=500)
    attachment = models.FileField(upload_to='chat_uploads/%Y/%m/', null=True, blank=True)
    attachment_name = models.CharField(max_length=255, blank=True)
    attachment_type = models.CharField(max_length=20, blank=True)
    edited = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True)
    updated_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        abstract = True

    @property
    def seconds_left(self):
        elapsed = (timezone.now() - self.created_at).total_seconds()
        return max(0, int(EDIT_WINDOW_SECONDS - elapsed))

    @property
    def within_window(self):
        return self.deleted_at is None and self.seconds_left > 0

    def mark_edited(self, text):
        self.message = text
        self.edited = True
        self.updated_at = timezone.now()
        self.save(update_fields=['message', 'edited', 'updated_at'])

    def mark_deleted(self):
        now = timezone.now()
        self.message = ''
        self.deleted_at = now
        self.updated_at = now
        self.save(update_fields=['message', 'deleted_at', 'updated_at'])


class ChatMessage(MessageBase):
    reply_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='thread_replies')
    account = models.ForeignKey(Account, null=True, blank=True, on_delete=models.SET_NULL)
    author_name = models.CharField(max_length=100)
    author_role = models.CharField(max_length=10)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.author_name}: {self.message[:40]}"


class PrivateMessage(MessageBase):
    reply_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='thread_replies')
    sender = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='received_messages')
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.sender_id} to {self.recipient_id}"


class ChatReaction(models.Model):
    REACTION_CHOICES = [(v, v) for v in ('smile','open_mouth','grin','sweat_laugh','laugh','sad','cry','surprised','angry','grimace','kiss','heart_eyes','pleading','tongue','cool','meh','smirk','heart','like','dislike','handshake','heart_hands','clap','folded_hands','ok_hand','index_up','wave','question','exclamation','one','two','three','four','five','point','peace','open_hand','fist','fire','hug','red_heart','fireworks','cake','party','sparkles','star','thumbs_up','thumbs_down','laughing','sob','thinking','rocket','tada','gift','balloon','coffee','pizza','sun','moon','check','x_mark')]
    message = models.ForeignKey(ChatMessage, null=True, blank=True, on_delete=models.CASCADE, related_name='reactions')
    private_message = models.ForeignKey(PrivateMessage, null=True, blank=True, on_delete=models.CASCADE, related_name='reactions')
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    reaction = models.CharField(max_length=20, choices=REACTION_CHOICES)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['message', 'account'], condition=models.Q(message__isnull=False), name='uniq_public_message_reaction'),
            models.UniqueConstraint(fields=['private_message', 'account'], condition=models.Q(private_message__isnull=False), name='uniq_private_message_reaction'),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        if (self.message_id is None) == (self.private_message_id is None):
            raise ValidationError('A reaction must belong to exactly one message.')


class ConversationNickname(models.Model):
    owner = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='chat_nicknames')
    partner = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='nicknames_set_by_others')
    nickname = models.CharField(max_length=60)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['owner', 'partner'], name='unique_chat_nickname_per_user')]

    def __str__(self):
        return f'{self.owner_id} → {self.partner_id}: {self.nickname}'
