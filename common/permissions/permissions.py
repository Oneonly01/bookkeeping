from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """
    通用数据所有者权限。

    要求业务对象具有 user 字段。
    """

    message = "无权访问该数据"

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        return hasattr(obj, "user") and obj.user_id == request.user.id
