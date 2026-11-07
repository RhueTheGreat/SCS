
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('StudentConcern', '0004_chat_room'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatmessage',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='edited',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='updated_at',
            field=models.DateTimeField(db_index=True, default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='activitylog',
            name='action',
            field=models.CharField(choices=[('login', 'Login'), ('login_failed', 'Failed login'), ('logout', 'Logout'), ('view_dashboard', 'Viewed dashboard'), ('search', 'Searched'), ('view_concern', 'Viewed concern'), ('submit_concern', 'Submitted concern'), ('update_concern', 'Edited concern'), ('delete_concern', 'Deleted concern'), ('change_status', 'Changed status'), ('reply', 'Posted reply'), ('export', 'Exported CSV'), ('chat_message', 'Sent chat message'), ('chat_edit', 'Edited chat message'), ('chat_delete', 'Deleted chat message'), ('private_message', 'Sent private message'), ('private_edit', 'Edited private message'), ('private_delete', 'Deleted private message'), ('create_account', 'Registered account'), ('update_account', 'Edited account'), ('delete_account', 'Deleted account')], max_length=30),
        ),
        migrations.CreateModel(
            name='PrivateMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.CharField(max_length=500)),
                ('edited', models.BooleanField(default=False)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now, editable=False)),
                ('updated_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('read_at', models.DateTimeField(blank=True, null=True)),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received_messages', to='StudentConcern.account')),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_messages', to='StudentConcern.account')),
            ],
            options={
                'ordering': ['id'],
            },
        ),
    ]
