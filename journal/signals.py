from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db.models.signals import m2m_changed, post_migrate
from django.dispatch import receiver

from .permissions import (
    ADMINISTRATORS,
    ROLE_PERMISSION_CODENAMES,
    STAFF_GROUPS,
)


@receiver(m2m_changed, sender=get_user_model().groups.through)
def enable_staff_for_administrative_groups(
    sender,
    instance,
    action,
    reverse,
    model,
    pk_set,
    **kwargs,
):
    if reverse or action != "post_add" or instance.is_staff:
        return
    if model.objects.filter(pk__in=pk_set, name__in=STAFF_GROUPS).exists():
        instance.is_staff = True
        instance.save(update_fields=["is_staff"])


@receiver(post_migrate)
def ensure_default_group_permissions(sender, **kwargs):
    if sender.label != "journal":
        return

    administrators, _ = Group.objects.get_or_create(name=ADMINISTRATORS)
    administrators.permissions.set(Permission.objects.all())

    for group_name, codenames in ROLE_PERMISSION_CODENAMES.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        group.permissions.set(
            Permission.objects.filter(
                content_type__app_label="journal",
                codename__in=codenames,
            )
        )

    get_user_model().objects.filter(
        groups__name__in=STAFF_GROUPS,
        is_staff=False,
    ).distinct().update(is_staff=True)
