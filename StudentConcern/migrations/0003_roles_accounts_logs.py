
import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('StudentConcern', '0002_alter_studentconcern_college'),
    ]

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('student', 'Student'), ('staff', 'Staff'), ('admin', 'Admin')], max_length=10)),
                ('Fullname', models.CharField(max_length=100)),
                ('StudentID', models.IntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(9999999)])),
                ('College', models.CharField(blank=True, choices=[('College of Computer Studies', 'College of Computer Studies'), ('College of Education', 'College of Education'), ('College of Agriculture', 'College of Agriculture')], max_length=100)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
            ],
            options={
                'ordering': ['role', 'Fullname'],
            },
        ),
        migrations.AddField(
            model_name='studentconcern',
            name='category',
            field=models.CharField(choices=[('Academic', 'Academic'), ('Facilities', 'Facilities'), ('Financial', 'Financial'), ('Welfare & Safety', 'Welfare & Safety'), ('Administrative', 'Administrative'), ('Other', 'Other')], default='Other', max_length=30),
        ),
        migrations.AddField(
            model_name='studentconcern',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False),
        ),
        migrations.AddField(
            model_name='studentconcern',
            name='evidence',
            field=models.ImageField(blank=True, upload_to='evidence/%Y/%m/'),
        ),
        migrations.AddField(
            model_name='studentconcern',
            name='priority',
            field=models.CharField(choices=[('Low', 'Low'), ('Normal', 'Normal'), ('High', 'High'), ('Urgent', 'Urgent')], default='Normal', max_length=10),
        ),
        migrations.AddField(
            model_name='studentconcern',
            name='status',
            field=models.CharField(choices=[('Pending', 'Pending'), ('In Review', 'In Review'), ('In Progress', 'In Progress'), ('Resolved', 'Resolved'), ('Rejected', 'Rejected')], default='Pending', max_length=20),
        ),
        migrations.AddField(
            model_name='studentconcern',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='studentconcern',
            name='StudentID',
            field=models.IntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(9999999)]),
        ),
        migrations.AddField(
            model_name='studentconcern',
            name='author',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='concerns', to='StudentConcern.account'),
        ),
        migrations.CreateModel(
            name='ActivityLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Fullname', models.CharField(blank=True, max_length=100)),
                ('role', models.CharField(blank=True, max_length=10)),
                ('StudentID', models.CharField(blank=True, max_length=20)),
                ('action', models.CharField(choices=[('login', 'Login'), ('login_failed', 'Failed login'), ('logout', 'Logout'), ('view_dashboard', 'Viewed dashboard'), ('search', 'Searched'), ('view_concern', 'Viewed concern'), ('submit_concern', 'Submitted concern'), ('update_concern', 'Edited concern'), ('delete_concern', 'Deleted concern'), ('change_status', 'Changed status'), ('reply', 'Posted reply'), ('export', 'Exported CSV'), ('create_account', 'Registered account'), ('update_account', 'Edited account'), ('delete_account', 'Deleted account')], max_length=30)),
                ('detail', models.CharField(blank=True, max_length=300)),
                ('ip', models.CharField(blank=True, max_length=64)),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now, editable=False)),
                ('account', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='StudentConcern.account')),
            ],
            options={
                'ordering': ['-id'],
            },
        ),
        migrations.CreateModel(
            name='ConcernReply',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('author_name', models.CharField(max_length=100)),
                ('author_role', models.CharField(max_length=10)),
                ('kind', models.CharField(choices=[('Feedback', 'Feedback'), ('Action Report', 'Action Report')], default='Feedback', max_length=20)),
                ('message', models.CharField(max_length=1000)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('author', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='StudentConcern.account')),
                ('concern', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='replies', to='StudentConcern.studentconcern')),
            ],
            options={
                'ordering': ['created_at', 'id'],
            },
        ),
    ]
