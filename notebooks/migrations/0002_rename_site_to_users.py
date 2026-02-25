from django.db import migrations


def rename_site_to_users(apps, schema_editor):
    Notebook = apps.get_model("notebooks", "Notebook")
    Notebook.objects.filter(visibility="site").update(visibility="users")


def rename_users_to_site(apps, schema_editor):
    Notebook = apps.get_model("notebooks", "Notebook")
    Notebook.objects.filter(visibility="users").update(visibility="site")


class Migration(migrations.Migration):
    dependencies = [
        ("notebooks", "0001_create_notebook"),
    ]

    operations = [
        migrations.RunPython(rename_site_to_users, rename_users_to_site),
    ]
