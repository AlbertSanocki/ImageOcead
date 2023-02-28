from rest_framework.permissions import BasePermission

class CanAccessBinaryImage(BasePermission):
    """User with this permission user has access to the endpoint for fetching binary image"""

    message = 'Your account tier does not allow you to fetch link to binary image. Upgrade Your account tier to Enterprice!'

    def has_permission(self, request, view):
        user_tier = getattr(request.user, 'tier', None)
        return bool(user_tier and user_tier.expiring_links)