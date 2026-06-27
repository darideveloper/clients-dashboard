from django.contrib.auth.models import User


def is_user_admin(user: User):
    user_groups = user.groups.all()
    for group in user_groups:
        if group.name in ["admins", "supports"]:
            return True
    return user.is_superuser
