from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('StudentConcern', '0008_expand_chat_reactions')]
    operations = [
        migrations.AlterField(
            model_name='chatreaction', name='reaction',
            field=models.CharField(max_length=20, choices=[(v, v) for v in (
                'smile','open_mouth','grin','sweat_laugh','laugh','sad','cry','surprised','angry','grimace','kiss','heart_eyes','pleading','tongue','cool','meh','smirk',
                'heart','like','dislike','handshake','heart_hands','clap','folded_hands','ok_hand','index_up','wave','question','exclamation','one','two','three','four','five','point','peace','open_hand','fist'
            )]),
        ),
    ]
