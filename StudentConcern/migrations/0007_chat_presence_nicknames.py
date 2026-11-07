import django.db.models.deletion
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('StudentConcern', '0006_chat_replies_reactions')]
    operations = [
        migrations.AddField(
            model_name='account', name='last_active_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.CreateModel(
            name='ConversationNickname',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nickname', models.CharField(max_length=60)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chat_nicknames', to='StudentConcern.account')),
                ('partner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='nicknames_set_by_others', to='StudentConcern.account')),
            ],
        ),
        migrations.AddConstraint(
            model_name='conversationnickname',
            constraint=models.UniqueConstraint(fields=('owner', 'partner'), name='unique_chat_nickname_per_user'),
        ),
    ]
