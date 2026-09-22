import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rag", "0003_alter_message_options_message_created_at_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="chats",
            name="deleted_at",
            field=models.DateTimeField(blank=True, default=None, null=True),
        ),
        migrations.AlterField(
            model_name="chats",
            name="id",
            field=models.UUIDField(
                default=uuid.uuid4, editable=False, primary_key=True, serialize=False
            ),
        ),
        migrations.AlterField(
            model_name="chats",
            name="title",
            field=models.CharField(default="Untitled Chat", max_length=255),
        ),
    ]
