
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('StudentConcern', '0003_roles_accounts_logs'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activitylog',
            name='action',
            field=models.CharField(choices=[('login', 'Login'), ('login_failed', 'Failed login'), ('logout', 'Logout'), ('view_dashboard', 'Viewed dashboard'), ('search', 'Searched'), ('view_concern', 'Viewed concern'), ('submit_concern', 'Submitted concern'), ('update_concern', 'Edited concern'), ('delete_concern', 'Deleted concern'), ('change_status', 'Changed status'), ('reply', 'Posted reply'), ('export', 'Exported CSV'), ('chat_message', 'Sent chat message'), ('chat_delete', 'Deleted chat message'), ('create_account', 'Registered account'), ('update_account', 'Edited account'), ('delete_account', 'Deleted account')], max_length=30),
        ),
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('author_name', models.CharField(max_length=100)),
                ('author_role', models.CharField(max_length=10)),
                ('message', models.CharField(max_length=500)),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now, editable=False)),
                ('account', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='StudentConcern.account')),
            ],
            options={
                'ordering': ['id'],
            },
        ),
    ]
