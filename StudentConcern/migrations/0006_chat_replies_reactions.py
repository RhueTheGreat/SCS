import django.db.models.deletion
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('StudentConcern', '0005_chat_edit_private')]
    operations = [
        migrations.AddField(model_name='account', name='last_seen_concerns', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='account', name='last_seen_public_chat', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='chatmessage', name='reply_to', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='thread_replies', to='StudentConcern.chatmessage')),
        migrations.AddField(model_name='privatemessage', name='reply_to', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='thread_replies', to='StudentConcern.privatemessage')),
        migrations.CreateModel(name='ChatReaction', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('reaction', models.CharField(choices=[('like','like'),('dislike','dislike'),('question','question'),('laugh','laugh'),('middlefinger','middlefinger')], max_length=20)),
            ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='StudentConcern.account')),
            ('message', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='reactions', to='StudentConcern.chatmessage')),
            ('private_message', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='reactions', to='StudentConcern.privatemessage')),
        ]),
        migrations.AddConstraint(model_name='chatreaction', constraint=models.UniqueConstraint(condition=models.Q(('message__isnull', False)), fields=('message','account'), name='uniq_public_message_reaction')),
        migrations.AddConstraint(model_name='chatreaction', constraint=models.UniqueConstraint(condition=models.Q(('private_message__isnull', False)), fields=('private_message','account'), name='uniq_private_message_reaction')),
    ]
