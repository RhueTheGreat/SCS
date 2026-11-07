from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('StudentConcern', '0007_chat_presence_nicknames')]
    operations = [
        migrations.AlterField(
            model_name='chatreaction', name='reaction',
            field=models.CharField(max_length=20, choices=[(v, v) for v in (
                'smile','laugh','cool','cry','sad','meh','smirk','heart','like','dislike',
                'handshake','question','exclamation','one','two','three','four','five',
                'point','peace','open_hand','fist'
            )]),
        ),
    ]
