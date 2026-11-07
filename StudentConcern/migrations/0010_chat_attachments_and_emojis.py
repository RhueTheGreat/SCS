# Generated for chat attachments and expanded reactions.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('StudentConcern', '0009_refine_chat_reaction_choices')]
    operations = [
        migrations.AddField(
            model_name='chatmessage',
            name='attachment',
            field=models.FileField(blank=True, null=True, upload_to='chat_uploads/%Y/%m/'),
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='attachment_name',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='attachment_type',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='privatemessage',
            name='attachment',
            field=models.FileField(blank=True, null=True, upload_to='chat_uploads/%Y/%m/'),
        ),
        migrations.AddField(
            model_name='privatemessage',
            name='attachment_name',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='privatemessage',
            name='attachment_type',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AlterField(
            model_name='chatreaction',
            name='reaction',
            field=models.CharField(choices=[(v, v) for v in ('smile','open_mouth','grin','sweat_laugh','laugh','sad','cry','surprised','angry','grimace','kiss','heart_eyes','pleading','tongue','cool','meh','smirk','heart','like','dislike','handshake','heart_hands','clap','folded_hands','ok_hand','index_up','wave','question','exclamation','one','two','three','four','five','point','peace','open_hand','fist','fire','hug','red_heart','fireworks','cake','party','sparkles','star','thumbs_up','thumbs_down','laughing','sob','thinking','rocket','tada','gift','balloon','coffee','pizza','sun','moon','check','x_mark')], max_length=20),
        ),
    ]
