from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        from django.contrib.auth.models import User
        from django.db.models.signals import post_save

        def ensure_profile(sender, instance, created, **kwargs):
            from .models import Profile
            if created:
                Profile.objects.get_or_create(user=instance, defaults={'display_name': instance.username})

        post_save.connect(ensure_profile, sender=User, dispatch_uid='core_ensure_profile')
