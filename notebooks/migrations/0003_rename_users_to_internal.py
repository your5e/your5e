from django.db import migrations


def rename_users_to_internal(apps, schema_editor):
    Notebook = apps.get_model("notebooks", "Notebook")
    Notebook.objects.filter(visibility="users").update(visibility="internal")


def rename_internal_to_users(apps, schema_editor):
    Notebook = apps.get_model("notebooks", "Notebook")
    Notebook.objects.filter(visibility="internal").update(visibility="users")


class Migration(migrations.Migration):
    dependencies = [
        ("notebooks", "0002_rename_site_to_users"),
    ]

    operations = [
        migrations.RunPython(rename_users_to_internal, rename_internal_to_users),
    ]
